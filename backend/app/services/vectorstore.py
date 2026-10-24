import os
import re
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.logging import logger

_chroma_client = None

def get_chroma_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        
        os.makedirs(settings.CHROMA_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=settings.CHROMA_DIR,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        logger.info(f"Initialized ChromaDB persistent client at: {settings.CHROMA_DIR}")
    return _chroma_client

def _clean_collection_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    if len(cleaned) < 3:
        cleaned = f"col_{cleaned}"
    return cleaned[:60]

def get_collection(name: str = "default_rag"):
    client = get_chroma_client()
    clean_name = _clean_collection_name(name)
    return client.get_or_create_collection(
        name=clean_name,
        metadata={"hnsw:space": "cosine"}
    )

def upsert_chunks(
    chunks: List[Any],
    embeddings: List[List[float]],
    collection_name: str = "default_rag"
):
    """
    Upserts chunks with their pre-calculated embeddings and metadata into ChromaDB.
    """
    if not chunks:
        return

    collection = get_collection(collection_name)
    ids = [c.id for c in chunks]
    documents = [c.text for c in chunks]
    metadatas = [
        {
            "document_id": c.document_id,
            "filename": getattr(c, "filename", "") or "",
            "page": int(c.page),
            "chunk_index": int(c.chunk_index),
            "char_start": int(c.char_start),
            "char_end": int(c.char_end),
            "char_count": int(c.char_count),
            "source": f"{getattr(c, 'filename', '') or c.document_id}#page={int(c.page)}"
        }
        for c in chunks
    ]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    logger.info(f"Upserted {len(chunks)} chunks into Chroma collection '{collection_name}'")

def query_collection(
    query_embedding: List[float],
    top_k: int = 3,
    collection_name: str = "default_rag",
    where_filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Queries ChromaDB using cosine distance and returns matched passages with similarity scores.
    Converts cosine distance to cosine similarity (1 - distance).
    """
    collection = get_collection(collection_name)
    
    # Chroma count check
    if collection.count() == 0:
        return []

    count = min(top_k, collection.count())
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=count,
        where=where_filter
    )

    passages = []
    if results and results.get("ids") and results["ids"][0]:
        ids = results["ids"][0]
        distances = results.get("distances", [[]])[0]
        docs = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        for idx, chunk_id in enumerate(ids):
            dist = distances[idx] if idx < len(distances) else 1.0
            # Cosine similarity is 1.0 - distance
            score = round(max(0.0, min(1.0, 1.0 - dist)), 4)
            meta = metadatas[idx] if idx < len(metadatas) else {}
            doc_text = docs[idx] if idx < len(docs) else ""

            passages.append({
                "chunk_id": chunk_id,
                "document_id": meta.get("document_id", ""),
                "filename": meta.get("filename", ""),
                "page": meta.get("page", 1),
                "score": score,
                "text": doc_text,
                "metadata": meta
            })

    # Sort descending by score
    passages.sort(key=lambda x: x["score"], reverse=True)
    return passages

def delete_document_from_chroma(document_id: str, collection_name: str = "default_rag"):
    """
    Removes all chunks belonging to a document from Chroma collection.
    """
    collection = get_collection(collection_name)
    try:
        collection.delete(where={"document_id": document_id})
        logger.info(f"Deleted document '{document_id}' chunks from Chroma collection '{collection_name}'")
    except Exception as e:
        logger.warning(f"Chroma delete error for doc {document_id}: {str(e)}")

def verify_vectorstore(collection_name: str = "default_rag") -> Dict[str, Any]:
    """
    Safe, lightweight verification of ChromaDB persistence and collection accessibility.
    Does not insert or modify user data.
    """
    try:
        client = get_chroma_client()
        clean_name = _clean_collection_name(collection_name)
        col = client.get_or_create_collection(
            name=clean_name,
            metadata={"hnsw:space": "cosine"}
        )
        count = col.count()
        return {
            "status": "connected",
            "provider": "chromadb",
            "collection": clean_name,
            "chunk_count": count,
            "distance_metric": "cosine",
            "healthy": True
        }
    except Exception as e:
        logger.error(f"Vectorstore health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "provider": "chromadb",
            "collection": collection_name,
            "error": str(e),
            "healthy": False
        }

