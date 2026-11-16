# 🛡️ ScamShield India

**AI that catches scam messages before they catch you** — fake KYC, UPI refund traps,
“digital arrest” calls, voice-cloned emergencies, fake jobs and guaranteed-return pitches.
Forward the message to a Telegram bot; get the scam type, a 0–100 risk score and the red
flags explained in plain English or Hindi. Built with the engineering practices big-tech
teams use: versioned API, tests at three levels, CI/CD, IaC, observability and a threat model.

[![CI](https://github.com/Deshhhhhhh/scamshield_india/actions/workflows/ci.yml/badge.svg)](https://github.com/Deshhhhhhh/scamshield_india/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Cost](https://img.shields.io/badge/cost-%E2%82%B90-orange)

> India reported **₹22,845.73 crore lost to cyber fraud in 2024**, across **~22.7 lakh NCRP
> reports**; digital-arrest scams alone accounted for **₹1,935 crore in 1.23 lakh cases**
> ([MHA/I4C data shared with Parliament](https://riskawareness.in/indias-cyber-fraud-crisis-escalates-36-lakh-cases-rs-22845-crore-lost-in-2024/) ·
> [annual series](https://getnyay.in/data/cyber-fraud) · [case study](https://udaipurtimes.com/crime/cyber-crime-explodes-in-india/cid17132832.htm)).
> AI is making these scams cheaper and more convincing — detection has to scale too.

---

## What it does

```
You forward a suspicious SMS/WhatsApp text to the bot
        │
        ▼
POST /v1/analyze  ──►  PII scrubber ──► ML (scikit-learn) ─┐
                          │                                 ├─► risk fusion ──► 0–100 + band
                          └────────────► LLM (Gemini) ──────┘        │
                                       (or offline fallback)         ▼
        Telegram reply ◄── verdict + red flags (EN/HI) ◄── FastAPI ──► SQLite (scrubbed text + sha256 only)
                                                                          │
                              Streamlit dashboard ◄── Pandas/SQL ◄─────────┘
                              Prometheus /metrics ──► Grafana
                              GitHub Actions cron ──► advisory collector (RBI / I4C / CERT-In)
```

- **Classifies** scam vs safe + **13 Indian scam types** (KYC update, UPI refund, fake job,
  digital arrest, voice clone, lottery, investment, delivery, electricity-bill, account-block,
  govt impersonation, loan app, generic spam).
- **Scores risk 0–100** (Safe / Medium / High / Critical) and **explains every red flag** in
  simple English or Hindi — e.g. “‘Digital arrest’ does not exist in Indian law…”.
- **Stores nothing personal**: phone/OTP/Aadhaar/PAN/UPI/links are masked before storage or any
  LLM call; only scrubbed text + sha256(raw) persist. DB schema has no raw-text column (test-enforced).
- **Dashboard**: scam types, trends over time, top red-flag patterns, collected advisories.
- **Advisory automation**: daily GitHub Actions cron ingests public RBI/I4C/CERT-In advisories.

## ⚡ Quickstart (zero-rupee)

Prereq: Python 3.11+ and `make` (or run the commands inside the Makefile directly).

```bash
git clone https://github.com/Deshhhhhhh/scamshield_india && cd scamshield_india
make setup                 # pip install -r requirements-dev.txt
make train                 # build dataset (UCI optional) + train baseline model
make test                  # 51 tests, ~89% coverage
uvicorn scamshield.main:app --reload   # API on :8000, docs at /docs
curl -X POST localhost:8000/v1/analyze -H 'Content-Type: application/json' -d \
  '{"message":"This is CBI. You are under digital arrest. Stay on the video call and transfer ₹50,000 now."}'
```

With Docker (recommended; trains the model inside the image):

```bash
docker compose up --build -d          # api :8000 · dashboard :8501 · prometheus :9090 · grafana :3000
docker compose --profile demo run --rm seed   # optional: 90 days of demo trends
```

Telegram bot: `@BotFather` → new bot → `export TELEGRAM_BOT_TOKEN=… SCAMSHIELD_API_URL=http://localhost:8000`
→ `python bot/telegram_bot.py`. Landing page: `landing/index.html` (replace GA4 ID + bot link).

AWS, without a card: `docker compose --profile aws up -d localstack && infra/README.md` →
Terraform (S3+DynamoDB+Lambda+HTTP API) applies against LocalStack. Real AWS is optional and
untouched by default. Free-tier limits change — check each service before you commit.

## 📡 API (v1)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/analyze` | Classify a message (≤2000 chars, EN/HI/Hinglish) → label, type, risk, red flags, explanation |
| POST | `/v1/feedback` | `{analysis_id, correct, note?}` — drift monitoring, never used for auto-training |
| GET | `/v1/stats?days=90` | Totals, per-type volumes, daily series, top red flags, feedback accuracy |
| GET | `/v1/advisories` | Latest collected public advisories |
| GET | `/v1/health` | Liveness + `model_loaded` |
| GET | `/v1/metrics` | Prometheus exposition |

OpenAPI auto-generated at `/openapi.json` (Swagger `/docs`, ReDoc `/redoc`). Errors are
`{error, detail?}` — no stack traces. POST endpoints are rate-limited (`429`, default 30/min/IP).

Example response (trimmed):

```json
{ "label": "scam", "scam_type": "digital_arrest", "risk_score": 97, "band": "Critical",
  "red_flags": [{"id": "digital_arrest", "label": "Fake police / CBI / digital-arrest call"},
                {"id": "secrecy", "label": "Tells you to keep it secret / stay on the line"}],
  "explanation": "‘Digital arrest’ does not exist in Indian law…", "latency_ms": 4.5 }
```

## 📊 Measured results (golden set, 80 hand-written messages, disjoint from training)

| System | Accuracy | Precision (scam) | Recall (scam) | F1 (scam) | Macro F1 |
|---|---|---|---|---|---|
| Baseline ML (TF-IDF + LogReg) | 88.75% | **100%** | 86.15% | 92.56% | 84.74% |
| LLM (offline fallback explainer) | 87.5% | 95.08% | 89.23% | 92.06% | 81.33% |
| **Combined (ML + LLM + red flags)** | **95.0%** | **95.52%** | **98.46%** | **96.97%** | **91.34%** |

TP 64 · FP 3 · FN 1 · TN 12. Combined per-type: 100% on kyc_update/upi_refund/investment_scam …
generic_spam only 20% (re-typed as the specific lure — harmless for the verdict; see model card).
Reproduce: `make evaluate`. **These are regression targets, not field guarantees — read
`docs/model-card.md` before quoting them anywhere.**

## 🏗️ Engineering (what “industry-ready” means here)

- **Tests ×3 levels** — unit (scrubber/red-flags/risk/storage), integration (API via TestClient
  incl. PII-absence assertions), evaluation harness with CI **golden-F1 ≥ 0.90 gate**.
- **CI/CD** — GitHub Actions: ruff + ruff-format, mypy, pytest (≥70% cov; actual 89%), pip-audit
  (advisory), Docker build. Dependabot for pip/actions/docker. See `.github/workflows/`.
- **Containers & IaC** — multi-stage `Dockerfile` (non-root, healthcheck), `docker-compose.yml`
  (api, dashboard, Prometheus, Grafana, profiles: `demo`, `aws`), Terraform for S3/DynamoDB(TTL,
  PITR, AES-256)/Lambda/HTTP API/least-privilege IAM, tested on LocalStack.
- **Observability** — structured JSON logs with `analysis_id`; Prometheus counters/histograms
  (analyses, latency, LLM outcome, PII redactions, rate-limit hits); provisioned Grafana dashboard.
- **Security** — threat model (`docs/threat-model.md`: prompt injection, PII, abuse, supply chain,
  SSRF, poisoning), prompt-injection defences (delimiters + JSON contract + pydantic + degrade),
  negated-match guard (“*never* share OTP” ≠ OTP request), security headers, no tracebacks.
- **Docs** — this README, architecture (SVG/mermaid), 6 ADRs (`docs/adr/`), runbook, model card,
  privacy, threat model, results, 2-min demo script.

## 🗂️ Repo map

```
scamshield/            core package: model, llm(+fallback), risk fusion, privacy, storage, api
data/scripts/          dataset builder (hand seeds + synthetic + UCI)   data/golden/  80-msg golden set
evaluation/            golden-set harness → docs/results.md             automation/    advisory cron
bot/ dashboard/ landing/  Telegram client · Streamlit · GA4 page         tests/       51 tests
infra/terraform/       AWS IaC (LocalStack-tested)                       docs/        ADRs, threat model, …
.github/workflows/     CI + daily advisory cron                          locustfile.py  load test
```

## ⚠️ Limitations & privacy (the honest section)

- **False positives exist**: legit “your OTP is…” bank alerts are the hard class; we added
  negation-aware matching but you should still expect occasional FPs (see model card: 3 on the
  golden set). **ScamShield never tells you to do anything — it just informs.**
- **Synthetic-heavy training** + 2005-era UCI ham/spam ⇒ real-world numbers will differ;
  the golden set is a regression gate, not a field study. No live PII was used, by design.
- **No raw personal data is stored** — only scrubbed text + sha256 hash (see `docs/privacy.md`,
  `docs/threat-model.md`). We also don’t know who you are; there are no accounts.
- LLM (when enabled) sees **scrubbed** text only; without a key it’s 100% on-device patterns.
- Free tiers/limits change; verify before relying on them. Report scams: **cybercrime.gov.in · 1930**.

## 🗺️ Roadmap

Consented real-world labelled set (replace golden) · Postgres + Supabase for hosted demo ·
Voice-note analysis (wav2vec) for voice-clone calls · WhatsApp Cloud API client · ONNX export
for on-device Android · Community red-flag contributions via PR with the F1 gate.

## 📄 License

MIT — see `LICENSE`. Data: SMS Spam Collection (UCI, public) for research use.

---

**Resume line:** “Built ScamShield India, an AI scam-detection pipeline with a Telegram bot,
ML + LLM classifier (**95% accuracy, 97% F1** on a hand-written Indian golden set), automated
public-advisory collection and an analytics dashboard — FastAPI, scikit-learn, Docker, CI-gated
tests (89% coverage), Terraform/LocalStack and a full threat model.”

*Made with ₹0 and unreasonable attention to detail. CheckFree-tier limits before you commit.*
