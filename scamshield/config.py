"""Runtime configuration from environment. No secrets in code."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: str = field(
        default_factory=lambda: os.environ.get("SCAMSHIELD_DB_PATH", str(ROOT / "data" / "scamshield.db"))
    )
    models_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("SCAMSHIELD_MODELS_DIR", str(ROOT / "models")))
    )
    model_file: str = field(default_factory=lambda: os.environ.get("SCAMSHIELD_MODEL_FILE", "scam_model.joblib"))
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.environ.get("SCAMSHIELD_RATE_LIMIT", "30")))
    max_message_chars: int = field(default_factory=lambda: int(os.environ.get("SCAMSHIELD_MAX_CHARS", "2000")))
    gemini_api_key: str | None = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY") or None)
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"))
    gemini_timeout_s: float = field(default_factory=lambda: float(os.environ.get("GEMINI_TIMEOUT_S", "8")))
    log_level: str = field(default_factory=lambda: os.environ.get("SCAMSHIELD_LOG_LEVEL", "INFO"))
    environment: str = field(default_factory=lambda: os.environ.get("SCAMSHIELD_ENV", "local"))

    @property
    def model_path(self) -> Path:
        return self.models_dir / self.model_file


settings = Settings()
