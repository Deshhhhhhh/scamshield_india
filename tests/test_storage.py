import uuid

import pytest

from scamshield import storage


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "t.db")
    storage.init_db(path)
    return path


def _row(**over):
    row = {
        "id": uuid.uuid4().hex,
        "text_sha256": uuid.uuid4().hex * 2,
        "scrubbed_text": "scrubbed sample [PHONE]",
        "label": "scam",
        "scam_type": "kyc_update",
        "risk_score": 80,
        "band": "Critical",
        "ml_type": "kyc_update",
        "ml_proba": 0.9,
        "llm_used": False,
        "llm_path": "fallback",
        "red_flag_ids": ["kyc_bait", "url_present"],
        "model_version": "m1",
        "prompt_version": "p1",
        "latency_ms": 12.5,
    }
    row.update(over)
    return row


def test_save_and_stats(db):
    storage.save_analysis(db, _row())
    storage.save_analysis(db, _row(label="safe", scam_type="safe", risk_score=5, band="Safe"))
    stats = storage.fetch_stats(db, days=1)
    assert stats["total_analyzed"] == 2
    assert stats["scam_count"] == 1
    assert stats["by_type"]
    assert any(f["flag"] == "kyc_bait" for f in stats["top_red_flags"])


def test_feedback_flow(db):
    row = _row()
    storage.save_analysis(db, row)
    assert storage.add_feedback(db, row["id"], True, None, None) is True
    assert storage.add_feedback(db, "nonexistent-id", True, None, None) is False


def test_advisory_upsert_dedupes(db):
    item = {
        "title": "RBI advisory",
        "source": "RBI",
        "url": "https://www.rbi.org.in/x",
        "published": "2024-10-15",
        "category": "digital_arrest",
    }
    assert storage.upsert_advisories(db, [item]) == 1
    assert storage.upsert_advisories(db, [item]) == 0
    assert len(storage.recent_advisories(db)) == 1


def test_no_raw_text_column(db):
    import sqlite3

    with sqlite3.connect(db) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(analyses)")}
    assert "raw_text" not in cols
    assert "text_sha256" in cols and "scrubbed_text" in cols
