"""RAG retrieval via LlamaIndex over per-product ChromaDB collections."""

from functools import lru_cache

from llama_index.core import Settings as LlamaSettings
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from loguru import logger

from app.config import settings
from app.vector_db.client import get_chroma_client
from app.vector_db.collection_service import get_product_collection, product_collection_name

DEFAULT_TOP_K = 5


@lru_cache
def _get_llama_embed_model() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(model_name=settings.EMBEDDING_MODEL_NAME)


def _configure_llama_settings() -> None:
    LlamaSettings.embed_model = _get_llama_embed_model()


def retrieve_relevant_chunks(product_id: int, query: str, top_k: int = DEFAULT_TOP_K) -> list[str]:
    """Retrieve top-k relevant text chunks for a product using LlamaIndex.

    Inputs: product_id, query string, top_k (default 5).
    Outputs: list of chunk text strings, ordered by relevance.
    """
    _configure_llama_settings()
    collection = get_product_collection(product_id)
    if collection.count() == 0:
        return []

    chroma_client = get_chroma_client()
    vector_store = ChromaVectorStore(chroma_collection=collection)
    index = VectorStoreIndex.from_vector_store(vector_store)

    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)

    chunks = [node.get_content() for node in nodes]
    logger.debug(f"Retrieved {len(chunks)} chunks for product_id={product_id}")
    return chunks
