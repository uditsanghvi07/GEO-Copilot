"""Local embedding service using sentence-transformers.

Fully offline/local — never calls a paid embeddings API. Model name read
from Settings.EMBEDDING_MODEL_NAME.
"""

from functools import lru_cache

from loguru import logger
from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    """Load and cache the local embedding model (lazy, on first use)."""
    logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
    return SentenceTransformer(settings.EMBEDDING_MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of text passages.

    Inputs: list of strings.
    Outputs: list of embedding vectors (list of floats).
    """
    if not texts:
        return []
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False)
    return [emb.tolist() for emb in embeddings]


def embed_query(query: str) -> list[float]:
    """Embed a single query string for retrieval."""
    return embed_texts([query])[0]
