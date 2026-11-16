"""Analysis pipeline: scrub → ML → LLM/fallback → fuse → persist → metrics."""

from __future__ import annotations

import time
import uuid

import joblib

from . import MODEL_VERSION, PROMPT_VERSION, storage
from .categories import type_labels
from .config import settings
from .llm import get_verdict
from .metrics import ANALYSES_TOTAL, ANALYSIS_LATENCY, PII_REDACTIONS, STORAGE_WRITES
from .model import predict
from .observability import get_logger
from .privacy import hash_text, scrub_text
from .redflags import find_red_flags
from .risk import combine

log = get_logger(__name__)

_model = None
_model_loaded = False


def get_model():
    global _model, _model_loaded
    if _model is None and not _model_loaded:
        _model_loaded = True
        try:
            _model = joblib.load(settings.model_path)
            log.info("model_loaded", extra={"path": str(settings.model_path)})
        except Exception as exc:  # noqa: BLE001 — degrade to fallback-only
            log.error("model_load_failed", extra={"reason": type(exc).__name__})
            _model = False
    return None if _model is False else _model


def analyze_message(message: str, language: str = "auto") -> dict:
    t0 = time.perf_counter()
    analysis_id = uuid.uuid4().hex

    scrubbed = scrub_text(message)
    for kind, n in scrubbed.redactions.items():
        PII_REDACTIONS.labels(kind=kind).inc(n)
    text = scrubbed.text

    # --- ML opinion (optional; degraded if artifact missing)
    pipe = get_model()
    if pipe is not None:
        ml_type, _ml_conf, ml_proba_map = predict(pipe, text)
        ml_scam_proba = 1.0 - ml_proba_map.get("safe", 0.0)
    else:
        ml_type, ml_scam_proba = "safe", 0.5

    # --- LLM opinion (Gemini if key, else deterministic fallback)
    verdict, used_remote, llm_path = get_verdict(text, language)

    # --- red flags (on scrubbed text)
    flags = find_red_flags(text)

    # --- fusion
    fused = combine(ml_type, ml_scam_proba, verdict.scam, verdict.scam_type, verdict.confidence, flags)

    lang_out = "hi" if language == "hi" else "en"
    if language == "auto":
        import re as _re

        lang_out = "hi" if _re.search(r"[ऀ-ॿ]", text) else "en"

    explanation = verdict.explanation
    latency_ms = round((time.perf_counter() - t0) * 1000, 2)

    try:
        storage.save_analysis(
            settings.db_path,
            {
                "id": analysis_id,
                "text_sha256": hash_text(message),  # hash of RAW, text stored scrubbed
                "scrubbed_text": text,
                "label": fused.label,
                "scam_type": fused.scam_type,
                "risk_score": fused.risk_score,
                "band": fused.band,
                "ml_type": ml_type,
                "ml_proba": round(ml_scam_proba, 4),
                "llm_used": used_remote,
                "llm_path": llm_path,
                "red_flag_ids": [f.id for f in flags],
                "model_version": MODEL_VERSION,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": latency_ms,
            },
        )
        STORAGE_WRITES.inc()
    except Exception as exc:  # noqa: BLE001 — storage failure must not break the API
        log.error("storage_write_failed", extra={"reason": type(exc).__name__})

    ANALYSES_TOTAL.labels(label=fused.label, scam_type=fused.scam_type).inc()
    ANALYSIS_LATENCY.observe(latency_ms / 1000.0)

    logger = log.info if fused.label == "safe" else log.warning
    logger(
        "analysis_complete",
        extra={
            "analysis_id": analysis_id,
            "label": fused.label,
            "scam_type": fused.scam_type,
            "risk_score": fused.risk_score,
            "band": fused.band,
            "llm_path": llm_path,
            "flags": [f.id for f in flags],
            "latency_ms": latency_ms,
            "pii_redactions": scrubbed.total_redactions,
        },
    )

    return {
        "analysis_id": analysis_id,
        "label": fused.label,
        "scam_type": fused.scam_type,
        "scam_type_label": type_labels(fused.scam_type, lang_out),
        "risk_score": fused.risk_score,
        "band": fused.band,
        "red_flags": [
            {
                "id": f.id,
                "label": f.label,
                "explanation": f.explanation_hi if lang_out == "hi" else f.explanation_en,
            }
            for f in flags
        ],
        "explanation": explanation,
        "language": lang_out,
        "model_version": MODEL_VERSION,
        "llm_path": llm_path,
        "latency_ms": latency_ms,
    }


def model_status() -> bool:
    return get_model() is not None


def db_path() -> str:
    return settings.db_path
