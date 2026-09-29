"""Generate a short answer from retrieved chunks. Citation comes from metadata."""

from __future__ import annotations

import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

from rag.config import ROOT, SYSTEM_PROMPT_PATH

load_dotenv(ROOT / ".env")

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)


def llm_configured() -> bool:
    """True if an LLM endpoint/key is available; otherwise extractive fallback is used."""
    return bool(os.getenv("OPENAI_API_KEY")) or (os.getenv("LLM_PROVIDER", "ollama").lower() != "openai")


def load_system_prompt() -> str:
    path = Path(SYSTEM_PROMPT_PATH)
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return "Answer using only the provided context. At most 3 sentences. No advice."


def pack_context(chunks: list[dict]) -> str:
    blocks = []
    for i, ch in enumerate(chunks, start=1):
        blocks.append(
            f"[chunk {i}]\n{ch.get('text','')}\n"
            f"SOURCE_URL: {ch.get('url','')}\n"
            f"FETCHED_AT: {ch.get('fetched_at','')}\n"
        )
    return "\n".join(blocks)


def _extractive(chunks: list[dict]) -> str:
    top = (chunks[0].get("text") or "").split("\n", 1)
    body = top[1] if len(top) > 1 else top[0]
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    clipped = " ".join(s.strip() for s in sentences if s.strip())[:500]
    parts = re.split(r"(?<=[.!?])\s+", clipped)
    return " ".join(parts[:3]).strip() or "The indexed page does not state this fact clearly in the retrieved section."


def _call_ollama(system: str, user: str) -> str | None:
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("LLM_MODEL", "llama3.2")
    try:
        resp = httpx.post(
            f"{host}/api/chat",
            json={
                "model": model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return (resp.json().get("message") or {}).get("content")
    except Exception:
        return None


def _call_openai(system: str, user: str) -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    try:
        resp = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def generate(question: str, chunks: list[dict]) -> dict:
    if not chunks:
        raise ValueError("generate() requires retrieved chunks")

    system = load_system_prompt()
    user = (
        f"Question: {question}\n\nContext:\n{pack_context(chunks)}\n\n"
        "Write at most 3 factual sentences. Do not include a URL; the application will attach the source."
    )
    provider = (os.getenv("LLM_PROVIDER") or "ollama").lower()
    text = None
    if provider == "openai":
        text = _call_openai(system, user) or _call_ollama(system, user)
    else:
        text = _call_ollama(system, user) or _call_openai(system, user)
    if not text or not text.strip():
        text = _extractive(chunks)

    text = " ".join(URL_RE.sub("", text).split())
    sentences = re.split(r"(?<=[.!?])\s+", text)
    answer = " ".join(sentences[:3]).strip().strip(" -:,;")
    best = chunks[0]
    fetched = [c.get("fetched_at") or "" for c in chunks if c.get("fetched_at")]
    last_updated = max(fetched) if fetched else (best.get("fetched_at") or "")
    return {
        "answer": answer,
        "source_url": best.get("url") or "",
        "last_updated": last_updated,
        "refusal": False,
        "refusal_reason": None,
    }


if __name__ == "__main__":
    fake = [
        {
            "text": "Scheme: HDFC Large Cap Fund | Doc: scheme-page | Section: Fees\n"
            "Expense ratio of the Direct plan is 1.08% p.a. (as on the scheme page).",
            "url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct",
            "scheme": "HDFC Large Cap Fund",
            "doc_type": "scheme-page",
            "section": "Fees",
            "fetched_at": "2026-09-20",
            "priority": "high",
            "title": "HDFC Large Cap Fund Direct",
            "plan": "Direct",
            "similarity": 0.71,
        },
        {
            "text": "Scheme: HDFC Flexi Cap Fund | Doc: scheme-page | Section: Fees\n"
            "Expense ratio of the Direct plan is 0.99% p.a. (as on the scheme page).",
            "url": "https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct",
            "scheme": "HDFC Flexi Cap Fund",
            "doc_type": "scheme-page",
            "section": "Fees",
            "fetched_at": "2026-09-25",
            "priority": "high",
            "title": "HDFC Flexi Cap Fund Direct",
            "plan": "Direct",
            "similarity": 0.62,
        },
    ]
    result = generate("What is the expense ratio of HDFC Large Cap Fund (Direct)?", fake)
    assert result["source_url"] == fake[0]["url"], result
    assert result["last_updated"] == "2026-09-25", result  # max fetched_at, from metadata only
    assert "http" not in result["answer"], result["answer"]
    assert result["refusal"] is False and result["refusal_reason"] is None
    print(result)
    print("keys:", sorted(result))

    try:
        generate("anything", [])
    except ValueError as exc:
        print("empty hits rejected:", exc)
    else:
        raise AssertionError("generate() must not run without retrieved chunks")
    print("generate OK")
