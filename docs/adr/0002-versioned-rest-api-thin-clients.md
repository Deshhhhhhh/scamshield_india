# ADR 0002 — Versioned REST API (`/v1/analyze`), thin clients

**Status:** accepted · 2026-11-16

**Context.** The first sketch had the Telegram bot classifying messages itself — logic
duplicated in every client and impossible to reuse for web/WhatsApp/IVR later.

**Decision.** All intelligence lives behind a versioned HTTP API. Clients (Telegram bot,
future web widget, curl) hold zero classification logic. OpenAPI spec auto-generated from
Pydantic models at `/openapi.json` (docs at `/docs`). Breaking changes ship as `/v2`.

**Trade-offs.**
- ✅ One place to test, observe, secure and rate-limit; bots/clients stay trivial.
- ✅ Contract-first: request/response schemas double as the public spec.
- ❌ Network hop adds ~1–5 ms and a deployable to run.
- ❌ Versioning discipline required (don't mutate `/v1` in place).

**Rejected alternatives.** Logic in the bot (duplication); GraphQL (overkill here);
"serverless function per client" (cost + drift).

**Revisit when.** A second client (web widget) is added — reuse as-is; only a `/v2` if the
response envelope changes incompatibly.
