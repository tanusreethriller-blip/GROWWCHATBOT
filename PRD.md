# PRD: HDFC Mutual Fund FAQ RAG Chatbot

**Product:** Facts-only FAQ assistant for selected HDFC Mutual Fund schemes  
**Type:** Small-corpus RAG chatbot  
**Status:** Draft  
**Owner:** Product  
**Last updated:** 29 Sep 2026

---

## 1. Problem statement

Retail investors and internal support/content teams repeatedly ask the same factual questions about mutual fund schemes (expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, how to download statements). Answers must come only from **official public pages**, with a **source link**, and must **never** be investment advice.

We will build a RAG chatbot that retrieves from a scoped HDFC AMC corpus and answers only grounded facts.

---

## 2. Goals and non-goals

### Goals

- Answer factual scheme/process questions using **only** ingested official pages.
- Show **one clear citation URL** on every answer.
- Refuse advice, performance comparison, and PII.
- Keep answers **≤3 sentences**, plus `Last updated from sources: <date>`.
- Implement a **full RAG pipeline**: load → chunk → embed → store → retrieve → generate.
- Ship a tiny prototype UI plus the assignment deliverables (sources, README, sample Q&A, disclaimer).

### Non-goals

- Personalized portfolio, tax, or “should I buy/sell” advice.
- Computing or comparing returns, NAV history, or rankings.
- Login, KYC, transactions, or account-linked data.
- Third-party blogs, aggregators, or screenshots of app backends as sources.
- Multi-AMC coverage in v1.
- Voice, multilingual UI, or production-grade auth/scale.

---

## 3. Users

| Persona | Need |
|---|---|
| Retail investor comparing HDFC schemes | Fast, cited facts (charges, lock-in, SIP min, riskometer, how-to for statements) |
| Support / content | Same answers, consistent wording, official links, no advice risk |

---

## 4. Scope (v1)

### AMC and schemes

**AMC:** HDFC Mutual Fund

**In-scope schemes (5):**

1. HDFC Flexi Cap Fund (Direct)
2. HDFC Large Cap Fund (Direct)
3. HDFC ELSS Tax Saver Fund (Direct)
4. HDFC Mid Cap Fund (Direct)
5. HDFC Balanced Advantage Fund (Direct)

### Allowed question types

- Expense ratio
- Exit load
- Minimum SIP / minimum investment
- ELSS lock-in
- Riskometer
- Benchmark
- How to download statements / capital-gains / CAS
- Other **facts present in the corpus** (KIM/SID/factsheet/FAQ/fee pages)

### Corpus (starter URL list — 15 public HDFC pages)

Must be expanded to **15–25 URLs** in the source list deliverable (add KIM/SID/factsheet PDFs or official fee/riskometer/benchmark notes where available). Starter set:

| # | URL |
|---|---|
| 1 | https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct |
| 2 | https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct |
| 3 | https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver-fund/direct |
| 4 | https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/direct |
| 5 | https://www.hdfcfund.com/explore/mutual-funds/hdfc-balanced-advantage-fund/direct |
| 6 | https://www.hdfcfund.com/explore/mutual-funds |
| 7 | https://www.hdfcfund.com/explore/mutual-funds/equity |
| 8 | https://www.hdfcfund.com/explore/mutual-funds/hybrid |
| 9 | https://www.hdfcfund.com/explore/mutual-funds/tax-savings |
| 10 | https://www.hdfcfund.com/explore/mutual-funds/index |
| 11 | https://www.hdfcfund.com/mutual-funds/factsheets |
| 12 | https://www.hdfcfund.com/services/consolidated-account-statement |
| 13 | https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india |
| 14 | https://www.hdfcfund.com/explore/mutual-funds/income-solutions |
| 15 | https://www.hdfcfund.com/explore/mutual-funds/solution-oriented |

**Source policy:** Public HDFC / SEBI / AMFI pages only. No blogs from non-AMC sites. HDFC’s own learn/blog page for capital-gains statements is in the given list and may be used as an official AMC how-to.

---

## 5. Product principles (skills W1–W3)

| Skill | Product rule |
|---|---|
| **W1 — Think like a model** | Identify the exact fact. If missing, out of scope, or opinion → refuse. Do not invent. |
| **W2 — Prompting** | Instruction-style system prompt: concise, polite refusals, citation wording, facts-only. |
| **W3 — RAG only** | Answers grounded in retrieved chunks. Citation must match retrieved source. |

---

## 6. User experience

### UI (tiny)

- Welcome line
- **3 example questions** (click-to-ask)
- Persistent note: **“Facts-only. No investment advice.”**
- Chat input + answer area
- Each answer: body (≤3 sentences) + **one source link** + **Last updated from sources:**

### Example questions (suggested)

1. What is the expense ratio of HDFC Large Cap Fund (Direct)?
2. What is the lock-in for HDFC ELSS Tax Saver Fund?
3. How do I download a capital gains statement?

### Answer format

```
<≤3 factual sentences>

Source: <one URL>

Last updated from sources: <YYYY-MM-DD>
```

### Refusal behavior

| User intent | Behavior |
|---|---|
| Buy/sell/switch, “best fund”, suitability | Polite facts-only refusal + one educational official link (e.g. AMFI/SEBI/HDFC learn) |
| Returns / comparison / “which performed better” | Do not compute. Point to official factsheet URL. |
| PII (PAN, Aadhaar, account, OTP, email, phone) | Do not accept or store. Tell user not to share PII; answer only generic process if still in corpus. |
| Scheme outside the 5 | Out of scope; say which schemes are covered. |
| Fact not in retrieved context | “I don’t have this in the official pages I indexed” + closest relevant source if any. |

### Disclaimer (UI snippet)

> This assistant shares facts from official public documents only. It is not investment advice. Mutual fund investments are subject to market risks. Read all scheme-related documents carefully. Do not share PAN, Aadhaar, account numbers, OTPs, email, or phone numbers here.

---

## 7. RAG architecture (must follow all stages)

End-to-end pipeline:

**Loading → Chunking → Embedding → Storing vectors → Retrieval → Generation**

### 7.1 Loading (ingestion)

- Fetch/load the 15–25 official pages (HTML and/or PDFs: factsheet, KIM, SID).
- Strip nav/boilerplate; keep scheme name, section headings, tables, dates.
- Persist raw + cleaned text with metadata: `url`, `title`, `scheme` (if any), `doc_type` (factsheet / KIM / SID / FAQ / how-to / listing), `fetched_at`.
- Re-ingest is a batch job, not live crawl per query in v1.

### 7.2 Chunking

Corpus is mixed: **scheme pages (tables + short labels)**, **hub listings**, **how-to articles**, and likely **PDF factsheets/KIM/SID**.

**Strategy:** hierarchical, structure-aware chunking — not a single naive character split.

| Content type | Chunking |
|---|---|
| HTML scheme pages | Split by heading / card / table row groups. One chunk ≈ one fact family (e.g. “exit load” table, “riskometer”, “benchmark”). Target **256–400 tokens**, overlap **40–80 tokens**. |
| How-to / FAQ | Split by H2/H3 + numbered steps. Keep a step sequence in one chunk when possible. |
| PDFs (factsheet/KIM/SID) | Page/section split using headings; keep tables intact in one chunk. |
| Hub/listing pages | Larger chunks OK; they are mostly navigation, low priority for retrieval. |

**Always prefix each chunk** with: `Scheme: … | Doc: … | Section: …` so retrieval and citations stay scheme-specific (avoids mixing Flexi Cap expense ratio with Large Cap).

**Why this:** MiniLM embeddings work better on short, single-topic chunks. MF facts live in tables and labeled fields; splitting mid-table causes wrong citations.

### 7.3 Embedding

- **Model:** `sentence-transformers/all-MiniLM-L6-v2`
- Embed chunk text (with metadata prefix).
- Same model at query time.

### 7.4 Storing vector data

- **Vector DB:** ChromaDB (local persistent directory for the prototype).
- Collection e.g. `hdfc_mf_faq`.
- Store: embedding + document text + metadata (`url`, `scheme`, `doc_type`, `section`, `fetched_at`).

### 7.5 Retrieval

- Embed user query.
- Similarity search, **top-k = 4–6**.
- Optional metadata filter when the query names a scheme.
- If max similarity is below a threshold, treat as “not in corpus” rather than guessing.
- Pass only retrieved chunks to the LLM (no unaugmented generation for factual answers).

### 7.6 Generation

- LLM uses **retrieved context only**.
- System prompt: facts-only, ≤3 sentences, one source URL from retrieved metadata, refuse advice/PII/returns math.
- Citation = `url` of the **best supporting chunk**, not a hallucinated link.

---

## 8. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| F1 | User can ask a question in the UI | P0 |
| F2 | System retrieves from ChromaDB using MiniLM embeddings | P0 |
| F3 | Answer is grounded in retrieved chunks | P0 |
| F4 | Every answer includes exactly one source URL | P0 |
| F5 | Answers ≤3 sentences + last-updated line | P0 |
| F6 | Advice / buy-sell / suitability → refusal + educational link | P0 |
| F7 | Returns comparison → no computation; link factsheet | P0 |
| F8 | PII not stored; user warned if they paste PII | P0 |
| F9 | Welcome + 3 examples + facts-only note | P0 |
| F10 | Offline/local prototype runnable via README | P0 |
| F11 | Source list of 15–25 URLs (CSV or MD) | P0 |
| F12 | Sample Q&A file (5–10 queries + answers + links) | P0 |

---

## 9. Non-functional requirements

| Area | Requirement |
|---|---|
| Privacy | No PAN, Aadhaar, account numbers, OTPs, emails, phones accepted or logged |
| Grounding | No answer without retrieval (except refusals, which may use a fixed educational URL) |
| Sources | AMC / SEBI / AMFI public pages only |
| Latency | Prototype: typically under 10s per query on a laptop |
| Transparency | Last-updated date from ingestion `fetched_at` (or document date if parsed) |
| Reproducibility | README: Python version, install, ingest command, run command, AMC + scheme list, known limits |

---

## 10. Out of scope (explicit)

- Investment recommendations, risk scoring of the user, tax optimization
- Live NAV / return calculators
- Other AMCs or more than 5 HDFC schemes in v1
- User accounts, chat history persistence with PII
- Fine-tuning an LLM on MF data

---

## 11. Deliverables (assignment)

1. Working prototype (app) or ≤3-min demo video if hosting is not possible
2. Source list (CSV/MD) of 15–25 URLs
3. README: setup, scope (AMC + schemes), known limits
4. Sample Q&A (5–10 queries with assistant answers + links)
5. Disclaimer snippet in UI

**Suggested sample Q&A coverage:** expense ratio, exit load, min SIP, ELSS lock-in, riskometer/benchmark, capital-gains statement how-to, one advice refusal, one returns refusal, one unknown/out-of-scope.

---

## 12. Success criteria

- ≥8/10 sample factual questions answered correctly vs source page, with the right scheme and a real URL.
- 100% of answers show a citation.
- 100% of advice/returns/PII probes handled per policy.
- Pipeline is visible in code: load, chunk, embed, Chroma persist, retrieve, generate.
- UI matches the tiny-spec (welcome, 3 examples, facts-only note).

---

## 13. Known risks and limits (document in README)

- HTML/JS-rendered pages may not contain full KIM/SID numbers; PDFs may be required.
- Direct vs Regular plans: always state plan if the page does.
- Expense ratios and loads **change**; answers are only as fresh as last ingest.
- MiniLM + small k can still retrieve the wrong scheme if chunks lack scheme prefixes.
- Listing pages add noise; down-rank or exclude from default retrieval if they hurt precision.

---

## 14. Tech stack (v1)

| Layer | Choice |
|---|---|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB |
| Chunking | Structure-aware, ~256–400 tokens, overlap ~40–80, scheme/doc prefix |
| App | Small local web or notebook UI (implementation choice) |
| LLM | Any instruction-following model used **only** with retrieved context |

---

## 15. Open decisions (implementation)

- Exact LLM (local vs API) — does not change RAG stages.
- Whether to ingest PDFs from the factsheets hub in addition to HTML. **Recommend yes** for expense ratio / load accuracy.
- Hosting vs demo video.

---

## 16. Glossary

| Abbreviation | Full form |
|---|---|
| AMC | Asset Management Company |
| MF | Mutual Fund |
| ELSS | Equity Linked Savings Scheme |
| SIP | Systematic Investment Plan |
| SEBI | Securities and Exchange Board of India |
| AMFI | Association of Mutual Funds in India |
| KIM | Key Information Memorandum |
| SID | Scheme Information Document |
| RAG | Retrieval-Augmented Generation |
| PII | Personally Identifiable Information |
| CAS | Consolidated Account Statement |
