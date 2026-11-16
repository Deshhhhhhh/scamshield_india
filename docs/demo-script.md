# 2-minute demo script (screen recording)

**0:00–0:15 — Hook.** "Indians reported ₹22,845 crore lost to cyber fraud in 2024
(govt. data). AI makes fake-KYC and digital-arrest scams cheaper every week. Here's ScamShield."

**0:15–0:30 — Architecture (30s).** Show `docs/assets/architecture.svg` in README.
"Telegram bot is just a client of a versioned /v1/analyze API: scrubber → ML + LLM → risk
fusion → privacy-safe storage → dashboard. Advisory collector cron adds public RBI/I4C feeds daily."

**0:30–1:15 — Live demo (API).** Terminal:
```
$ curl -X POST localhost:8000/v1/analyze -d '{"message":"This is CBI Cyber Cell... Stay on the video call, do not tell anyone, transfer ₹50,000 now."}'
→ Critical, digital_arrest, 97/100, red flags: digital_arrest, secrecy (+explanation)
$ curl ... -d '{"message":"Your OTP is 392811. Never share OTP with anyone."}'
→ Safe — negation-aware, the scary-looking message is recognised as a legit bank SMS
```

**1:15–1:35 — Dashboard.** Streamlit `:8501`: trends line chart, scam-type bars,
top red flags, advisories tab, privacy tab ("what we store: hash + scrubbed text — no PII, ever").

**1:35–1:55 — Engineering proof.** Flash: CI run (ruff, mypy, 51 tests, coverage 89%,
golden-F1 gate), coverage report, `docs/results.md` table (95% acc / 97% F1 combined),
ADRs/threat-model file list. "This is how big-tech teams build: tested, observed, documented."

**1:55–2:00 — Close.** "ScamShield India: measurable, private, free to run. Report scams at
cybercrime.gov.in, call 1930."

Checklist before recording: `docker compose up --build -d && docker compose --profile demo run --rm seed`;
silence notifications; browser at 125% zoom; hide API tokens (`.env`); test the exact curl commands.
