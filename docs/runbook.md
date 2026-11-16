# Runbook — operating ScamShield India

Audience: whoever is on call (in a real deployment: you). Local demo path included.
Dashboards: Grafana `:3000` (docker-compose) · Streamlit `:8501` · API metrics `:8000/v1/metrics`.

## Quick start / restart

```bash
# local
uvicorn scamshield.main:app --host 0.0.0.0 --port 8000    # API
streamlit run dashboard/app.py                            # dashboard
# compose (full stack)
docker compose up --build -d
docker compose --profile demo run --rm seed                # optional demo data
# health
curl localhost:8000/v1/health
```

Expected healthy: `{"status":"ok","model_loaded":true,"database":"ok"}`.

## Failure modes

### 1. `model_loaded: false` in /v1/health
Cause: `models/scam_model.joblib` missing/unreadable.
Impact: API still answers (fallback explainer); accuracy drops ~7 pts on the golden set.
Fix: `python data/scripts/build_dataset.py && python -m scamshield.model --csv data/training/train.csv`,
restart API. Verify: `/v1/health` → `model_loaded: true`; run `make evaluate`.

### 2. LLM errors spiking (`scamshield_llm_calls_total{outcome="error"}`)
Cause: Gemini key invalid / quota / timeout (8 s).
Impact: none to availability — fallback answers; log shows `llm_fallback reason=…`.
Fix: unset `GEMINI_API_KEY` (fallback only) or correct the key/model; check `GeminiClient` timeouts.

### 3. API returning 429 for a legitimate user
Cause: per-IP 30 POST/min default hit (`SCAMSHIELD_RATE_LIMIT`).
Fix (demo): raise env var + restart. Fix (real): put behind CDN/WAF; keep app limit.

### 4. Database "locked" under compose
Cause: two writers / WAL not enabled (it is by default) or volume on network FS.
Fix: keep dashboard read-only (it is), ensure WAL (`PRAGMA journal_mode=WAL` auto), or move to
Postgres (see ADR 0001 revisit). `docker compose restart api dashboard`.

### 5. Advisory cron (GitHub Actions) failing
Checks: workflow log → fetch step. RSS source may be down/changed — swap URL in
`automation/fetch_advisories.py: RSS_SOURCES` (keep defusedxml + keyword filter).
The curated seed keeps the DB non-empty even with all feeds dead.

### 6. Feedback shows falling "correct" rate
Not an outage — this is your drift signal. Pull examples, add to golden set, retrain,
re-run `make evaluate`. Never "fix" by relaxing the CI gate.

### 7. Dashboard shows empty charts
Cause: DB empty or wrong `SCAMSHIELD_DB_PATH` between api and dashboard.
Fix: `docker compose --profile demo run --rm seed`, confirm both services share the
`scamshield-data` volume.

## SLOs (rolling 28d, local demo target)

| SLI | Target | Source |
|---|---|---|
| /v1/analyze success rate | ≥ 99% (excluding 4xx) | access logs / uvicorn |
| p95 latency | < 10 s (fallback < 100 ms typical) | `scamshield_analysis_latency_seconds` |
| Combined scam F1 (golden) | ≥ 0.90 | CI gate on every PR |
| `model_loaded` | true | `/v1/health` |

## Backup / restore (local demo)

Backup: `cp data/scamshield.db data/backups/scamshield-$(date +%F).db` (WAL: also copy `-wal` if present, or checkpoint first: `sqlite3 data/scamshield.db 'PRAGMA wal_checkpoint(FULL);'`).
Restore: stop services, replace file, start.

## Incident template

`Timeline · Impact (users, duration) · Root cause · Detection (which metric/log) · Fix ·
Follow-ups (test added? ADR updated?)`. File under `docs/incidents/` once public.
