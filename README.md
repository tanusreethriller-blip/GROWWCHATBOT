# HDFC Mutual Fund FAQ RAG

Facts-only chatbot for five HDFC Direct schemes. Answers are retrieved from official public pages (HDFC / SEBI / AMFI) and always include one source link. Not investment advice.

## Scope

**AMC:** HDFC Mutual Fund  

**Schemes (Direct):**

1. HDFC Flexi Cap Fund  
2. HDFC Large Cap Fund  
3. HDFC ELSS Tax Saver Fund  
4. HDFC Mid Cap Fund  
5. HDFC Balanced Advantage Fund  

## Setup

Python 3.11+ recommended.

```bash
cd BUILDHOURS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional LLM (otherwise the app uses an extractive fallback from retrieved chunks):

```bash
cp .env.example .env
# Ollama: LLM_PROVIDER=ollama, LLM_MODEL=llama3.2, run `ollama serve`
# or OpenAI-compatible: LLM_PROVIDER=openai, OPENAI_API_KEY=...
```

## Ingest (load → chunk → embed → Chroma)

```bash
python ingest.py
```

Re-use already downloaded pages:

```bash
python ingest.py --skip-fetch
```

This writes `data/raw/`, `data/cleaned/`, and persistent vectors in `chroma/` (gitignored). Collection name: `hdfc_mf_faq`. Embeddings: `sentence-transformers/all-MiniLM-L6-v2`.

## Run the UI

```bash
streamlit run app.py
```

## Pipeline modules

| Stage | File |
|---|---|
| Load | `rag/load.py` |
| Chunk | `rag/chunk.py` |
| Embed | `rag/embed.py` |
| Store | `rag/store.py` |
| Guardrails | `rag/guardrails.py` |
| Retrieve | `rag/retrieve.py` |
| Generate | `rag/generate.py` |
| Ask | `rag/pipeline.py` |

## Known limits

- Live `hdfcfund.com` pages are often blocked (HTTP 403 / Akamai). Ingest falls back to Internet Archive snapshots of the **same official URLs**. Citations still use the canonical HDFC/SEBI/AMFI URL, not the Wayback URL.
- Direct vs Regular: answers only state the plan if it appears in the indexed text.
- Charges change; `Last updated from sources` is the ingest date (`fetched_at`).
- Listing/explore pages are low priority and are down-ranked in retrieval.
- No buy/sell advice, no return calculations, no PII.

## Sources

See `sources.csv` (15–25 allowlisted URLs).
