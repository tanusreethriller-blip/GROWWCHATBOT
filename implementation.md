# Implementation guide (phase-wise)

**Use this file to drive Cursor.**  
**Do not skip phases.** Each phase assumes the previous phase’s **Done when** checklist is true.

| Read first | Why |
|---|---|
| `PRD.md` | Product rules (facts-only, refusals, UI copy, 5 schemes) |
| `architecture.md` | Components, pipelines, metadata, response JSON |
| This file | What to build **now**, what **not** to build yet |

**Stack (locked):** Python 3.11+, `sentence-transformers/all-MiniLM-L6-v2`, ChromaDB collection `hdfc_mf_faq`, ingest ≠ query, no live crawl on chat.

**LLM (open):** Ollama **or** API is fine. Do not change RAG stages if you swap the LLM.

---

## How to run Cursor (one phase per prompt)

1. Open a **new agent chat** (or a clean turn) for that phase only.
2. Paste the **Cursor prompt** at the end of the phase.
3. After Cursor finishes, run the **Done when** checks yourself (or ask Cursor: “verify Done when for Phase N”).
4. Only then start the next phase.

**Standing rules for every prompt (already inlined below):**

- Follow `architecture.md` layout: `ingest.py`, `app.py`, `rag/*.py`, `prompts/system.txt`.
- Keep RAG stages in **separate files** (`load.py`, `chunk.py`, `embed.py`, `store.py`, `retrieve.py`, `generate.py`, `guardrails.py`).
- Citation URL = chunk **metadata**, never model-invented.
- No PII in logs. No git secrets. `data/raw/`, `data/cleaned/`, `chroma/` gitignored.
- Do not implement later phases “while you’re here.”

---

## Phase map

| Phase | Name | Architecture | Outcome |
|---|---|---|---|
| 0 | Scaffold | §8, §9, §12 | Runnable empty project + config |
| 1 | Source catalog | §4 catalog, PRD URLs | `sources.csv` 15–25 rows |
| 2 | Load | §5.1 | Fetch allowlist → `data/raw` + `data/cleaned` |
| 3 | Chunk | §5.2 | Prefixed chunks, 256–400 tokens |
| 4 | Embed + store | §5.3–5.4 | MiniLM + Chroma persist |
| 5 | Ingest CLI | §3 ingest | `python ingest.py` end-to-end |
| 6 | Guardrails | §6.1 | Answer vs refuse **before** retrieval |
| 7 | Retrieve | §6.2 | top-k, scheme filter, threshold |
| 8 | Generate | §6.3–6.4 | Prompt + JSON contract |
| 9 | Query service | §3 query, §6 | `ask(question) → JSON` |
| 10 | UI | §7, PRD §6 | Tiny chat UI |
| 11 | Deliverables | PRD §11 | README, sample Q&A, sources |
| 12 | Tune + harden | §11–§12 | Threshold, listing noise, PDFs if HTML is empty |

---

## Phase 0 — Project scaffold

**Goal:** Empty app that imports, with config knobs from architecture §12.

**Create**

- `requirements.txt`: `sentence-transformers`, `chromadb`, `beautifulsoup4`, `lxml`, `httpx` or `requests`, `pypdf` or `pymupdf`, UI lib later (Streamlit **or** Gradio — pick **Streamlit** unless already chosen).
- `.gitignore`: `.env`, `data/raw/`, `data/cleaned/`, `chroma/`, `__pycache__/`, `.venv/`
- `.env.example`: `LLM_*` placeholders only
- `rag/__init__.py`
- `rag/config.py`: `COLLECTION_NAME = "hdfc_mf_faq"`, `CHUNK_TOKENS` 256–400, `CHUNK_OVERLAP` 40–80, `TOP_K` 5, `SIMILARITY_THRESHOLD` placeholder, `CHROMA_PATH`, `EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`
- Stub files: `ingest.py`, `app.py`, empty `rag/load.py` … `guardrails.py` with `pass` or `NotImplementedError`
- `prompts/system.txt` empty placeholder
- `README.md` one-liner: “HDFC MF FAQ RAG — see implementation.md”

**Do not:** fetch URLs, download MiniLM usage beyond listing the model name, build UI.

**Done when**

- [ ] `python -c "from rag.config import COLLECTION_NAME"` works in a venv
- [ ] Layout matches architecture §8
- [ ] No secrets committed

### Cursor prompt — Phase 0

```
Implement Phase 0 only from implementation.md.

Read architecture.md §8, §9, §12.

Create the repo scaffold: venv-friendly requirements.txt, .gitignore, .env.example, rag/config.py with the locked knobs (MiniLM model name, Chroma path, collection hdfc_mf_faq, chunk size/overlap, top_k), stub rag modules and ingest.py/app.py, empty prompts/system.txt.

Do not fetch sources, ingest, retrieve, or build UI.

Stop when Phase 0 Done when checks pass. Summarize files created.
```

---

## Phase 1 — Source catalog

**Goal:** Allowlist CSV Cursor and ingest will trust. No fetch yet.

**Create `sources.csv` columns**

`url,title,scheme,plan,doc_type,priority`

- `scheme`: exact names from PRD (or empty for hubs/how-tos)
- `plan`: `Direct` for the 5 scheme pages
- `doc_type`: `scheme-page` | `listing` | `how-to` | `factsheet` (hub can be `listing` or `factsheet`)
- `priority`: `low` for listing/explore hubs; `high` for scheme pages, CAS, capital-gains how-to, factsheets

Seed the 15 PRD URLs. Add 0–10 more **only** if they are official HDFC/SEBI/AMFI (KIM/SID/factsheet PDFs or fee pages). Target **15–25** rows.

**Do not:** download pages.

**Done when**

- [ ] 15–25 rows, all public official URLs
- [ ] Five Direct scheme rows have `scheme` + `priority=high`
- [ ] Explore/index/hybrid listing rows are `priority=low`

### Cursor prompt — Phase 1

```
Implement Phase 1 only from implementation.md.

Read PRD.md corpus table and architecture.md document metadata.

Create sources.csv with the required columns. Seed all 15 PRD HDFC URLs with correct scheme/doc_type/priority. Listing/explore hubs = priority low. Do not fetch or parse HTML.

Stop when Phase 1 Done when checks pass.
```

---

## Phase 2 — Loading

**Goal:** Allowlist fetch → raw snapshot + cleaned text + sidecar metadata (`architecture.md` §5.1).

**Implement `rag/load.py`**

- Read `sources.csv` only (no other hosts).
- GET each URL; save `data/raw/` (html/pdf bytes).
- HTML: extract main content + headings + tables; strip nav/footer.
- PDF: extract text (if URL is pdf or you follow factsheet links — if Phase 2 HTML-only, document that PDFs are Phase 12).
- Write `data/cleaned/<id>.txt` + `<id>.json` with: `url`, `title`, `scheme`, `plan`, `doc_type`, `fetched_at`, `priority`.

**Do not:** chunk, embed, Chroma.

**Done when**

- [ ] Running the loader (function or small script) populates cleaned files for the 5 scheme pages
- [ ] Every cleaned doc has `url` + `fetched_at`
- [ ] Failures are logged per URL; one 404 does not abort the rest

### Cursor prompt — Phase 2

```
Implement Phase 2 only from implementation.md.

Read architecture.md §5.1.

Implement rag/load.py: fetch only sources.csv URLs, write data/raw and data/cleaned with required metadata JSON. Strip HTML chrome; keep headings and tables as text.

Do not chunk, embed, or write to Chroma.

Add a way to run load only (function called from ingest.py later is OK; a `if __name__` debug path is OK).

Stop when Phase 2 Done when checks pass. Note if scheme pages are JS-empty.
```

---

## Phase 3 — Chunking

**Goal:** Structure-aware chunks with scheme prefix (`architecture.md` §5.2).

**Implement `rag/chunk.py`**

- Input: cleaned text + metadata.
- Split by headings / double newlines / table blocks; then window to ~256–400 tokens with overlap 40–80 (`rag/config.py`).
- **Do not split a markdown/text table across chunks** if avoidable.
- Prefix every chunk:

  `Scheme: {scheme or None} | Doc: {doc_type} | Section: {heading}`

- Return list of `{text, url, scheme, doc_type, section, fetched_at, priority, title, plan, chunk_index}`.

**Do not:** embed or upsert.

**Done when**

- [ ] Unit-style check: two schemes produce prefixes with different `Scheme:` values
- [ ] Chunks are not whole hub pages as a single giant blob (listings may be coarser)
- [ ] Prefix is on **every** chunk

### Cursor prompt — Phase 3

```
Implement Phase 3 only from implementation.md.

Read architecture.md §5.2 and rag/config.py.

Implement rag/chunk.py: structure-aware splitting, token window and overlap from config, prefix Scheme | Doc | Section on every chunk. Keep tables intact when possible.

Do not call the embedding model or Chroma.

Add a small debug: chunk one cleaned file and print count + first 200 chars of 2 chunks.

Stop when Phase 3 Done when checks pass.
```

---

## Phase 4 — Embedding + Chroma store

**Goal:** Same MiniLM for docs; persistent Chroma (`architecture.md` §5.3–5.4).

**Implement**

- `rag/embed.py`: load `sentence-transformers/all-MiniLM-L6-v2` once; `embed_texts(list[str]) -> vectors`
- `rag/store.py`: persistent client `CHROMA_PATH`; collection `hdfc_mf_faq`; `reset_collection()` or upsert by `id = sha1(url + section + chunk_index)`; metadata keys exactly as architecture (Chroma metadata values must be scalars)

**Do not:** wire full ingest CLI yet (thin test OK); do not retrieve; do not LLM.

**Done when**

- [ ] Embedding dim is 384
- [ ] Can upsert 2 dummy chunks and `collection.count() >= 2` after reopen of the client
- [ ] Re-upsert same `id` does not duplicate

### Cursor prompt — Phase 4

```
Implement Phase 4 only from implementation.md.

Read architecture.md §5.3 and §5.4.

Implement rag/embed.py (all-MiniLM-L6-v2) and rag/store.py (persistent Chroma, collection hdfc_mf_faq, stable sha1 ids, metadata fields from architecture). Support wipe or upsert so re-ingest does not leave stale dupes.

Do not implement ingest.py end-to-end, retrieve, generate, or UI.

Prove with a short script or __main__: embed two strings, upsert, reload, count.

Stop when Phase 4 Done when checks pass.
```

---

## Phase 5 — Ingest CLI

**Goal:** One command runs load → chunk → embed → store (`architecture.md` §3 ingest).

**Implement `ingest.py`**

- Load all sources (or skip fetch if cleaned exists — flag `--skip-fetch` optional).
- Chunk all cleaned docs.
- Embed in batches.
- Reset or upsert entire collection.
- Print: docs loaded, chunks, collection count, persist path.

**Done when**

- [ ] `python ingest.py` completes against `sources.csv`
- [ ] `chroma/` directory exists and count > 0
- [ ] No network calls inside a later query path (ingest is the only crawler)

### Cursor prompt — Phase 5

```
Implement Phase 5 only from implementation.md.

Read architecture.md §3 ingest pipeline.

Wire ingest.py: load → chunk → embed → store using existing rag modules. Print stats. Re-ingest must not leave duplicate stale chunks.

Do not implement guardrails, retrieve, LLM, or UI.

Stop when Phase 5 Done when checks pass.
```

---

## Phase 6 — Guardrails

**Goal:** W1 at the edge (`architecture.md` §6.1). No retrieval.

**Implement `rag/guardrails.py`**

Order:

1. PII → refuse; do not return raw user text to logs; `refusal_reason=pii`
2. Advice/suitability → refuse + educational URL (constant official AMFI/SEBI/HDFC learn link)
3. Returns/performance compare → refuse + factsheet hub URL from `sources.csv` if possible
4. Named scheme not in the five → refuse listing the five names
5. Else `allow`

Return the same JSON shape as architecture §6.4 (`refusal: true`, `source_url` set).

**Done when**

- [ ] “Should I buy HDFC Flexi Cap?” → refusal, no crash
- [ ] Fake PAN/email in query → PII refusal
- [ ] “Expense ratio of HDFC Large Cap Fund?” → allow

### Cursor prompt — Phase 6

```
Implement Phase 6 only from implementation.md.

Read architecture.md §6.1 and §6.4 and PRD §6 refusal table.

Implement rag/guardrails.py with the ordered checks. Return the response JSON contract for refusals. Do not call Chroma or the LLM.

Add a few assert-style tests or a __main__ demo for buy-advice, PII, and a factual allow.

Stop when Phase 6 Done when checks pass.
```

---

## Phase 7 — Retrieval

**Goal:** Query embed + Chroma top-k + scheme filter + threshold (`architecture.md` §6.2).

**Implement `rag/retrieve.py`**

- Embed question with **same** `embed.py`
- Alias map: “large cap”, “elss”, “tax saver”, “flexi”, “mid cap”, “baf” / “balanced advantage” → canonical `scheme`
- `where` filter when scheme detected
- Post-filter `priority == low` unless too few results
- `top_k` from config
- If best score below threshold → empty hits (caller will “not in corpus”)
- Document whether Chroma returns distance vs similarity; implement threshold consistently

**Do not:** LLM.

**Done when**

- [ ] After ingest, query “ELSS lock-in” returns chunks whose prefix/metadata is ELSS Tax Saver (or how-to), not a random listing only
- [ ] Low-score garbage query returns no hits

### Cursor prompt — Phase 7

```
Implement Phase 7 only from implementation.md.

Read architecture.md §6.2.

Implement rag/retrieve.py using rag/embed.py and rag/store.py. Scheme alias filter, top_k 4-6, drop listing/low priority when possible, similarity threshold from config.

Do not call the LLM or build UI.

Include a __main__ that prints top chunks for: ELSS lock-in, expense ratio large cap, and a nonsense query.

Stop when Phase 7 Done when checks pass.
```

---

## Phase 8 — Generation

**Goal:** Context packing + system prompt; **app sets citation** (`architecture.md` §6.3–6.4).

**Implement**

- `prompts/system.txt`: facts-only, ≤3 sentences, only provided chunks, no advice, no return math, no invented URLs, say if missing
- `rag/generate.py`: pack chunks as specified; call LLM; parse answer text; **set `source_url` from rank-1 (or best used) chunk metadata**; `last_updated` = max `fetched_at`; never trust model URLs
- LLM behind a small adapter (env: Ollama or API). If no key, stub that returns “LLM not configured” **without** hallucinating facts — or skip generate and fail clearly

**Done when**

- [ ] Given two fake chunks with known URLs, output JSON uses the metadata URL
- [ ] Answer path does not run if hits are empty (that wiring can be Phase 9, but generate must not invent)

### Cursor prompt — Phase 8

```
Implement Phase 8 only from implementation.md.

Read architecture.md §6.3, §6.4, PRD answer format.

Write prompts/system.txt and rag/generate.py. Citation and last_updated are assigned in code from chunk metadata, not from the model. Use env for LLM. Empty retrieval must not produce a fake source.

Do not build Streamlit UI yet.

Stop when Phase 8 Done when checks pass.
```

---

## Phase 9 — Query service

**Goal:** Single function `ask(question) -> dict` (`architecture.md` query pipeline).

**Implement in `rag/pipeline.py` (new) or `app.py` without UI**

Flow: guardrails → if refuse return; retrieve → if empty “not in indexed official pages” + optional closest URL if you have one, **no LLM**; else generate → JSON.

**Done when**

- [ ] One Python call answers a factual question using Chroma
- [ ] Advice question never hits generate
- [ ] Empty retrieval never hits generate

### Cursor prompt — Phase 9

```
Implement Phase 9 only from implementation.md.

Read architecture.md §3 query pipeline and §6.

Wire ask(question) -> JSON: guardrails, retrieve, threshold empty path, generate. No UI.

Demonstrate three calls: factual, advice refusal, nonsense/not-in-corpus.

Stop when Phase 9 Done when checks pass.
```

---

## Phase 10 — Tiny UI

**Goal:** PRD §6 + architecture §7.

**Implement Streamlit (or Gradio) in `app.py`**

- Welcome line
- Banner: “Facts-only. No investment advice.”
- Disclaimer snippet from PRD
- 3 example questions (click-to-ask) from PRD
- Input + history **in memory only**
- Render: ≤3 sentence body, Source link, `Last updated from sources:`
- Always show `source_url` from JSON, not from parsed model text

**Do not:** login, persist chats, analytics with raw questions.

**Done when**

- [ ] `streamlit run app.py` (or equivalent) shows all UI elements
- [ ] Example click runs `ask()`
- [ ] Refusal and factual paths both show a link

### Cursor prompt — Phase 10

```
Implement Phase 10 only from implementation.md.

Read PRD.md §6 UI and architecture.md §7.

Build the tiny Streamlit (or existing UI choice) app in app.py calling ask(). Welcome, 3 examples, facts-only note, PRD disclaimer, citation + last updated from response JSON. In-memory chat only.

Do not add auth or extra pages.

Stop when Phase 10 Done when checks pass.
```

---

## Phase 11 — Assignment deliverables

**Goal:** PRD §11 artifacts.

**Create/update**

- `README.md`: setup (Python, venv, install, `ingest.py`, `app.py`), AMC + 5 schemes, known limits (architecture §11)
- `sources.csv` already exists; confirm 15–25 URLs (CSV **or** also `sources.md`)
- `sample_qa.md`: 5–10 items covering expense ratio, exit load, min SIP, ELSS lock-in, riskometer/benchmark, capital-gains how-to, **advice refusal**, **returns refusal**, **out-of-scope/unknown** — paste **actual** assistant outputs + links after a local run
- Disclaimer is in the UI (already)

**Done when**

- [ ] Someone else can ingest + run from README alone
- [ ] Sample file has 5–10 real Q&As with links

### Cursor prompt — Phase 11

```
Implement Phase 11 only from implementation.md.

Read PRD.md §11 and architecture.md §11 known limits.

Write README.md (setup, scope, limits). After running the app if possible, write sample_qa.md with 5-10 real Q&As including refusals. Do not invent sample answers if ingest was not run — say so and use placeholders only as a last resort.

Stop when Phase 11 Done when checks pass.
```

---

## Phase 12 — Tune and harden (only if needed)

**Goal:** Hit PRD success bar (≥8/10 factual, 100% citations, 100% policy).

**Do in order, only what evidence requires**

1. If HTML cleaned files lack TER/load/lock-in: add official PDF factsheet/KIM/SID rows to `sources.csv` and extend loader; re-ingest.
2. If wrong scheme: tighten alias map, prefixes, exclude `doc_type=listing` from default retrieve.
3. Tune `SIMILARITY_THRESHOLD` on `sample_qa.md`.
4. Latency: batch embeds already; no per-query crawl.

**Done when** PRD §12 success criteria hold on the sample set.

### Cursor prompt — Phase 12

```
Implement Phase 12 only from implementation.md.

Read architecture.md §11 and §12 and PRD.md §12.

Do not refactor for taste. Fix only evidenced issues: empty HTML → PDF ingest; wrong-scheme retrieval; threshold; listing noise.

Re-run sample questions. Report before/after.

Stop when Phase 12 Done when checks pass or list remaining gaps.
```

---

## Definition of done (whole product)

- [ ] Ingest and query are separate; all RAG stages exist as named modules
- [ ] MiniLM + Chroma `hdfc_mf_faq`
- [ ] Every answer has one metadata citation + last updated
- [ ] Guardrails catch advice / returns / PII without depending on the LLM
- [ ] Tiny UI per PRD
- [ ] README + sources list + sample Q&A

If Cursor starts Phase 10 during Phase 4, **stop it** and paste only that phase’s prompt again.
