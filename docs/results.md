# Evaluation results — golden set

Evaluated: 2026-11-16T18:14:03+0000  |  golden: 80 messages (65 scam / 15 safe, hand-written, disjoint from training)
Model: `m1-logreg-tfidf-v1`  Prompt: `p1-2026-11`  LLM: offline FallbackExplainer (no paid API)

| System | Accuracy | Precision (scam) | Recall (scam) | F1 (scam) | Macro F1 |
|---|---|---|---|---|---|
| Baseline ML (TF-IDF+LogReg) | 88.75% | 100.00% | 86.15% | 92.56% | 84.74% |
| LLM fallback (offline explainer) | 87.50% | 95.08% | 89.23% | 92.06% | 81.33% |
| Combined (ML + LLM + red flags) | 95.00% | 95.52% | 98.46% | 96.97% | 91.34% |

## Confusion (combined)
- TP=64 FP=3 FN=1 TN=12

## Combined: per-scam-type accuracy (top-1 scam_type correct)

| Scam type | n | Accuracy |
|---|---|---|
| Bank account block / suspension threat | 5 | 80% |
| Digital arrest / law-enforcement impersonation | 5 | 60% |
| Electricity bill disconnection scam | 5 | 80% |
| Fake delivery / courier scam | 5 | 80% |
| Fake job offer / task scam | 5 | 80% |
| Generic spam / unsolicited promotion | 5 | 20% |
| Government / regulator impersonation | 5 | 60% |
| Fake investment / guaranteed returns | 5 | 100% |
| Fake KYC update | 5 | 100% |
| Instant loan app / extortion | 5 | 60% |
| Lottery / prize / reward bait | 5 | 80% |
| Fake UPI refund / collect request | 5 | 100% |
| Voice-clone / family emergency | 5 | 80% |

## Errors (combined)

- true=scam pred=safe risk=11: “Weekend getaway to Goa at ₹2,499 per person including stay! Limited seats.…”
- true=safe pred=scam risk=60: “Your electricity bill of ₹1,850 for October is due on 28 Nov. Pay through official discom portal.…”
- true=safe pred=scam risk=58: “Your SBI statement is ready. Login to YONO to view. We never ask for OTP.…”
- true=safe pred=scam risk=63: “Your OTP for SBI net banking login is 392811. Never share OTP with anyone.…”

**Read this table honestly:** the golden set is small and templated-adjacent. Treat these as
engineering regression targets, not real-world guarantees. See `docs/model-card.md`.
