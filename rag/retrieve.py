"""Query embed + Chroma top-k with scheme filter and score threshold.

Chroma returns **distances**, not similarities. The collection is created with
`hnsw:space="cosine"` (see `rag/store.py`), so distance ~= 1 - cosine
similarity; `_similarity_from_distance` converts so the configured
`SIMILARITY_THRESHOLD` is read as a minimum similarity, not a distance.
"""

from __future__ import annotations

import re

from rag.config import IN_SCOPE_SCHEMES, SIMILARITY_THRESHOLD, TOP_K
from rag.embed import embed_texts
from rag.store import get_collection

SCHEME_ALIASES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\belss\b|\btax\s*saver\b", re.I), "HDFC ELSS Tax Saver Fund"),
    (re.compile(r"\bbalanced\s+advantage\b|\bbaf\b", re.I), "HDFC Balanced Advantage Fund"),
    (re.compile(r"\bflexi\s*cap\b", re.I), "HDFC Flexi Cap Fund"),
    (re.compile(r"\blarge\s*cap\b", re.I), "HDFC Large Cap Fund"),
    (re.compile(r"\bmid\s*cap\b", re.I), "HDFC Mid Cap Fund"),
]


def detect_scheme(question: str) -> str | None:
    q = question or ""
    for canonical in IN_SCOPE_SCHEMES:
        if canonical.lower() in q.lower():
            return canonical
    for pattern, name in SCHEME_ALIASES:
        if pattern.search(q):
            return name
    return None


def _similarity_from_distance(distance: float | None) -> float:
    if distance is None:
        return 0.0
    # Cosine space in Chroma: distance ~= 1 - cosine similarity
    return max(0.0, 1.0 - float(distance))


def retrieve(question: str, top_k: int | None = None, threshold: float | None = None) -> list[dict]:
    k = top_k or TOP_K
    cutoff = SIMILARITY_THRESHOLD if threshold is None else threshold
    collection = get_collection()
    if collection.count() == 0:
        return []

    query_vec = embed_texts([question])[0].tolist()
    scheme = detect_scheme(question)
    kwargs: dict = {
        "query_embeddings": [query_vec],
        "n_results": min(k + 4, max(collection.count(), 1)),
        "include": ["documents", "metadatas", "distances"],
    }
    if scheme:
        kwargs["where"] = {"scheme": scheme}

    try:
        raw = collection.query(**kwargs)
    except Exception:
        raw = collection.query(
            query_embeddings=[query_vec],
            n_results=min(k + 4, max(collection.count(), 1)),
            include=["documents", "metadatas", "distances"],
        )

    hits: list[dict] = []
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    for doc, meta, dist in zip(docs, metas, dists):
        meta = meta or {}
        sim = _similarity_from_distance(dist)
        hits.append(
            {
                "text": doc or "",
                "similarity": sim,
                "distance": dist,
                **meta,
            }
        )

    high = [h for h in hits if (h.get("priority") or "low") != "low"]
    chosen = high if len(high) >= min(2, k) else hits
    chosen = [h for h in chosen if h["similarity"] >= cutoff]
    chosen.sort(key=lambda h: h["similarity"], reverse=True)
    return chosen[:k]


if __name__ == "__main__":
    elss = retrieve("ELSS lock-in")
    assert elss, "expected hits for ELSS lock-in"
    assert all((h.get("scheme") or "").startswith("HDFC ELSS") or h.get("doc_type") == "how-to" for h in elss), elss
    assert not any(h.get("doc_type") == "listing" for h in elss), "listing noise leaked into scheme query"
    print("ELSS lock-in ->", len(elss), "hits, top:", round(elss[0]["similarity"], 3), elss[0].get("scheme"))

    for q in ("expense ratio of large cap", "minimum SIP HDFC Mid Cap Fund"):
        hits = retrieve(q)
        assert hits and hits[0].get("scheme"), q
        print(f"{q!r} -> {len(hits)} hits, top:", round(hits[0]["similarity"], 3), hits[0].get("scheme"))

    garbage = retrieve("asdkfjh blue widget zxcv")
    assert garbage == [], garbage
    print("garbage query -> 0 hits (below threshold)")
    print("retrieval OK")
