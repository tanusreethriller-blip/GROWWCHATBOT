"""Pre-retrieval refusals: PII, advice, returns, out-of-scope schemes."""

from __future__ import annotations

import re

from rag.config import EDUCATIONAL_URL, FACTSHEET_HUB_URL, IN_SCOPE_SCHEMES

PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.I)
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
OTP_RE = re.compile(r"\b(?:otp|one[-\s]?time\s?password)\b", re.I)

ADVICE_RE = re.compile(
    r"\b(should i|shall i|can i buy|recommend|best fund|which fund is better|"
    r"buy or sell|switch to|is it good to invest|suitable for me)\b",
    re.I,
)
RETURNS_RE = re.compile(
    r"\b(return|returns|cagr|nav history|outperform|performed better|"
    r"1[- ]year|3[- ]year|5[- ]year|performance compare|which performed)\b",
    re.I,
)

OTHER_AMC_RE = re.compile(
    r"\b(sbi|icici|nippon|axis|uti|kotak|mirae|parag parikh|ppfas|tata mf|"
    r"aditya birla|absli|dsp|invesco|franklin|motilal)\b",
    re.I,
)

# Any mention of the 5 in-scope schemes (canonical names or common aliases).
IN_SCOPE_MENTION_RE = re.compile(
    r"\b(flexi\s*cap|large\s*cap|mid\s*cap|balanced\s+advantage|\bbaf\b|"
    r"tax\s*saver|elss|equity\s*linked\s+savings?)\b",
    re.I,
)
HDFC_FUND_RE = re.compile(r"\bhdfc\b", re.I)
FUND_WORD_RE = re.compile(r"\b(fund|scheme|elss)\b", re.I)


def _response(*, answer: str, source_url: str, last_updated: str, reason: str) -> dict:
    return {
        "answer": answer,
        "source_url": source_url,
        "last_updated": last_updated,
        "refusal": True,
        "refusal_reason": reason,
    }


def classify(question: str) -> dict | None:
    """Return a refusal payload, or None to allow retrieval."""
    q = question or ""
    if PAN_RE.search(q) or AADHAAR_RE.search(q) or EMAIL_RE.search(q) or PHONE_RE.search(q) or OTP_RE.search(q):
        return _response(
            answer=(
                "Please do not share PAN, Aadhaar, account numbers, OTPs, email, or phone numbers. "
                "This assistant does not store personal data and cannot look up your account."
            ),
            source_url=EDUCATIONAL_URL,
            last_updated="",
            reason="pii",
        )
    if ADVICE_RE.search(q):
        return _response(
            answer=(
                "I cannot advise whether you should buy, sell, or switch a scheme. "
                "This tool only shares facts from official public pages, not investment advice."
            ),
            source_url=EDUCATIONAL_URL,
            last_updated="",
            reason="advice",
        )
    if RETURNS_RE.search(q):
        return _response(
            answer=(
                "I do not compute or compare returns. "
                "Use the official factsheet for scheme performance and related disclosures."
            ),
            source_url=FACTSHEET_HUB_URL,
            last_updated="",
            reason="returns",
        )
    if OTHER_AMC_RE.search(q) or (
        HDFC_FUND_RE.search(q) and FUND_WORD_RE.search(q) and not IN_SCOPE_MENTION_RE.search(q)
    ):
        names = "; ".join(IN_SCOPE_SCHEMES)
        return _response(
            answer=(
                f"That scheme or AMC is out of scope. I only cover these HDFC Direct schemes: {names}."
            ),
            source_url=EDUCATIONAL_URL,
            last_updated="",
            reason="out_of_scope",
        )
    return None


if __name__ == "__main__":
    cases = [
        ("Should I buy HDFC Flexi Cap?", "advice"),
        ("My PAN is ABCDE1234F", "pii"),
        ("Email me at ravi.sharma@gmail.com about my SIP", "pii"),
        ("Which fund performed better last year?", "returns"),
        ("Tell me about SBI Bluechip", "out_of_scope"),
        ("What is the exit load on HDFC Small Cap Fund?", "out_of_scope"),
        ("Expense ratio of HDFC Large Cap Fund?", None),
        ("What is the lock-in period for HDFC ELSS Tax Saver Fund?", None),
        ("How do I download a capital gains statement?", None),
    ]
    for text, expected in cases:
        result = classify(text)
        got = (result or {}).get("refusal_reason")
        assert got == expected, f"{text!r}: expected {expected}, got {got}"
        if result:
            assert result["refusal"] is True and result["source_url"].startswith("http"), result
        print(f"{text!r} -> {got or 'allow'}")
    print("guardrails OK")
