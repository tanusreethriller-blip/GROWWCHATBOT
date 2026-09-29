"""Query orchestration: guardrails → retrieve → generate."""

from __future__ import annotations

from rag.config import FACTSHEET_HUB_URL
from rag.generate import generate
from rag.guardrails import classify
from rag.retrieve import retrieve


def ask(question: str) -> dict:
    q = (question or "").strip()
    if not q:
        return {
            "answer": "Ask a factual question about one of the five in-scope HDFC schemes.",
            "source_url": FACTSHEET_HUB_URL,
            "last_updated": "",
            "refusal": True,
            "refusal_reason": "empty",
        }

    refused = classify(q)
    if refused:
        return refused

    hits = retrieve(q)
    if not hits:
        return {
            "answer": (
                "I do not have this in the official pages I indexed. "
                "Try naming one of the five HDFC Direct schemes, or check the factsheet hub."
            ),
            "source_url": FACTSHEET_HUB_URL,
            "last_updated": "",
            "refusal": True,
            "refusal_reason": "not_in_corpus",
        }

    return generate(q, hits)


if __name__ == "__main__":
    def _boom(*args, **kwargs):
        raise AssertionError("generate() must not be called on this path")

    import rag.pipeline as self_module

    real_generate = self_module.generate

    self_module.generate = _boom
    for blocked in ("Should I buy HDFC Flexi Cap Fund?", "asdkfjh blue widget zxcv", "My PAN is ABCDE1234F"):
        guarded = ask(blocked)
        assert guarded["refusal"] is True and guarded["source_url"].startswith("http"), guarded
        print(f"no-generate path OK: {blocked!r} -> {guarded['refusal_reason']}")
    self_module.generate = real_generate

    for question in (
        "What is the exit load on HDFC Flexi Cap Fund (Direct)?",
        "What is the minimum SIP amount for HDFC Mid Cap Fund?",
        "How do I download a capital gains statement?",
    ):
        result = ask(question)
        assert set(result) == {"answer", "source_url", "last_updated", "refusal", "refusal_reason"}, result
        assert result["source_url"].startswith("https://"), result
        assert result["last_updated"], result
        assert not result["refusal"], result
        print(f"Q: {question}\n   {result['answer'][:160]}\n   {result['source_url']} ({result['last_updated']})")
    print("pipeline OK")
