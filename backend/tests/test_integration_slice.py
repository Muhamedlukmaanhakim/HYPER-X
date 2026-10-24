import json
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.database import Base, SessionLocal, engine
from app.models.models import Configuration, Document, TestCase
from app.services.providers import TestDoubleProvider, get_llm_provider

@pytest.fixture(scope="module")
def client():
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c

def test_full_vertical_slice_integration(client, monkeypatch):
    """
    Vertical slice integration test:
    1. Seed sample doc & test cases.
    2. Ask playground question.
    3. Run evaluation using TestDoubleProvider.
    4. Export results to CSV and verify real columns and data.
    """
    # 1. Ingestion / Sample doc seeding
    doc_resp = client.post("/api/documents/seed-sample")
    assert doc_resp.status_code == 200
    doc_data = doc_resp.json()
    assert doc_data["original_name"] == "sample_document.txt"
    assert doc_data["chunk_count"] > 0

    # Seed sample test cases
    tc_resp = client.post("/api/testcases/seed-sample")
    assert tc_resp.status_code == 200
    tc_list = tc_resp.json()
    assert len(tc_list) >= 5

    # 2. RAG Ask endpoint (Playground)
    ask_resp = client.post("/api/rag/ask", json={
        "question": "What is the standard API rate limit for Tier 1 consumers?",
        "top_k": 3
    })
    assert ask_resp.status_code == 200
    ask_data = ask_resp.json()
    assert ask_data["answer"] != ""
    assert len(ask_data["retrieved_passages"]) > 0

    # 3. Evaluation Run with injected TestDoubleProvider
    # Monkeypatch provider factory so that evaluation uses TestDoubleProvider
    test_double = TestDoubleProvider(predefined_responses={
        "rate limit": "Tier 1 consumers are capped at 120 requests per minute with 180 burst [sample_doc:2:0]."
    })
    monkeypatch.setattr("app.api.routers.evaluations.get_llm_provider", lambda **kwargs: test_double)
    monkeypatch.setattr("app.services.rag.get_llm_provider", lambda **kwargs: test_double)


    # Fetch configuration
    cfg_resp = client.get("/api/settings/configurations")
    cfg_id = cfg_resp.json()[0]["id"]

    eval_resp = client.post("/api/evaluations/run", json={
        "name": "Integration Slice Test Run",
        "configuration_id": cfg_id,
        "k_values": [1, 3],
        "llm_judge_enabled": False,
        "pass_threshold": 0.50
    })
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["status"] == "completed"
    assert eval_data["evaluated_case_count"] > 0
    run_id = eval_data["id"]

    # 4. Fetch Detailed Results
    detail_resp = client.get(f"/api/evaluations/{run_id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["results"]) > 0
    first_res = detail_data["results"][0]
    assert first_res["category"] in [
        "pass", "retrieval_miss", "incomplete_or_irrelevant_context",
        "unsupported_answer", "incorrect_despite_relevant_context",
        "citation_error", "unanswerable_answered", "needs_review"
    ]
    assert first_res["rule_fired"] != ""

    # 5. CSV Export
    csv_resp = client.get(f"/api/exports/runs/{run_id}/csv")
    assert csv_resp.status_code == 200
    csv_text = csv_resp.text
    assert "Run ID,Run Name" in csv_text
    assert run_id in csv_text
    assert "Recall@1" in csv_text

    # Summary CSV Export
    summary_csv_resp = client.get(f"/api/exports/runs/{run_id}/summary-csv")
    assert summary_csv_resp.status_code == 200
    assert "Evaluation Run Summary Report" in summary_csv_resp.text
