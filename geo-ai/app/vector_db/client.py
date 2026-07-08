"""Thin wrapper around a persistent, local ChromaDB client.

Kept minimal in Module 1 - no collections are created or used yet. Future
RAG-oriented agents (content generation, competitor analysis) will call
`get_or_create_collection()` rather than importing chromadb directly, so the
persistence directory and embedding function stay centralized here.
"""

from functools import lru_cache

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.config import Settings as ChromaSettings

from app.config import settings


@lru_cache
def get_chroma_client() -> chromadb.ClientAPI:
    """Return a cached, persistent ChromaDB client rooted at
    Settings.CHROMA_PERSIST_DIR."""
    return chromadb.PersistentClient(
        path=settings.CHROMA_PERSIST_DIR,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


def get_or_create_collection(name: str) -> Collection:
    """Fetch (or lazily create) a named ChromaDB collection.

    Inputs: name (str) - collection name, e.g. "product_{id}_content".
    Outputs: a chromadb `Collection` handle.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(name=name)
