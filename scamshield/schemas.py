"""API contracts (Pydantic). The OpenAPI schema generated from these is the public spec."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalyzeRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=2000, description="The suspicious message (English/Hindi/Hinglish)"
    )
    language: str = Field("auto", pattern="^(auto|en|hi)$")

    @field_validator("message")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("message must not be blank")
        return v


class RedFlagOut(BaseModel):
    id: str
    label: str
    explanation: str


class AnalyzeResponse(BaseModel):
    analysis_id: str
    label: str
    scam_type: str
    scam_type_label: str
    risk_score: int
    band: str
    red_flags: list[RedFlagOut]
    explanation: str
    language: str
    model_version: str
    llm_path: str
    latency_ms: float
    disclaimer: str = (
        "ScamShield is a decision-support tool, not legal/financial advice. "
        "Never share OTPs or PINs. Report cyber fraud at cybercrime.gov.in or call 1930."
    )


class FeedbackRequest(BaseModel):
    analysis_id: str = Field(..., min_length=8, max_length=64)
    correct: bool
    actual_label: str | None = Field(None, max_length=64)
    note: str | None = Field(None, max_length=500)


class FeedbackResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    version: str
    model_loaded: bool
    database: str
    environment: str


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
