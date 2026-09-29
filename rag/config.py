from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COLLECTION_NAME = "hdfc_mf_faq"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_PATH = ROOT / "chroma"

CHUNK_TOKENS = 320
CHUNK_OVERLAP = 64
EMBED_BATCH_SIZE = 64
TOP_K = 5
# Chroma default space is L2; we convert to a 0–1-ish similarity. Tune in Phase 12.
SIMILARITY_THRESHOLD = 0.25

SOURCES_CSV = ROOT / "sources.csv"
RAW_DIR = ROOT / "data" / "raw"
CLEANED_DIR = ROOT / "data" / "cleaned"
SYSTEM_PROMPT_PATH = ROOT / "prompts" / "system.txt"

IN_SCOPE_SCHEMES = (
    "HDFC Flexi Cap Fund",
    "HDFC Large Cap Fund",
    "HDFC ELSS Tax Saver Fund",
    "HDFC Mid Cap Fund",
    "HDFC Balanced Advantage Fund",
)

EDUCATIONAL_URL = "https://www.amfiindia.com/investor-corner"
FACTSHEET_HUB_URL = "https://www.hdfcfund.com/mutual-funds/factsheets"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
WAYBACK_PREFIX = "https://web.archive.org/web/2025/"
