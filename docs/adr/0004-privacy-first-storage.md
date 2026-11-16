# ADR 0004 — Privacy by construction: scrubbed text + SHA-256 only

**Status:** accepted · 2026-11-16

**Context.** Scam messages are full of PII (phones, OTPs, Aadhaar). Storing them — even
"encrypted" — turns a demo DB into a breach liability and violates data minimisation under
India's DPDP Act 2023.

**Decision.** Raw messages are never persisted or logged. Storage keeps: scrubbed text,
sha256(raw) for dedup, classification, versions, latency. Logs carry analysis_id only.
The scrubber runs *before* storage AND before any LLM call.

**Trade-offs.**
- ✅ A full dump of the DB leaks no OTP, phone, Aadhaar, PAN or card — by construction, tested (`test_api.py::test_analyze_never_echoes_pii`, `leak_check`).
- ✅ DPDP-aligned minimisation; easier to explain to users and reviewers.
- ❌ Cannot re-show a user their history; cannot train on real raw text without consent.
- ❌ Hash allows equality-dedup but not content search — accepted.

**Rejected alternatives.** Store raw + encrypt at rest (key compromise defeats it; not
"no data stored"); hash-only storage with no scrubbed text (dashboard would show nothing;
scrubbed text is the minimum useful artefact).

**Revisit when.** Consented, opt-in "share raw for research" program exists with proper legal basis.
