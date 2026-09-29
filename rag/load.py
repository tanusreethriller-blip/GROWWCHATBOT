"""Load allowlisted official pages into data/raw and data/cleaned."""

from __future__ import annotations

import csv
import json
import re
import time
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from rag.config import CLEANED_DIR, RAW_DIR, SOURCES_CSV, USER_AGENT, WAYBACK_PREFIX


def safe_id(url: str) -> str:
    parsed = urlparse(url)
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", f"{parsed.netloc}{parsed.path}")
    return slug.strip("_")[:180]


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()
    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines: list[str] = []
    for el in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "th", "td", "caption"]):
        text = " ".join(el.get_text(" ", strip=True).split())
        if text:
            if el.name in {"h1", "h2", "h3", "h4"}:
                lines.append(f"\n## {text}\n")
            else:
                lines.append(text)
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 80:
        fallback = " ".join(main.get_text(" ", strip=True).split())
        return fallback
    return text


def _pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts = []
    for i, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        parts.append(f"## Page {i}\n{extracted.strip()}")
    return "\n\n".join(parts).strip()


def _get_with_wayback(client: httpx.Client, url: str) -> httpx.Response:
    """Live fetch first; Akamai often 403s, then use Wayback of the same official URL."""
    live = client.get(url)
    if live.status_code == 200 and len(live.content) > 500:
        return live
    last_exc: Exception | None = None
    for attempt in range(4):
        try:
            archive = client.get(f"{WAYBACK_PREFIX}{url}")
            if archive.status_code == 429:
                time.sleep(8 * (attempt + 1))
                continue
            archive.raise_for_status()
            if len(archive.content) < 200:
                raise RuntimeError(f"empty archive snapshot for {url}")
            print(f"[load] wayback fallback for {url} (live HTTP {live.status_code})")
            return archive
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(4 * (attempt + 1))
    raise last_exc or RuntimeError(f"archive fetch failed for {url}")


def load_catalog(path: Path | None = None) -> list[dict[str, str]]:
    csv_path = path or SOURCES_CSV
    rows: list[dict[str, str]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("url") or "").strip()
            if not url:
                continue
            rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def fetch_and_clean(rows: list[dict[str, str]] | None = None) -> list[dict]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    catalog = rows if rows is not None else load_catalog()
    fetched_at = date.today().isoformat()
    docs: list[dict] = []

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=45.0) as client:
        for row in catalog:
            url = row["url"]
            doc_id = safe_id(url)
            meta = {
                "url": url,
                "title": row.get("title") or url,
                "scheme": row.get("scheme") or "",
                "plan": row.get("plan") or "",
                "doc_type": row.get("doc_type") or "listing",
                "fetched_at": fetched_at,
                "priority": row.get("priority") or "low",
            }
            try:
                resp = _get_with_wayback(client, url)
                content_type = resp.headers.get("content-type", "").lower()
                suffix = ".pdf" if "pdf" in content_type or url.lower().endswith(".pdf") else ".html"
                raw_path = RAW_DIR / f"{doc_id}{suffix}"
                raw_path.write_bytes(resp.content)
                if suffix == ".pdf":
                    text = _pdf_text(raw_path)
                else:
                    text = _strip_html(resp.text)
            except Exception as exc:  # noqa: BLE001 — per-URL failure must not abort ingest
                print(f"[load] skip {url}: {exc}")
                continue

            if len(text.strip()) < 80:
                print(f"[load] skip {url}: too little text ({len(text)} chars)")
                continue
            time.sleep(2.0)

            cleaned_path = CLEANED_DIR / f"{doc_id}.txt"
            sidecar = CLEANED_DIR / f"{doc_id}.json"
            cleaned_path.write_text(text, encoding="utf-8")
            sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
            docs.append({**meta, "text": text, "id": doc_id})
            print(f"[load] {url} -> {len(text)} chars")
    return docs


def load_cleaned() -> list[dict]:
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    docs: list[dict] = []
    for sidecar in sorted(CLEANED_DIR.glob("*.json")):
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        text_path = sidecar.with_suffix(".txt")
        if not text_path.exists():
            continue
        docs.append({**meta, "text": text_path.read_text(encoding="utf-8"), "id": sidecar.stem})
    return docs


if __name__ == "__main__":
    fetch_and_clean()
