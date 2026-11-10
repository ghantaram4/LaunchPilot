from __future__ import annotations

import json
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from filelock import FileLock

from .config import DATA
from .models import Handoff

RETENTION_SECONDS = 7 * 24 * 3600


class Store:
    def __init__(self, root: Path = DATA):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.campaigns = self.root / "campaigns"
        self.campaigns.mkdir(exist_ok=True)
        self.lock = FileLock(str(self.root / "operations.lock"), timeout=2)
        with self.registry() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS campaigns (id TEXT PRIMARY KEY, created REAL, expires REAL)")

    @contextmanager
    def registry(self):
        conn = sqlite3.connect(self.root / "registry.sqlite")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def path(self, campaign_id: str) -> Path:
        try:
            if str(uuid.UUID(campaign_id)) != campaign_id:
                raise ValueError()
        except ValueError:
            raise Handoff("storage", "Invalid campaign identifier.", False) from None
        return self.campaigns / campaign_id

    def require(self, campaign_id: str):
        with self.registry() as conn:
            row = conn.execute("SELECT expires FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row or row[0] <= time.time():
            raise Handoff("retention", "Campaign missing or expired. Start a new campaign with consent.", False)

    @contextmanager
    def db(self, campaign_id: str):
        self.require(campaign_id)
        conn = sqlite3.connect(self.path(campaign_id) / "application.sqlite")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA secure_delete=ON")
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create(self, docs: list[dict], *, consent: bool, demo: bool = False, raw_files: list | None = None) -> str:
        if consent is not True:
            raise Handoff("consent", "Explicit consent is required before campaign/checkpoint writes or generation.", False)
        cid = str(uuid.uuid4())
        with self.lock:
            with self.registry() as conn:
                now = time.time()
                conn.execute("INSERT INTO campaigns VALUES (?,?,?)", (cid, now, now + RETENTION_SECONDS))
            folder = self.path(cid)
            folder.mkdir()
            with self.db(cid) as conn:
                conn.executescript("""
                    CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    CREATE TABLE calls (id INTEGER PRIMARY KEY, stage TEXT, input_hash TEXT, status TEXT,
                        started REAL, elapsed REAL DEFAULT 0, response TEXT, usage TEXT, error TEXT);
                    CREATE TABLE work (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL);
                """)
                values = {"docs": docs, "consent": {"accepted": True, "at": now,
                          "scope": "Source transmission to Nebius, paid generation and internal checkpoints"},
                          "demo": demo, "active_spent": 0.0, "run_started": None,
                          "max_attempts": 8, "max_seconds": 180.0}
                conn.executemany("INSERT INTO settings VALUES (?,?)", [(k, json.dumps(v)) for k, v in values.items()])
            if raw_files:
                uploads = folder / "uploads"
                uploads.mkdir()
                for i, (name, contents) in enumerate(raw_files):
                    suffix = Path(name).suffix.lower()
                    suffix = suffix if suffix in {".pdf", ".txt", ".csv"} else ".bin"
                    (uploads / f"source-{i}{suffix}").write_bytes(contents)
        return cid

    def get(self, cid: str, key: str):
        with self.db(cid) as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, cid: str, key: str, value):
        with self.db(cid) as conn:
            conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))

    def list(self) -> list[dict]:
        with self.registry() as conn:
            return [{"id": r[0], "created": r[1], "expires": r[2]} for r in conn.execute(
                "SELECT id,created,expires FROM campaigns WHERE expires>? ORDER BY created DESC", (time.time(),))]

    def calls(self, cid: str) -> list[dict]:
        with self.db(cid) as conn:
            return [dict(r) for r in conn.execute(
                "SELECT id,stage,status,elapsed,usage,error FROM calls ORDER BY id")]

    def work(self, cid: str) -> dict | None:
        with self.db(cid) as conn:
            row = conn.execute("SELECT payload FROM work WHERE id=1").fetchone()
        return json.loads(row[0]) if row else None

    def save_work(self, cid: str, value: dict):
        with self.db(cid) as conn:
            conn.execute("INSERT OR REPLACE INTO work VALUES (1,?)", (json.dumps(value),))

    def cleanup(self, now: float | None = None) -> dict:
        """Deletes only validated UUID campaign directories; exports live outside app-managed storage."""
        now = time.time() if now is None else now
        result = {"removed": 0, "errors": []}
        with self.lock:
            with self.registry() as conn:
                expired = list(conn.execute("SELECT id FROM campaigns WHERE expires<=?", (now,)))
                for (cid,) in expired:
                    target = self.path(cid).resolve()
                    if target.parent != self.campaigns.resolve():
                        raise RuntimeError("Retention target outside campaign directory")
                    try:
                        if target.exists():
                            shutil.rmtree(target)
                        conn.execute("DELETE FROM campaigns WHERE id=?", (cid,))
                        result["removed"] += 1
                    except OSError:
                        result["errors"].append(f"Cleanup could not delete expired campaign {cid}; close other app processes and retry cleanup.")
            # Compact the source-free registry so deleted IDs do not accumulate.
            with self.registry() as conn:
                conn.execute("VACUUM")
        return result
