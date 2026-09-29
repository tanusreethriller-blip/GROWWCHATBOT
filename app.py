"""Tiny facts-only FAQ UI. Chat history is in-memory only (no persistence, no auth)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from rag.generate import llm_configured
from rag.pipeline import ask

DISCLAIMER = (
    "This assistant shares facts from official public documents only. It is not investment advice. "
    "Mutual fund investments are subject to market risks. Read all scheme-related documents carefully. "
    "Do not share PAN, Aadhaar, account numbers, OTPs, email, or phone numbers here."
)

EXAMPLES = [
    "What is the expense ratio of HDFC Large Cap Fund (Direct)?",
    "What is the lock-in for HDFC ELSS Tax Saver Fund?",
    "How do I download a capital gains statement?",
]


def _render_turn(question: str, result: dict) -> None:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        body = result.get("answer") or ""
        (st.warning if result.get("refusal") else st.write)(body)
        url = result.get("source_url") or ""
        if url:
            st.markdown(f"**Source:** <{url}>")
        updated = result.get("last_updated")
        if updated:
            st.caption(f"Last updated from sources: {updated}")
        elif not result.get("refusal"):
            st.caption("Last updated from sources: date shown on the source page")


st.set_page_config(page_title="HDFC MF FAQ", layout="centered")
st.title("HDFC Mutual Fund FAQ assistant")
st.write(
    "Welcome. Ask factual questions about five HDFC Direct schemes "
    "(Flexi Cap, Large Cap, ELSS Tax Saver, Mid Cap, Balanced Advantage). "
    "Every answer comes from an official page I indexed and cites exactly one link."
)
st.info("Facts-only. No investment advice.")
st.caption(DISCLAIMER)
if not llm_configured():
    st.caption("LLM not configured - answers are quoted verbatim from the retrieved official page.")

if "turns" not in st.session_state:
    st.session_state.turns = []

cols = st.columns(len(EXAMPLES))
for i, example in enumerate(EXAMPLES):
    if cols[i].button(example, use_container_width=True, key=f"example_{i}"):
        st.session_state.pending = example

typed = st.chat_input("Ask a factual scheme question (no PAN/Aadhaar/OTP/email/phone)")
to_ask = typed or st.session_state.pop("pending", None)
if to_ask:
    st.session_state.turns.append((to_ask, ask(to_ask)))

for question, result in st.session_state.turns:
    _render_turn(question, result)
