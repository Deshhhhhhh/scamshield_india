"""FastAPI application. Versioned API: everything lives under /v1.

Security posture (see docs/threat-model.md):
  * untrusted input → scrubbed before use, length-capped, schema-validated
  * per-IP token-bucket rate limit (429 on excess)
  * security headers on every response
  * no stack traces in error responses
  * raw message never logged or persisted
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import Response as RawResponse

from . import __version__, storage
from .config import settings
from .metrics import FEEDBACK_TOTAL, RATE_LIMIT_HITS, render_metrics
from .observability import get_logger
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
)
from .service import analyze_message, model_status

log = get_logger(__name__)

_bucket: dict[str, deque[float]] = defaultdict(deque)


def _rate_limit_ok(key: str, limit: int, window_s: float = 60.0) -> bool:
    now = time.time()
    dq = _bucket[key]
    while dq and dq[0] < now - window_s:
        dq.popleft()
    if len(dq) >= limit:
        return False
    dq.append(now)
    return True


def create_app() -> FastAPI:
    app = FastAPI(
        title="ScamShield India API",
        version=__version__,
        description=(
            "Detect scam messages (fake KYC, UPI refund, digital arrest, voice clones, "
            "fake jobs) with ML + LLM, explain red flags in English/Hindi, and track "
            "trends — without storing personal data."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.environment == "local" and ["*"] or ["https://scamshield.example.in"],
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        max_age=86400,
    )

    @app.middleware("http")
    async def security_and_limits(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        client = request.client.host if request.client else "unknown"
        if (
            request.url.path.startswith("/v1/")
            and request.method == "POST"
            and not _rate_limit_ok(
                client,
                settings.rate_limit_per_minute,
            )
        ):
            RATE_LIMIT_HITS.inc()
            return JSONResponse(
                {
                    "error": "rate_limited",
                    "detail": f"Limit {settings.rate_limit_per_minute} req/min. Try again shortly.",
                },
                status_code=429,
                headers={"Retry-After": "60", "X-Request-ID": rid},
            )
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 — never leak internals
            log.exception("unhandled_error", extra={"request_id": rid, "path": request.url.path})
            return JSONResponse(
                {
                    "error": "internal_error",
                    "detail": "Unexpected error. See server logs with the request id.",
                    "request_id": rid,
                },
                status_code=500,
                headers={"X-Request-ID": rid},
            )
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response

    @app.get("/v1/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        db_ok = "ok"
        try:
            storage.init_db(settings.db_path)
        except Exception:  # noqa: BLE001
            db_ok = "error"
        return HealthResponse(
            status="ok" if db_ok == "ok" else "degraded",
            version=__version__,
            model_loaded=model_status(),
            database=db_ok,
            environment=settings.environment,
        )

    @app.post("/v1/analyze", response_model=AnalyzeResponse, tags=["analyze"])
    def analyze(req: AnalyzeRequest) -> dict:
        return analyze_message(req.message, req.language)

    @app.post("/v1/feedback", response_model=FeedbackResponse, tags=["feedback"])
    def feedback(req: FeedbackRequest) -> FeedbackResponse:
        ok = storage.add_feedback(settings.db_path, req.analysis_id, req.correct, req.actual_label, req.note)
        FEEDBACK_TOTAL.labels(correct=str(req.correct).lower()).inc()
        if not ok:
            return JSONResponse(  # type: ignore[return-value]
                {"error": "not_found", "detail": "analysis_id not found"},
                status_code=404,
            )
        return FeedbackResponse(status="recorded")

    @app.get("/v1/stats", tags=["analytics"])
    def stats(days: int = 90) -> dict:
        days = max(1, min(days, 365))
        return storage.fetch_stats(settings.db_path, days)

    @app.get("/v1/advisories", tags=["analytics"])
    def advisories(limit: int = 25) -> dict:
        limit = max(1, min(limit, 100))
        return {"advisories": storage.recent_advisories(settings.db_path, limit)}

    @app.get("/v1/metrics", include_in_schema=False)
    def metrics() -> RawResponse:
        body, content_type = render_metrics()
        return RawResponse(content=body, media_type=content_type)

    @app.get("/", include_in_schema=False)
    def root() -> dict:
        return {"service": "ScamShield India", "version": __version__, "docs": "/docs", "health": "/v1/health"}

    return app


app = create_app()
