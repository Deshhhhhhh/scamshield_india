import sqlite3

from fastapi.testclient import TestClient

from scamshield.config import settings
from scamshield.main import app

client = TestClient(app)

DIGITAL_ARREST = (
    "This is CBI Cyber Cell. A money laundering case is registered against your Aadhaar. "
    "Stay on the video call, do not tell anyone, transfer ₹50,000 now."
)
SAFE_MSG = "Kal subah 7 baje gym milega? Main aa raha hoon."
OTP_LURE = "Sir, your KYC expired. Share your OTP now to reactivate your SBI account immediately."


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "degraded")
    assert "model_loaded" in body


def test_analyze_digital_arrest_is_scam():
    r = client.post("/v1/analyze", json={"message": DIGITAL_ARREST})
    assert r.status_code == 200
    body = r.json()
    assert body["label"] == "scam"
    assert body["risk_score"] >= 50
    assert body["red_flags"]
    assert body["scam_type"] != "safe"


def test_analyze_otp_lure_forces_scam():
    r = client.post("/v1/analyze", json={"message": OTP_LURE})
    body = r.json()
    assert body["label"] == "scam"
    assert any(f["id"] == "otp_request" for f in body["red_flags"])


def test_analyze_safe_message():
    r = client.post("/v1/analyze", json={"message": SAFE_MSG})
    assert r.status_code == 200
    assert r.json()["label"] == "safe"


def test_analyze_never_echoes_pii():
    raw = "Dear customer your SBI KYC expired. Call +91 9876543210. Your OTP is 556677. Update now."
    r = client.post("/v1/analyze", json={"message": raw})
    text = r.text
    assert "9876543210" not in text
    # DB must not contain raw PII either
    with sqlite3.connect(settings.db_path) as conn:
        row = conn.execute("SELECT scrubbed_text FROM analyses ORDER BY created_at DESC LIMIT 1").fetchone()
    assert "9876543210" not in (row[0] or "")


def test_blank_message_rejected():
    assert client.post("/v1/analyze", json={"message": "   "}).status_code == 422
    assert client.post("/v1/analyze", json={}).status_code == 422


def test_oversize_message_rejected():
    assert client.post("/v1/analyze", json={"message": "x" * 2001}).status_code == 422


def test_feedback_roundtrip():
    r = client.post("/v1/analyze", json={"message": DIGITAL_ARREST})
    aid = r.json()["analysis_id"]
    fb = client.post("/v1/feedback", json={"analysis_id": aid, "correct": True})
    assert fb.status_code == 200
    missing = client.post("/v1/feedback", json={"analysis_id": "doesnotexist123", "correct": True})
    assert missing.status_code == 404


def test_stats_endpoint():
    client.post("/v1/analyze", json={"message": DIGITAL_ARREST})
    r = client.get("/v1/stats", params={"days": 7})
    assert r.status_code == 200
    body = r.json()
    assert body["total_analyzed"] >= 1
    assert "by_type" in body and "top_red_flags" in body


def test_metrics_endpoint():
    r = client.get("/v1/metrics")
    assert r.status_code == 200
    assert b"scamshield_analyses_total" in r.content


def test_security_headers():
    r = client.get("/v1/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_openapi_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = set(r.json()["paths"])
    assert "/v1/analyze" in paths and "/v1/feedback" in paths


def test_rate_limiter_logic():
    from scamshield.main import _bucket, _rate_limit_ok

    _bucket.clear()
    key = "test-client-ratelimit"
    assert all(_rate_limit_ok(key, 3) for _ in range(3))
    assert not _rate_limit_ok(key, 3)
