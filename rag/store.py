"""Persistent ChromaDB collection hdfc_mf_faq."""

from __future__ import annotations

import hashlib
from pathlib import Path

import chromadb

from rag.config import CHROMA_PATH, COLLECTION_NAME


def _chunk_id(chunk: dict) -> str:
    key = f"{chunk.get('url','')}|{chunk.get('section','')}|{chunk.get('chunk_index',0)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def get_collection(path: Path | None = None):
    persist = str(path or CHROMA_PATH)
    client = chromadb.PersistentClient(path=persist)
    return client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def reset_collection(path: Path | None = None) -> None:
    persist = str(path or CHROMA_PATH)
    client = chromadb.PersistentClient(path=persist)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    client.get_or_create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})


def upsert_chunks(chunks: list[dict], embeddings: list[list[float]], path: Path | None = None) -> int:
    if not chunks:
        return 0
    collection = get_collection(path)
    ids = [_chunk_id(c) for c in chunks]
    metadatas = []
    for c in chunks:
        metadatas.append(
            {
                "url": c.get("url") or "",
                "scheme": c.get("scheme") or "",
                "doc_type": c.get("doc_type") or "",
                "section": c.get("section") or "",
                "fetched_at": c.get("fetched_at") or "",
                "priority": c.get("priority") or "low",
                "title": c.get("title") or "",
                "plan": c.get("plan") or "",
            }
        )
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=[c["text"] for c in chunks],
        metadatas=metadatas,
    )
    return collection.count()


if __name__ == "__main__":
    from rag.embed import embed_texts

    reset_collection()
    dummy = [
        {
            "text": "Scheme: HDFC Large Cap Fund | Doc: scheme-page | Section: Fees\nExpense ratio example.",
            "url": "https://example.invalid/large",
            "scheme": "HDFC Large Cap Fund",
            "doc_type": "scheme-page",
            "section": "Fees",
            "fetched_at": "2026-09-29",
            "priority": "high",
            "title": "Large Cap",
            "plan": "Direct",
            "chunk_index": 0,
        },
        {
            "text": "Scheme: HDFC ELSS Tax Saver Fund | Doc: scheme-page | Section: Lock-in\n3 year lock-in example.",
            "url": "https://example.invalid/elss",
            "scheme": "HDFC ELSS Tax Saver Fund",
            "doc_type": "scheme-page",
            "section": "Lock-in",
            "fetched_at": "2026-09-29",
            "priority": "high",
            "title": "ELSS",
            "plan": "Direct",
            "chunk_index": 0,
        },
    ]
    vecs = embed_texts([d["text"] for d in dummy])
    n = upsert_chunks(dummy, vecs.tolist())
    print("count after upsert", n)
    n2 = upsert_chunks(dummy, vecs.tolist())
    print("count after re-upsert", n2)
    coll = get_collection()
    print("reopen count", coll.count())
