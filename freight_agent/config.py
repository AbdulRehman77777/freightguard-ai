"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from .exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class Settings:
    api_key: str
    model: str
    provider: str = "groq"
    timeout_seconds: float = 60.0
    max_retries: int = 2


def load_settings(*, require_api_key: bool = True) -> Settings:
    """Load settings from .env/environment and validate their ranges."""
    load_dotenv()
    provider = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    providers = {
        "groq": (
            "GROQ_API_KEY",
            "GROQ_MODEL",
            "openai/gpt-oss-20b",
            "GROQ_TIMEOUT_SECONDS",
        ),
        "openai": (
            "OPENAI_API_KEY",
            "OPENAI_MODEL",
            "gpt-4o-mini",
            "OPENAI_TIMEOUT_SECONDS",
        ),
    }
    if provider not in providers:
        raise ConfigurationError("LLM_PROVIDER must be either 'groq' or 'openai'.")

    key_name, model_name, default_model, timeout_name = providers[provider]
    api_key = os.getenv(key_name, "").strip()
    if require_api_key and not api_key:
        raise ConfigurationError(
            f"{key_name} is not configured for LLM_PROVIDER={provider}. "
            "Copy .env.example to .env and add a valid key."
        )

    model = os.getenv(model_name, default_model).strip()
    if not model:
        raise ConfigurationError(f"{model_name} must not be blank.")

    try:
        timeout = float(os.getenv(timeout_name, "60"))
        retries = int(os.getenv("MAX_EXTRACTION_RETRIES", "2"))
    except ValueError as exc:
        raise ConfigurationError("Timeout and retry settings must be numeric.") from exc
    if timeout <= 0 or timeout > 300:
        raise ConfigurationError(f"{timeout_name} must be between 0 and 300.")
    if retries < 0 or retries > 5:
        raise ConfigurationError("MAX_EXTRACTION_RETRIES must be between 0 and 5.")
    return Settings(
        api_key=api_key,
        model=model,
        provider=provider,
        timeout_seconds=timeout,
        max_retries=retries,
    )
