"""Structure-aware chunking with scheme/doc/section prefixes."""

from __future__ import annotations

import re

from rag.config import CHUNK_OVERLAP, CHUNK_TOKENS


def _approx_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _split_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^(## .+)$", text)
    if len(parts) == 1:
        return [("Body", text.strip())]
    sections: list[tuple[str, str]] = []
    preamble = parts[0].strip()
    if preamble:
        sections.append(("Preamble", preamble))
    for i in range(1, len(parts), 2):
        heading = parts[i].lstrip("# ").strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if body:
            sections.append((heading or "Section", body))
    return sections or [("Body", text.strip())]


def _window(text: str, max_tokens: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= max_tokens:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_tokens)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def chunk_document(doc: dict, max_tokens: int | None = None, overlap: int | None = None) -> list[dict]:
    max_tokens = max_tokens or CHUNK_TOKENS
    overlap = overlap if overlap is not None else CHUNK_OVERLAP
    scheme = doc.get("scheme") or "None"
    doc_type = doc.get("doc_type") or "listing"
    out: list[dict] = []
    chunk_index = 0
    for heading, body in _split_sections(doc.get("text") or ""):
        pieces = _window(body, max_tokens=max_tokens, overlap=overlap)
        if doc_type == "listing":
            pieces = _window(body, max_tokens=max(max_tokens, 480), overlap=overlap)
        for piece in pieces:
            prefix = f"Scheme: {scheme} | Doc: {doc_type} | Section: {heading}"
            text = f"{prefix}\n{piece}".strip()
            out.append(
                {
                    "text": text,
                    "url": doc.get("url") or "",
                    "scheme": doc.get("scheme") or "",
                    "doc_type": doc_type,
                    "section": heading,
                    "fetched_at": doc.get("fetched_at") or "",
                    "priority": doc.get("priority") or "low",
                    "title": doc.get("title") or "",
                    "plan": doc.get("plan") or "",
                    "chunk_index": chunk_index,
                }
            )
            chunk_index += 1
    return out


def chunk_documents(docs: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    for doc in docs:
        chunks.extend(chunk_document(doc))
    return chunks


if __name__ == "__main__":
    from rag.load import load_cleaned

    docs = load_cleaned()
    if not docs:
        print("No cleaned docs. Run rag/load.py first.")
    else:
        chunks = chunk_document(docs[0])
        print(f"doc={docs[0].get('title')} chunks={len(chunks)}")
        for c in chunks[:2]:
            print("---")
            print(c["text"][:200])
            print("approx_tokens", _approx_tokens(c["text"]))
