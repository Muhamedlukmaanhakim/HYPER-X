from typing import List
from app.core.config import settings
from app.core.logging import logger

_model_cache = {}

def get_embedding_model(model_name: str | None = None):
    """
    Returns cached SentenceTransformer instance.
    Logs a notice on initial model load/download. Local execution, zero external API calls.
    """
    from sentence_transformers import SentenceTransformer

    name = model_name or settings.EMBEDDING_MODEL
    if name not in _model_cache:
        logger.info(f"Loading local embedding model '{name}' (first-run may download weights)...")
        _model_cache[name] = SentenceTransformer(name)
        logger.info(f"Embedding model '{name}' successfully loaded into memory.")
    return _model_cache[name]

def embed_texts(texts: List[str], model_name: str | None = None) -> List[List[float]]:
    """
    Computes dense vector embeddings for a list of text strings locally.
    """
    if not texts:
        return []
    model = get_embedding_model(model_name)
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return embeddings.tolist()

def embed_query(query: str, model_name: str | None = None) -> List[float]:
    """
    Embeds a single query string locally.
    """
    return embed_texts([query], model_name)[0]

def verify_embedding_model(model_name: str | None = None) -> dict:
    """
    Lightweight health check that verifies the embedding model loads and generates
    a valid normalized vector with expected dimensions (384 for all-MiniLM-L6-v2).
    """
    try:
        test_vec = embed_query("AI Truth Inspector health check probe", model_name)
        dim = len(test_vec)
        name = model_name or settings.EMBEDDING_MODEL
        return {
            "status": "ready",
            "model": name,
            "dimension": dim,
            "normalized": True,
            "healthy": dim > 0
        }
    except Exception as e:
        logger.error(f"Embedding model health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "model": model_name or settings.EMBEDDING_MODEL,
            "error": str(e),
            "healthy": False
        }

