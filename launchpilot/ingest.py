import csv
import hashlib
import io
import re
from pathlib import Path

from pypdf import PdfReader

from .models import FIELDS, Handoff

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 65000
ALIASES = {"event": "event_name", "event name": "event_name", "start time": "start_time",
           "end time": "end_time", "registration link": "registration_url", "registration url": "registration_url",
           "time zone": "timezone", "target audience": "audience", "cost": "price"}


def _text(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Handoff("extraction", "Use a UTF-8 TXT or CSV file; this file could not be decoded.", False) from None


def calendar(raw: bytes) -> list[dict]:
    if len(raw) > MAX_BYTES:
        raise Handoff("extraction", "Calendar exceeds 5 MB.", False)
    try:
        reader = csv.DictReader(io.StringIO(_text(raw)), strict=True)
        if not reader.fieldnames or "event_name" not in reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("headers")
        rows = list(reader)
        if not 1 <= len(rows) <= 100 or any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("rows")
        if any(len(str(row)) > MAX_CHARS for row in rows):
            raise ValueError("row length")
        return [{k: v.strip() for k, v in row.items()} for row in rows]
    except Handoff:
        raise
    except (csv.Error, ValueError):
        raise Handoff("extraction", "Malformed calendar. Use unique CSV headers including event_name and 1–100 complete rows.", False) from None


def extract(brief_name: str, raw: bytes, calendar_name: str, csv_raw: bytes, row_index: int = 0) -> list[dict]:
    if not raw or len(raw) > MAX_BYTES:
        raise Handoff("extraction", "Event brief must be nonempty and at most 5 MB.", False)
    suffix = Path(brief_name).suffix.lower()
    try:
        if suffix == ".txt":
            pages = [_text(raw)]
        elif suffix == ".pdf":
            reader = PdfReader(io.BytesIO(raw), strict=True)
            if reader.is_encrypted or len(reader.pages) > 30:
                raise ValueError("encrypted or too long")
            pages = [p.extract_text() or "" for p in reader.pages]
            if any(len(p.strip()) < 20 for p in pages):
                raise ValueError("page without extractable text")
        else:
            raise ValueError("extension")
        if not "".join(pages).strip() or sum(map(len, pages)) > MAX_CHARS:
            raise ValueError("text length")
    except Handoff:
        raise
    except Exception:
        raise Handoff("extraction", "Brief extraction failed. Upload a text-based PDF (≤30 pages, all pages readable) or UTF-8 TXT, up to 65,000 characters. Scans, encrypted or corrupt PDFs need a replacement.", False) from None
    rows = calendar(csv_raw)
    if not 0 <= row_index < len(rows):
        raise Handoff("extraction", "Select a calendar event row.", False)
    digest = hashlib.sha256(raw).hexdigest()
    docs = [{"id": f"brief:p{i}", "filename": Path(brief_name).name, "page": i, "row": 0,
             "sha256": digest, "text": text.strip()} for i, text in enumerate(pages, 1)]
    row = rows[row_index]
    docs.append({"id": f"calendar:r{row_index + 2}", "filename": Path(calendar_name).name,
                 "page": 0, "row": row_index + 2, "sha256": hashlib.sha256(csv_raw).hexdigest(),
                 "text": "\n".join(f"{k}: {v}" for k, v in row.items()), "fields": row})
    return docs


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold().rstrip(".")


def candidates(docs: list[dict]) -> dict[str, list[dict]]:
    found = {k: [] for k in FIELDS}
    for doc in docs:
        for line in doc["text"].splitlines():
            label, sep, value = line.partition(":")
            key = ALIASES.get(label.strip().casefold(), label.strip().casefold().replace(" ", "_"))
            if sep and key in found and value.strip():
                value = value.strip()
                if normalize(value) not in {"unknown", "tbd", "tbc", "n/a", "not confirmed", "pending"}:
                    found[key].append({"value": value, "source_ids": [doc["id"]], "quote": line})
    return found
