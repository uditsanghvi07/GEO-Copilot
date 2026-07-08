"""ChromaDB collection management — one isolated collection per product."""

from chromadb.api.models.Collection import Collection

from app.vector_db.client import get_chroma_client


def product_collection_name(product_id: int) -> str:
    """Return the ChromaDB collection name for a product."""
    return f"product_{product_id}"


def get_product_collection(product_id: int) -> Collection:
    """Get or create the persistent ChromaDB collection for a product.

    Inputs: product_id.
    Outputs: chromadb Collection handle.
    """
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=product_collection_name(product_id),
        metadata={"hnsw:space": "cosine"},
    )


def collection_has_documents(product_id: int) -> bool:
    """Check whether a product's collection has any ingested chunks."""
    try:
        collection = get_product_collection(product_id)
        return collection.count() > 0
    except Exception:  # noqa: BLE001
        return False
