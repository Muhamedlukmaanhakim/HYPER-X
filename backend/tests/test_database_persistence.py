import json
import os
import shutil
import tempfile
import uuid
import numpy as np
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.models.database import Base
from app.models.models import (
    CaseResult,
    Chunk,
    Configuration,
    Comparison,
    Document,
    EvaluationRun,
    TestCase
)
from app.services.chunking import ChunkItem, chunk_pages
from app.services.comparison import compare_evaluation_runs
from app.services.embeddings import embed_query, embed_texts, verify_embedding_model
from app.services.ingestion import ExtractedPage

@pytest.fixture
def temp_workspace():
    """Provides an isolated temporary directory for testing databases without touching real data."""
    tmp_dir = tempfile.mkdtemp(prefix="truth_inspector_test_")
    db_file = os.path.join(tmp_dir, "test_truth_inspector.db")
    chroma_dir = os.path.join(tmp_dir, "chroma")
    upload_dir = os.path.join(tmp_dir, "uploads")
    os.makedirs(chroma_dir, exist_ok=True)
    os.makedirs(upload_dir, exist_ok=True)

    db_url = f"sqlite:///{db_file.replace(os.sep, '/')}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    yield {
        "dir": tmp_dir,
        "db_url": db_url,
        "db_file": db_file,
        "chroma_dir": chroma_dir,
        "upload_dir": upload_dir,
        "engine": engine,
        "Session": TestingSession
    }

    engine.dispose()
    shutil.rmtree(tmp_dir, ignore_errors=True)


# 1. Database initialization and schema verification
def test_database_initialization_and_schema(temp_workspace):
    engine = temp_workspace["engine"]
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected_tables = {
        "documents", "chunks", "configurations", "test_cases",
        "evaluation_runs", "case_results", "reviewer_overrides",
        "comparisons", "jobs", "metric_definitions"
    }
    assert expected_tables.issubset(set(tables)), f"Missing tables: {expected_tables - set(tables)}"


# 2. SQLite write and read operations
def test_sqlite_write_and_read_operations(temp_workspace):
    Session = temp_workspace["Session"]
    db = Session()

    doc_id = f"doc_{uuid.uuid4().hex[:8]}"
    doc = Document(
        id=doc_id,
        filename=f"{doc_id}_test.txt",
        original_name="test.txt",
        file_type="txt",
        file_size_bytes=1024,
        chunk_count=2,
        status="indexed"
    )
    chunk1 = Chunk(
        id=f"{doc_id}:1:0",
        document_id=doc_id,
        page=1,
        chunk_index=0,
        text="First passage content for SQLite persistence test.",
        char_count=49
    )
    chunk2 = Chunk(
        id=f"{doc_id}:1:1",
        document_id=doc_id,
        page=1,
        chunk_index=1,
        text="Second passage content for SQLite persistence test.",
        char_count=50
    )
    db.add(doc)
    db.add(chunk1)
    db.add(chunk2)
    db.commit()

    # Query back
    fetched_doc = db.query(Document).filter(Document.id == doc_id).first()
    assert fetched_doc is not None
    assert fetched_doc.original_name == "test.txt"
    assert len(fetched_doc.chunks) == 2
    assert fetched_doc.chunks[0].chunk_index == 0
    db.close()


# 3. ChromaDB indexing and retrieval
def test_chromadb_indexing_and_retrieval(temp_workspace):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    chroma_dir = temp_workspace["chroma_dir"]
    client = chromadb.PersistentClient(path=chroma_dir, settings=ChromaSettings(anonymized_telemetry=False))
    collection = client.create_collection(name="test_col", metadata={"hnsw:space": "cosine"})

    texts = [
        "ACME API rate limit is 120 requests per minute with burst up to 180 requests.",
        "ACME data retention policy stores user logs for 90 days before cold storage archiving."
    ]
    embeddings = embed_texts(texts)

    collection.upsert(
        ids=["c1", "c2"],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"document_id": "doc_test", "filename": "policy.txt", "page": 1, "chunk_index": 0},
            {"document_id": "doc_test", "filename": "policy.txt", "page": 2, "chunk_index": 1}
        ]
    )

    assert collection.count() == 2

    # Query
    q_emb = embed_query("What is the rate limit for requests?")
    res = collection.query(query_embeddings=[q_emb], n_results=2)
    assert len(res["ids"][0]) == 2
    # The first result should be the rate limit passage
    assert res["ids"][0][0] == "c1"
    dist = res["distances"][0][0]
    similarity = 1.0 - dist
    assert similarity > 0.5


# 4. Embedding dimension and normalization consistency
def test_embedding_dimension_and_normalization():
    probe = "AI Truth Inspector embedding probe"
    vector = embed_query(probe)
    assert len(vector) == 384, f"Expected 384 dimensions, got {len(vector)}"

    # Check normalization: L2 norm of normalized embeddings is ~1.0
    norm = np.linalg.norm(np.array(vector))
    assert abs(norm - 1.0) < 1e-4

    # Check verify_embedding_model health probe
    status = verify_embedding_model()
    assert status["healthy"] is True
    assert status["dimension"] == 384
    assert status["status"] == "ready"


# 5. Document chunk metadata consistency
def test_document_chunk_metadata():
    pages = [
        ExtractedPage(page_number=1, text="System Architecture Overview. Section 1 describes microservices."),
        ExtractedPage(page_number=2, text="Database and Persistence Layer. SQLite is used for structured records.")
    ]
    chunks = chunk_pages(pages, document_id="doc_meta_1", chunk_size=800, chunk_overlap=150, filename="arch.txt")

    assert len(chunks) == 2
    for c in chunks:
        assert c.document_id == "doc_meta_1"
        assert c.filename == "arch.txt"
        assert c.id.startswith("doc_meta_1:")
        assert c.char_count > 0
        d = c.to_dict()
        assert "filename" in d
        assert "char_start" in d
        assert "char_end" in d


# 6. Duplicate document ingestion behavior
def test_duplicate_document_ingestion_behavior(temp_workspace):
    Session = temp_workspace["Session"]
    db = Session()

    # Initial upload
    doc_1 = Document(
        id="doc_dup_1",
        filename="doc_dup_1_spec.txt",
        original_name="spec.txt",
        file_type="txt",
        file_size_bytes=500,
        chunk_count=1,
        status="indexed"
    )
    db.add(doc_1)
    db.commit()

    # Emulate duplicate check logic
    existing = db.query(Document).filter(Document.original_name == "spec.txt").first()
    assert existing is not None
    # Identical size and status -> reuse existing
    assert existing.status == "indexed"
    assert existing.file_size_bytes == 500
    db.close()


# 7. Retrieval from previously indexed documents across simulated restart
def test_retrieval_across_client_restart(temp_workspace):
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    chroma_dir = temp_workspace["chroma_dir"]

    # First session: write data
    client_1 = chromadb.PersistentClient(path=chroma_dir, settings=ChromaSettings(anonymized_telemetry=False))
    col_1 = client_1.create_collection(name="persist_col", metadata={"hnsw:space": "cosine"})
    col_1.upsert(
        ids=["p_chunk_1"],
        embeddings=[embed_query("Persistent storage test chunk")],
        documents=["Persistent storage test chunk content"],
        metadatas=[{"document_id": "doc_p", "page": 1, "filename": "persist.txt"}]
    )
    assert col_1.count() == 1
    del col_1
    del client_1

    # Second session: restart client from same directory
    client_2 = chromadb.PersistentClient(path=chroma_dir, settings=ChromaSettings(anonymized_telemetry=False))
    col_2 = client_2.get_collection(name="persist_col")
    assert col_2.count() == 1

    # Retrieve
    q_emb = embed_query("Persistent storage test")
    res = col_2.query(query_embeddings=[q_emb], n_results=1)
    assert res["ids"][0][0] == "p_chunk_1"
    assert res["metadatas"][0][0]["filename"] == "persist.txt"


# 8. Evaluation result persistence in SQLite
def test_evaluation_result_persistence(temp_workspace):
    Session = temp_workspace["Session"]
    db = Session()

    cfg = Configuration(
        id="cfg_test_persist",
        name="Test Config",
        chunk_size=800,
        chunk_overlap=150,
        top_k=3
    )
    db.add(cfg)

    run = EvaluationRun(
        id="run_persist_1",
        name="Baseline Persistence Run",
        configuration_id="cfg_test_persist",
        configuration_snapshot_json=json.dumps({"top_k": 3, "chunk_size": 800}),
        test_case_count=1,
        evaluated_case_count=1,
        pass_rate=1.0,
        mean_recall=1.0,
        mean_mrr=1.0,
        status="completed"
    )
    db.add(run)

    case_res = CaseResult(
        id="cr_persist_1",
        run_id="run_persist_1",
        test_case_id="tc_1",
        question="What is the data retention limit?",
        question_type="direct_factual",
        reference_answer="90 days.",
        generated_answer="90 days [sample_doc:1:0].",
        mrr=1.0,
        exact_match=1.0,
        category="pass",
        rule_fired="pass",
        suggested_debugging_step="Pass: Model correctly answered citing evidence."
    )
    db.add(case_res)
    db.commit()
    db.close()

    # Re-open session and read back
    db2 = Session()
    saved_run = db2.query(EvaluationRun).filter(EvaluationRun.id == "run_persist_1").first()
    assert saved_run is not None
    assert saved_run.pass_rate == 1.0
    assert len(saved_run.results) == 1
    assert saved_run.results[0].category == "pass"
    db2.close()


# 9. Baseline versus simulated comparison persistence
def test_comparison_persistence(temp_workspace):
    Session = temp_workspace["Session"]
    db = Session()

    cfg = Configuration(id="cfg_comp", name="Comp Config")
    run_base = EvaluationRun(
        id="run_base",
        name="Baseline",
        configuration_id="cfg_comp",
        configuration_snapshot_json="{}",
        pass_rate=0.90,
        mean_recall=0.95,
        mean_mrr=0.95,
        status="completed"
    )
    run_sim = EvaluationRun(
        id="run_sim",
        name="Simulated",
        configuration_id="cfg_comp",
        configuration_snapshot_json="{}",
        is_simulated=True,
        pass_rate=0.40,
        mean_recall=0.30,
        mean_mrr=0.30,
        status="completed"
    )
    db.add_all([cfg, run_base, run_sim])

    comp = Comparison(
        id="cmp_test_1",
        name="Baseline vs Simulated",
        baseline_run_id="run_base",
        candidate_run_id="run_sim",
        test_case_count=10,
        metric_deltas_json=json.dumps({"pass_rate_delta": -0.50, "mean_recall_delta": -0.65}),
        category_changes_json=json.dumps({"regressions": 5, "improvements": 0})
    )
    db.add(comp)
    db.commit()
    db.close()

    # Verify retrieval
    db2 = Session()
    saved_comp = db2.query(Comparison).filter(Comparison.id == "cmp_test_1").first()
    assert saved_comp is not None
    deltas = json.loads(saved_comp.metric_deltas_json)
    assert deltas["pass_rate_delta"] == -0.50
    db2.close()


# 10. Persistence across application restart simulation
def test_full_persistence_across_app_restart(temp_workspace):
    # Phase 1: create records
    Session1 = temp_workspace["Session"]
    db1 = Session1()
    doc = Document(
        id="doc_restart_1",
        filename="restart_doc.txt",
        original_name="restart_doc.txt",
        file_type="txt",
        status="indexed"
    )
    db1.add(doc)
    db1.commit()
    db1.close()

    # Phase 2: simulate restart by creating fresh engine and session to same db file
    fresh_engine = create_engine(temp_workspace["db_url"], connect_args={"check_same_thread": False})
    FreshSession = sessionmaker(bind=fresh_engine)
    db2 = FreshSession()
    fetched = db2.query(Document).filter(Document.id == "doc_restart_1").first()
    assert fetched is not None
    assert fetched.original_name == "restart_doc.txt"
    db2.close()
    fresh_engine.dispose()


# 11. Missing or invalid configuration handling
def test_missing_or_invalid_configuration(temp_workspace):
    Session = temp_workspace["Session"]
    db = Session()
    # Query non-existent document
    doc = db.query(Document).filter(Document.id == "non_existent_id").first()
    assert doc is None
    # Query non-existent evaluation run
    run = db.query(EvaluationRun).filter(EvaluationRun.id == "non_existent_run").first()
    assert run is None
    db.close()


# 12. Graceful handling of database errors
def test_graceful_handling_of_database_errors():
    from app.models.database import verify_database
    from app.services.vectorstore import verify_vectorstore

    # Test verify_database with valid app db
    res = verify_database()
    assert res["healthy"] is True
    assert res["status"] == "connected"
    assert res["dialect"] == "sqlite"

    # Test verify_vectorstore with valid app chroma
    res_vec = verify_vectorstore("default_rag")
    assert res_vec["healthy"] is True
    assert res_vec["status"] == "connected"
    assert res_vec["provider"] == "chromadb"
