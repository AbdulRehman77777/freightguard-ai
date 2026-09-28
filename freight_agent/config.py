"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    model: str = "openai/gpt-oss-20b"
    timeout_seconds: float = 60.0
    max_retries: int = 2


def load_settings(*, require_api_key: bool = True) -> Settings:
    """Load settings from .env/environment and validate their ranges."""
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise ConfigurationError(
            "GROQ_API_KEY is not configured. Copy .env.example to .env and add a valid key."
        )

    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
    if not model:
        raise ConfigurationError("GROQ_MODEL must not be blank.")

    try:
        timeout = float(os.getenv("GROQ_TIMEOUT_SECONDS", "60"))
        retries = int(os.getenv("MAX_EXTRACTION_RETRIES", "2"))
    except ValueError as exc:
        raise ConfigurationError("Timeout and retry settings must be numeric.") from exc
    if timeout <= 0 or timeout > 300:
        raise ConfigurationError("GROQ_TIMEOUT_SECONDS must be between 0 and 300.")
    if retries < 0 or retries > 5:
        raise ConfigurationError("MAX_EXTRACTION_RETRIES must be between 0 and 5.")
    return Settings(api_key=api_key, model=model, timeout_seconds=timeout, max_retries=retries)
