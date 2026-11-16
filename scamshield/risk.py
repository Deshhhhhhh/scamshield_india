"""Risk fusion: combines ML probability, LLM/fallback verdict and red-flag weight.

Score 0–100. Bands: 0-24 Safe, 25-49 Medium, 50-74 High, 75-100 Critical.
Hard rule: any critical red flag (OTP/PIN request, digital arrest) forces scam,
regardless of what the models say — a false safe on those is unacceptable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .redflags import FlagMatch, has_critical_flag


@dataclass
class RiskResult:
    label: str  # "scam" | "safe"
    scam_type: str  # taxonomy id or "safe"
    risk_score: int  # 0-100
    band: str  # Safe | Medium | High | Critical


def band_for(score: int) -> str:
    if score < 25:
        return "Safe"
    if score < 50:
        return "Medium"
    if score < 75:
        return "High"
    return "Critical"


def combine(
    ml_type: str,
    ml_scam_proba: float,
    verdict_scam: bool,
    verdict_type: str,
    verdict_confidence: float,
    flags: list[FlagMatch],
) -> RiskResult:
    flag_weight = sum(f.weight for f in flags)
    flag_ids = [f.id for f in flags]
    ml_says_scam = ml_type != "safe"
    effective_scam = verdict_scam or ml_says_scam or has_critical_flag(flag_ids)

    if not effective_scam:
        safe_score = int(max(0, min(24, round(ml_scam_proba * 22 + min(8, flag_weight * 2)))))
        return RiskResult("safe", "safe", safe_score, band_for(safe_score))

    score_f = ml_scam_proba * 50
    if verdict_scam:
        score_f += 20 + verdict_confidence * 22  # 20–42
    if ml_says_scam and verdict_scam:
        score_f += 8  # agreement bonus
    score_f += min(25, flag_weight * 3.5)  # red-flag boost, capped

    if has_critical_flag(flag_ids):
        score_f = max(score_f, 68)  # critical floor

    score = int(max(25, min(97, round(score_f))))

    if verdict_scam and verdict_type != "safe":
        stype = verdict_type
    elif ml_says_scam:
        stype = ml_type
    else:
        stype = "generic_spam"
    return RiskResult("scam", stype, score, band_for(score))
