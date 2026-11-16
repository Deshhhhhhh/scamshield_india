"""SQLite storage (local/free-tier friendly). Parameterized queries only.

Privacy contract: the raw message is NEVER written here — only its SHA-256 hash
(for dedup) and the scrubbed text. See docs/threat-model.md §3.
"""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Iterable
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id            TEXT PRIMARY KEY,
    created_at    TEXT NOT NULL,
    text_sha256   TEXT NOT NULL,
    scrubbed_text TEXT NOT NULL,
    label         TEXT NOT NULL,
    scam_type     TEXT NOT NULL,
    risk_score    INTEGER NOT NULL,
    band          TEXT NOT NULL,
    ml_type       TEXT,
    ml_proba      REAL,
    llm_used      INTEGER NOT NULL DEFAULT 0,
    llm_path      TEXT,
    red_flag_ids  TEXT,
    model_version TEXT,
    prompt_version TEXT,
    latency_ms    REAL
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at);
CREATE INDEX IF NOT EXISTS idx_analyses_type ON analyses(scam_type);

CREATE TABLE IF NOT EXISTS feedback (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id  TEXT NOT NULL REFERENCES analyses(id),
    correct      INTEGER NOT NULL,
    actual_label TEXT,
    note         TEXT,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS advisories (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    source     TEXT NOT NULL,
    url        TEXT UNIQUE NOT NULL,
    published  TEXT,
    category   TEXT,
    fetched_at TEXT NOT NULL
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())


def connect(db_path: str) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def save_analysis(db_path: str, row: dict) -> None:
    init_db(db_path)
    with connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO analyses
               (id, created_at, text_sha256, scrubbed_text, label, scam_type,
                risk_score, band, ml_type, ml_proba, llm_used, llm_path,
                red_flag_ids, model_version, prompt_version, latency_ms)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["id"],
                row.get("created_at") or _now(),
                row["text_sha256"],
                row["scrubbed_text"],
                row["label"],
                row["scam_type"],
                row["risk_score"],
                row["band"],
                row.get("ml_type"),
                row.get("ml_proba"),
                int(bool(row.get("llm_used"))),
                row.get("llm_path"),
                ",".join(row.get("red_flag_ids", [])),
                row.get("model_version"),
                row.get("prompt_version"),
                row.get("latency_ms"),
            ),
        )


def add_feedback(db_path: str, analysis_id: str, correct: bool, actual_label: str | None, note: str | None) -> bool:
    init_db(db_path)
    with connect(db_path) as conn:
        exists = conn.execute(
            "SELECT 1 FROM analyses WHERE id = ?",
            (analysis_id,),
        ).fetchone()
        if not exists:
            return False
        conn.execute(
            "INSERT INTO feedback(analysis_id, correct, actual_label, note, created_at) VALUES (?,?,?,?,?)",
            (analysis_id, int(correct), actual_label, (note or "")[:500], _now()),
        )
        return True


def fetch_stats(db_path: str, days: int = 90) -> dict:
    init_db(db_path)
    cutoff = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() - days * 86400))
    with connect(db_path) as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM analyses WHERE created_at >= ?",
            (cutoff,),
        ).fetchone()["c"]
        by_type = [
            dict(r)
            for r in conn.execute(
                "SELECT scam_type, COUNT(*) AS n FROM analyses"
                " WHERE created_at >= ? GROUP BY scam_type ORDER BY n DESC",
                (cutoff,),
            ).fetchall()
        ]
        by_band = [
            dict(r)
            for r in conn.execute(
                "SELECT band, COUNT(*) AS n FROM analyses WHERE created_at >= ? GROUP BY band", (cutoff,)
            ).fetchall()
        ]
        by_day = [
            dict(r)
            for r in conn.execute(
                "SELECT substr(created_at,1,10) AS day, COUNT(*) AS n,"
                " AVG(risk_score) AS avg_risk FROM analyses"
                " WHERE created_at >= ? GROUP BY day ORDER BY day",
                (cutoff,),
            ).fetchall()
        ]
        flags: dict[str, int] = {}
        for r in conn.execute(
            "SELECT red_flag_ids FROM analyses WHERE created_at >= ? AND red_flag_ids != ''",
            (cutoff,),
        ).fetchall():
            for fid in (r["red_flag_ids"] or "").split(","):
                if fid:
                    flags[fid] = flags.get(fid, 0) + 1
        top_flags = sorted(
            ({"flag": k, "n": v} for k, v in flags.items()),
            key=lambda d: d["n"] if isinstance(d["n"], int) else 0,
            reverse=True,
        )[:10]
        scam = conn.execute(
            "SELECT COUNT(*) AS c FROM analyses WHERE created_at >= ? AND label='scam'",
            (cutoff,),
        ).fetchone()["c"]
        fb = conn.execute(
            "SELECT COUNT(*) AS total, SUM(correct) AS correct"
            " FROM feedback f JOIN analyses a ON a.id = f.analysis_id"
            " WHERE a.created_at >= ?",
            (cutoff,),
        ).fetchone()
        advisories = conn.execute(
            "SELECT COUNT(*) AS c FROM advisories",
        ).fetchone()["c"]

    feedback_acc = None
    if fb and fb["total"]:
        feedback_acc = round(100.0 * (fb["correct"] or 0) / fb["total"], 1)
    return {
        "window_days": days,
        "total_analyzed": total,
        "scam_count": scam,
        "scam_share_pct": round(100.0 * scam / total, 1) if total else 0.0,
        "by_type": by_type,
        "by_band": by_band,
        "by_day": by_day,
        "top_red_flags": top_flags,
        "feedback_accuracy_pct": feedback_acc,
        "advisories_collected": advisories,
    }


def recent_advisories(db_path: str, limit: int = 25) -> list[dict]:
    init_db(db_path)
    with connect(db_path) as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT title, source, url, published, category FROM advisories"
                " ORDER BY COALESCE(published, fetched_at) DESC LIMIT ?",
                (limit,),
            ).fetchall()
        ]


def upsert_advisories(db_path: str, items: Iterable[dict]) -> int:
    init_db(db_path)
    inserted = 0
    with connect(db_path) as conn:
        for item in items:
            cur = conn.execute(
                "INSERT OR IGNORE INTO advisories(title, source, url, published, category, fetched_at)"
                " VALUES (?,?,?,?,?,?)",
                (
                    item["title"][:300],
                    item["source"][:120],
                    item["url"][:1000],
                    item.get("published"),
                    item.get("category"),
                    _now(),
                ),
            )
            inserted += cur.rowcount
    return inserted
