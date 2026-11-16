# Model card — ScamShield India classifier

**Model:** `m1-logreg-tfidf-v1` (sklearn Pipeline: union of word 1–2-gram and char 3–5-gram
TF-IDF → balanced multinomial-ish LogisticRegression, `max_iter=2000`, `C=4.0`)
**LLM path:** `p1-2026-11` (Gemini 2.0 Flash JSON mode *or* offline `FallbackExplainer`; same output schema)
**Versions are emitted in every API response and stored with each record.**

## Intended use

Decision-support for Indian SMS/WhatsApp-style messages: "is this a scam, which type, how
risky, what are the red flags, EN/HI explanation." Used by the Telegram bot and `/v1/analyze`.

**Out of scope:** legal/financial advice; blocking or reporting actions (humans decide);
voice analysis (voice-clone *messages* are covered, audio is not); non-message content.

## Training data

| Source | Rows | Notes |
|---|---|---|
| Hand-written seeds (this repo) | ~280 | Real Lucknow/India context: SBI/HDFC/Paytm/CBI/TRAI lures, Hinglish |
| Synthetic templates, seeded RNG | ~1,500 | Slot-filled variants (bank, amount, link, date); prevents overfitting to exact strings |
| UCI SMS Spam Collection (2005/2011) | 2,247 | 747 English spam (→ `generic_spam`), 1,500 ham; real-world grounding |
| **Total train** | **2,487** (15% holdout stratified) | See `data/scripts/build_dataset.py` |

The **golden set** (`data/golden/golden_set.csv`, 80 messages: 65 scam across 13 types +
15 safe) is hand-written, disjoint from training (enforced + tested), and fixed.

## Evaluation (measured 2026-11-16, this workspace)

| System | Accuracy | Precision (scam) | Recall (scam) | F1 (scam) | Macro F1 |
|---|---|---|---|---|---|
| Baseline ML | 88.75% | **100%** | 86.15% | 92.56% | 84.74% |
| LLM fallback (offline) | 87.5% | 95.08% | 89.23% | 92.06% | 81.33% |
| **Combined (ML+LLM+red flags)** | **95.0%** | **95.52%** | **98.46%** | **96.97%** | **91.34%** |

Combined confusion matrix: TP 64 · FP 3 · FN 1 · TN 12.
Holdout (synthetic-adjacent, optimistic, for reference only): accuracy 98.4%, scam-F1 98.5%.

Per-type accuracy (combined, n=5 each): kyc_update 100%, upi_refund 100%, investment_scam 100%,
fake_delivery 80%, lottery_prize 80%, voice_clone 80%, bank_account_block 80%, electricity_bill 80%,
fake_job_offer 80%, digital_arrest 60%, government_impersonation 60%, loan_app 60%,
**generic_spam 20%** (mostly re-typed as the specific scam it resembles — harmless for the
scam/safe verdict, but reported honestly).

Reproduce: `make evaluate` → `docs/results.md` + `models/eval_results.json`.

## Known failure modes

- **"Weekend getaway — ₹2,499 including stay"** → predicted safe; no risk markers, not in any
  training cluster (accepted FN, Medium-risk phrasing absent).
- **Legit bank messages containing "OTP"** are the dangerous class; mitigated by the
  negation guard ("never share OTP" no longer flags) and by keeping `otp_request` critical
  only when *directed at the user* ("share/send your OTP").
- **Generic spam** without a specific lure is under-specified by design (low priority).
- **Hindi Devanagari** coverage is keyword/pattern-level; ML handles romanized Hinglish better.

## Limitations (read before judging)

- Training data is largely synthetic + 2005-era English SMS. **Real-world precision/recall will
  differ** — measure on consented live data before any production claim.
- Golden set is small (80) and was authored by the builder; it is a regression gate, not a
  field study.
- No online learning; feedback (`/v1/feedback`) is collected for later human review only.
- Evolving scam language (new brands, new scripts) needs periodic retraining; drift visible in
  `scamshield_analyses_total{scam_type}` shifts vs. prior months.

## Ethics & user safety

Decision-support, never enforcement. Every response carries a disclaimer + cybercrime.gov.in /
1930. Scammers' victims may paste OTPs under duress — the scrubber masks them before storage.
No profiling, no user accounts, no selling data. The system prefers *false safe* caution in
wording ("no known patterns") over certainty claims.
