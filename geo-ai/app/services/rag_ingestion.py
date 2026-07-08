"""RAG ingestion: chunk product content, embed locally, upsert to ChromaDB."""

import json
import re
from pathlib import Path

from loguru import logger
from sqlalchemy.orm import Session

from app.models.play_store_data import PlayStoreData
from app.models.website_data import WebsiteData
from app.services.embedding_service import embed_texts
from app.vector_db.collection_service import get_product_collection

CHUNK_TARGET_WORDS = 300
CHUNK_OVERLAP_WORDS = 50


def _chunk_text(text: str, source: str, section: str) -> list[dict]:
    """Split text into ~200-400 word chunks with slight overlap."""
    words = text.split()
    if not words:
        return []
    chunks: list[dict] = []
    start = 0
    idx = 0
    while start < len(words):
        end = min(len(words), start + CHUNK_TARGET_WORDS)
        chunk_words = words[start:end]
        chunks.append(
            {
                "text": " ".join(chunk_words),
                "source": source,
                "section": section,
                "chunk_index": idx,
            }
        )
        idx += 1
        if end >= len(words):
            break
        start = end - CHUNK_OVERLAP_WORDS

    return chunks


def _extract_body_from_snapshot(snapshot_path: str | None) -> str:
    """Best-effort plain text extraction from a saved HTML snapshot."""
    if not snapshot_path:
        return ""
    path = Path(snapshot_path)
    if not path.exists():
        return ""
    try:
        from bs4 import BeautifulSoup

        html = path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        main = soup.find("main") or soup.find("article") or soup.body or soup
        return main.get_text(separator=" ", strip=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug(f"Could not extract body from {snapshot_path}: {exc!r}")
        return ""


def build_ingestion_chunks(db: Session, product_id: int) -> list[dict]:
    """Gather all ingestible text for a product from website_data + play_store_data."""
    chunks: list[dict] = []

    website = db.query(WebsiteData).filter(WebsiteData.product_id == product_id).first()
    if website:
        if website.title:
            chunks.extend(_chunk_text(website.title, "website", "title"))
        if website.meta_description:
            chunks.extend(_chunk_text(website.meta_description, "website", "meta_description"))
        if website.headings_summary:
            try:
                headings = json.loads(website.headings_summary)
                heading_text = " ".join(
                    h for level in ("h1", "h2", "h3") for h in headings.get(level, [])
                )
                if heading_text:
                    chunks.extend(_chunk_text(heading_text, "website", "headings"))
            except (json.JSONDecodeError, TypeError):
                pass

        for page in website.crawled_pages or []:
            role = page.get("role", "page")
            body = _extract_body_from_snapshot(page.get("snapshot_path"))
            if body:
                chunks.extend(_chunk_text(body, "website", role))

    play_store = db.query(PlayStoreData).filter(PlayStoreData.product_id == product_id).first()
    if play_store:
        if play_store.short_description:
            chunks.extend(_chunk_text(play_store.short_description, "play_store", "short_description"))
        if play_store.full_description:
            chunks.extend(_chunk_text(play_store.full_description, "play_store", "full_description"))

    return chunks


def ingest_product_content(db: Session, product_id: int) -> int:
    """Chunk, embed, and upsert product content into its ChromaDB collection.

    Inputs: db session, product_id.
    Outputs: number of chunks upserted.
    """
    chunks = build_ingestion_chunks(db, product_id)
    if not chunks:
        logger.info(f"No content to ingest for product_id={product_id}")
        return 0

    collection = get_product_collection(product_id)
    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    ids = [f"{product_id}_{c['source']}_{c['section']}_{c['chunk_index']}" for c in chunks]
    metadatas = [
        {"source": c["source"], "section": c["section"], "product_id": product_id}
        for c in chunks
    ]

    collection.upsert(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
    logger.info(f"Ingested {len(chunks)} chunks for product_id={product_id}")
    return len(chunks)
