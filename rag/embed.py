"""MiniLM embeddings — same model for documents and queries."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

from rag.config import EMBED_BATCH_SIZE, EMBED_MODEL

EMBED_DIM = 384


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


def embed_texts(texts: list[str], batch_size: int | None = None) -> np.ndarray:
    if not texts:
        return np.zeros((0, EMBED_DIM), dtype=np.float32)
    model = get_model()
    size = max(1, batch_size or EMBED_BATCH_SIZE)
    batches: list[np.ndarray] = []
    for start in range(0, len(texts), size):
        encoded = model.encode(
            texts[start : start + size],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        batches.append(np.asarray(encoded, dtype=np.float32))
    return np.vstack(batches)


if __name__ == "__main__":
    vecs = embed_texts(["expense ratio", "ELSS lock-in"])
    print("shape", vecs.shape, "dim", vecs.shape[1])
