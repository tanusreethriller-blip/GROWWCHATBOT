"""Batch ingest: load -> chunk -> embed -> store.

This is the only place that touches the network for content. The query path
(ask/retrieve/generate) reads Chroma and data/cleaned only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag.chunk import chunk_documents
from rag.config import CHROMA_PATH, COLLECTION_NAME, EMBED_BATCH_SIZE
from rag.embed import embed_texts
from rag.load import safe_id, fetch_and_clean, load_catalog, load_cleaned
from rag.store import get_collection, reset_collection, upsert_chunks


def _prune_stale_cleaned(keep_ids: set[str]) -> int:
    """Drop cleaned sidecars whose URL is no longer in sources.csv."""
    from rag.config import CLEANED_DIR

    removed = 0
    for sidecar in CLEANED_DIR.glob("*.json"):
        if sidecar.stem in keep_ids:
            continue
        for path in (sidecar, sidecar.with_suffix(".txt")):
            if path.exists():
                path.unlink()
        removed += 1
    return removed


def _merge_with_previous(fetched: list[dict], catalog_urls: set[str]) -> list[dict]:
    """Keep the previous cleaned snapshot for catalog URLs that failed this run.

    HDFC blocks live fetches and the archive fallback is rate limited, so a single
    run often refreshes only part of the catalog. Without this, a transient
    failure would silently shrink the corpus.
    """
    merged = {doc["url"]: doc for doc in fetched}
    reused = 0
    for doc in load_cleaned():
        if doc["url"] in merged or doc["url"] not in catalog_urls:
            continue
        merged[doc["url"]] = doc
        reused += 1
    if reused:
        print(f"[ingest] reused {reused} previous cleaned snapshot(s) for URLs that failed this run")
    return list(merged.values())


def run_ingest(
    *,
    skip_fetch: bool = False,
    fetch_missing: bool = False,
    batch_size: int | None = None,
) -> dict[str, int]:
    catalog = load_catalog()
    if not catalog:
        raise SystemExit("sources.csv has no URLs; nothing to ingest.")

    if skip_fetch:
        docs = load_cleaned()
        if not docs:
            print("[ingest] no cleaned files found, falling back to fetch")
            docs = fetch_and_clean(catalog)
    else:
        if fetch_missing:
            from rag.config import CLEANED_DIR

            pending = [
                row for row in catalog if not (CLEANED_DIR / f"{safe_id(row['url'])}.txt").exists()
            ]
            print(f"[ingest] fetching {len(pending)} of {len(catalog)} URLs that have no cleaned file yet")
            docs = fetch_and_clean(pending) if pending else []
        else:
            docs = fetch_and_clean(catalog)
            pruned = _prune_stale_cleaned({safe_id(row["url"]) for row in catalog})
            if pruned:
                print(f"[ingest] pruned {pruned} cleaned file(s) no longer in sources.csv")
        docs = _merge_with_previous(docs, {row["url"] for row in catalog})

    failed = len({d["url"] for d in docs} ^ {row["url"] for row in catalog})
    print(f"[ingest] catalog_urls={len(catalog)} documents={len(docs)} failed_or_skipped={failed}")
    if not docs:
        print("[ingest] no usable documents; aborting")
        return {"documents": 0, "chunks": 0, "collection_count": 0, "failed": failed}

    chunks = chunk_documents(docs)
    print(f"[ingest] chunks={len(chunks)}")
    if not chunks:
        print("[ingest] nothing to embed")
        return {"documents": len(docs), "chunks": 0, "collection_count": 0, "failed": failed}

    size = batch_size or EMBED_BATCH_SIZE
    total_batches = (len(chunks) + size - 1) // size
    print(f"[ingest] embedding {len(chunks)} chunks in {total_batches} batch(es) of {size}")
    embeddings = embed_texts([c["text"] for c in chunks], batch_size=size)

    # Wipe only after embedding succeeds so a failed run keeps the old collection.
    reset_collection()
    count = upsert_chunks(chunks, embeddings.tolist())

    print(f"[ingest] collection={COLLECTION_NAME} count={count}")
    print(f"[ingest] persist_path={CHROMA_PATH} exists={CHROMA_PATH.exists()}")
    return {"documents": len(docs), "chunks": len(chunks), "collection_count": count, "failed": failed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest official HDFC/SEBI/AMFI pages into Chroma.")
    parser.add_argument("--skip-fetch", action="store_true", help="Reuse data/cleaned instead of fetching")
    parser.add_argument(
        "--fetch-missing",
        action="store_true",
        help="Fetch only catalog URLs that have no cleaned file yet (fast re-ingest after adding sources)",
    )
    parser.add_argument("--batch-size", type=int, default=None, help=f"Embedding batch size (default {EMBED_BATCH_SIZE})")
    args = parser.parse_args(argv)

    stats = run_ingest(skip_fetch=args.skip_fetch, fetch_missing=args.fetch_missing, batch_size=args.batch_size)
    if stats["collection_count"] <= 0:
        print("[ingest] FAILED: collection is empty")
        return 1
    verified = get_collection().count()
    print(f"[ingest] verified_count={verified}")
    return 0 if verified == stats["collection_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
