"""Prometheus metrics. Scraped from /v1/metrics; visualised in Grafana (docker-compose)."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

ANALYSES_TOTAL = Counter(
    "scamshield_analyses_total",
    "Messages analyzed",
    ["label", "scam_type"],
)
ANALYSIS_LATENCY = Histogram(
    "scamshield_analysis_latency_seconds",
    "End-to-end analysis latency",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
LLM_CALLS = Counter(
    "scamshield_llm_calls_total",
    "LLM outcomes",
    ["outcome"],  # used | fallback | error
)
PII_REDACTIONS = Counter(
    "scamshield_pii_redactions_total",
    "PII items masked before storage/LLM",
    ["kind"],
)
FEEDBACK_TOTAL = Counter(
    "scamshield_feedback_total",
    "User feedback events",
    ["correct"],
)
RATE_LIMIT_HITS = Counter(
    "scamshield_rate_limit_hits_total",
    "Requests rejected by rate limiter",
)
STORAGE_WRITES = Counter(
    "scamshield_storage_writes_total",
    "Rows written to storage",
)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
