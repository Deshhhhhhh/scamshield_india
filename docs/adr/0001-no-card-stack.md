# ADR 0001 — No-card stack (LocalStack, SQLite, fallback LLM, Streamlit)

**Status:** accepted · 2026-11-16

**Context.** Free tiers shrink constantly and AWS needs a card. The project must be
demonstrable by a student at zero cost and zero risk of charges, while still proving
cloud-shaped engineering.

**Decision.** Local-first free stack: SQLite (WAL) for records, Streamlit for the dashboard,
a deterministic offline LLM fallback (Gemini plugged in only via env var), Docker Compose
for the whole stack, and Terraform tested against LocalStack instead of a real account.

**Trade-offs.**
- ✅ ₹0 spend, no card, no surprise bills; fully reproducible demo.
- ✅ Terraform/infra skills still demonstrated and reviewable in code.
- ❌ Not cloud-load-tested; LocalStack ≠ production AWS (IAM nuances, quotas, cold starts).
- ❌ SQLite is single-node; fine for demo, wrong for multi-writer scale.

**Rejected alternatives.** (a) Real AWS free tier — needs a card, small but non-zero risk of
charges from misconfig; (b) paid LLM API — violates the zero-rupee constraint; (c) Supabase
free tier — would work, but SQLite keeps the demo self-contained and offline-capable; noted as
a drop-in replacement for hosted demos (see `README → Deployment`).

**Revisit when.** The project gets a public demo with real users — then Supabase/Neon
(Postgres) and a container host, still on free/hobby tiers.
