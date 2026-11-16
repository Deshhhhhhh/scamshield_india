# Privacy & data handling — ScamShield India

**Principle: the raw message never persists.** This document is the auditable summary of
what exists where. Threat analysis lives in `docs/threat-model.md`.

## What we collect

| Data | Where | Retained | Lawful basis / need |
|---|---|---|---|
| Scrubbed message text | SQLite `analyses.scrubbed_text` | Until user deletes DB (local demo: forever on your machine) | Service operation; product analytics on aggregate |
| sha256 of raw message | `analyses.text_sha256` | Same | Dedup of repeat forwards; abuse detection |
| Label, type, risk, band, red-flag ids, versions, latency | Same row | Same | Evaluation, dashboards, feedback loop |
| Feedback (id → correct?/note) | `feedback` table | Same | Quality monitoring only |
| Aggregated stats | `/v1/stats`, dashboard | Aggregate, ephemeral | Trend analytics |

## What we never collect or store

Raw message text · phone numbers · OTPs/PINs/CVV · Aadhaar · PAN · card numbers · UPI VPAs ·
emails · names matching intro patterns · URLs' paths/queries (domain kept) · IP addresses in DB
(IPs only in-memory for the 60-second rate-limit window).

## Controls

- Scrubber runs **before** storage and **before** the LLM (`scamshield/service.py`, single choke-point).
- `leak_check()` CI-tested on the scrubbed output; API test asserts raw phone absent in response **and DB**.
- Logs are JSON and carry `analysis_id`, never message content.
- Parameterized SQL only; schema has no raw column.
- Rate limiting is in-memory per-IP, 60 s window, discarded.

## Deletion & access

Local demo: delete `data/scamshield.db` to erase everything. On hosted deployments we would
honour deletion by `text_sha256` (provided by the user from their forward) without ever seeing
content. There is nothing else to export — that is the point.

## Regulatory alignment

Design follows data-minimisation and purpose limitation of India's **DPDP Act, 2023** and the
storage-side expectations of the Digital Personal Data Protection Rules. This is an
engineering posture, not legal advice; consult counsel before a public launch.
