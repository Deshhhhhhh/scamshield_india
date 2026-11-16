"""PII scrubbing. Nothing is stored or sent to an LLM before passing through here.

Guarantees (verified by tests):
  * phone numbers (+91 / 0091 / trunk-0 / bare 10-digit)
  * OTPs / one-time codes (keyword-anchored)
  * Aadhaar numbers (12 digits, grouped or bare)
  * PAN numbers, credit/debit-card-length digit runs, UPI VPAs, emails
  * URLs are reduced to [LINK:domain] — path/query (often token-bearing) are dropped
  * obvious name self-introductions ("my name is Rohan Verma")

Known limitations (documented in docs/model-card.md): free-text names that do not
follow keyword patterns are NOT detected; amounts under 9 digits are kept as-is.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

_PATTERNS: list[tuple[str, re.Pattern[str], str | None]] = [
    ("card", re.compile(r"(?<!\d)(?:\d[ -]?){13,19}\d(?!\d)"), "[CARD]"),
    ("aadhaar", re.compile(r"(?<!\d)[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"), "[AADHAAR]"),
    (
        "pan",
        re.compile(r"(?<![A-Z0-9])[ABCFGHLJPTF][A-Z]{4}\d{4}[A-Z](?![A-Z0-9])"),
        "[PAN]",
    ),
    (
        "upi_vpa",
        re.compile(
            r"(?<![\w.\-])[\w.\-]{2,}@(?:ok|ybl|ibl|axl|paytm|upi|okhdfcbank|oksbi|okicici|okaxis|apl|fam)"
            r"(?![\w.])",
            re.IGNORECASE,
        ),
        "[UPI-ID]",
    ),
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]{2,}"), "[EMAIL]"),
    # OTP anchored to a keyword so we don't eat legitimate amounts
    (
        "otp_anchored",
        re.compile(
            r"(?:otp|one[- ]?time[- ]?(?:password|code|pin)|verification code|secure code)"
            r"[^\d]{0,25}(\d{4,8})",
            re.IGNORECASE,
        ),
        None,  # handled by _scrub_otp to keep the keyword
    ),
    ("phone_plus91", re.compile(r"(?:\+91|0091)[\s.\-]?[6-9]\d{1,2}[\s.\-]?\d{3,4}[\s.\-]?\d{4}"), "[PHONE]"),
    ("phone_bare", re.compile(r"(?<!\d)[6-9]\d{4}[\s.\-]?\d{5}(?!\d)"), "[PHONE]"),
    ("phone_landline", re.compile(r"(?<!\d)0\d{2,4}[\s.\-]?\d{6,8}(?!\d)"), "[PHONE]"),
    ("long_number", re.compile(r"(?<!\d)\d{9,12}(?!\d)"), "[NUMBER]"),
    (
        "person_intro",
        re.compile(
            r"((?:my name is|i am|i'm|mera naam(?: hai)?|this is)\s+)[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
            re.IGNORECASE | re.UNICODE,
        ),
        None,
    ),  # handled specially to keep the lead-in phrase
    ("dear_name", re.compile(r"\b(dear|namaste|hi|hello)\s+[A-Z][a-z]{2,}\b"), None),
    ("url", re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE), None),  # keep domain only
]

_OTP_RE = re.compile(
    r"((?:otp|one[- ]?time[- ]?(?:password|code|pin)|verification code|secure code)[^\d]{0,25})(\d{4,8})",
    re.IGNORECASE,
)
_INTRO_RE = re.compile(
    r"((?:my name is|i am|i'm|mera naam(?: hai)?|this is)\s+)[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?",
    re.IGNORECASE | re.UNICODE,
)
_DEAR_RE = re.compile(r"\b(dear|namaste|hi|hello)\s+[A-Z][a-z]{2,}\b")
_URL_RE = re.compile(r"https?://([^/\s<>\"']+)[^\s<>\"']*", re.IGNORECASE)


@dataclass
class ScrubResult:
    text: str
    redactions: dict[str, int] = field(default_factory=dict)

    @property
    def total_redactions(self) -> int:
        return sum(self.redactions.values())

    def to_dict(self) -> dict:
        return {"text": self.text, "redactions": self.redactions}


def _count(redactions: dict[str, int], kind: str, n: int = 1) -> None:
    if n > 0:
        redactions[kind] = redactions.get(kind, 0) + n


def scrub_text(text: str) -> ScrubResult:
    """Mask PII in `text`. Pure function, safe to call on untrusted input."""
    redactions: dict[str, int] = {}
    out = text

    for kind, pattern, replacement in _PATTERNS:
        if kind == "otp_anchored":
            out, n = _OTP_RE.subn(lambda m: m.group(1) + "[OTP]", out)
            _count(redactions, "otp", n)
        elif kind == "person_intro":
            out, n = _INTRO_RE.subn(lambda m: m.group(1) + "[NAME]", out)
            _count(redactions, "name", n)
        elif kind == "dear_name":
            out, n = _DEAR_RE.subn(lambda m: m.group(1) + " [NAME]", out)
            _count(redactions, "name", n)
        elif kind == "url":
            out, n = _URL_RE.subn(lambda m: "[LINK:" + m.group(1).lower() + "]", out)
            _count(redactions, "url", n)
        else:
            assert replacement is not None
            out, n = pattern.subn(replacement, out)
            _count(redactions, kind, n)

    out = re.sub(r"[\s\u200b\u200c\u200d\u2060\ufeff]+", " ", out).strip()
    return ScrubResult(text=out, redactions=redactions)


def hash_text(raw_text: str) -> str:
    """Stable dedup hash of the RAW message. We store only this hash, never raw text."""
    normalized = re.sub(r"\s+", " ", raw_text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


_LEAK_CHECK = [
    re.compile(r"(?:\+91|0091)?[6-9]\d{9}"),
    re.compile(r"(?<!\d)\d{12}(?!\d)"),
    re.compile(r"\b\d{6}\b"),
]


def leak_check(text: str) -> bool:
    """True if the text still looks like it contains raw PII. Used by tests and CI gates."""
    return any(pat.search(text) for pat in _LEAK_CHECK)
