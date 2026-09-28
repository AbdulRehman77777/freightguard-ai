from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import openai
import pytest

from freight_agent.config import Settings, load_settings
from freight_agent.exceptions import ConfigurationError, DocumentExtractionError
from freight_agent.extractor import (
    GROQ_BASE_URL,
    GroqExtractionService,
    OpenAIExtractionService,
    create_extraction_service,
)
from freight_agent.schemas import ExtractionFreightDocument


def settings(provider="groq"):
    model = "openai/gpt-oss-20b" if provider == "groq" else "gpt-4o-mini"
    return Settings(
        api_key="test-key",
        model=model,
        provider=provider,
        timeout_seconds=1,
        max_retries=0,
    )


def test_client_uses_groq_endpoint():
    with patch("freight_agent.extractor.OpenAI") as client_class:
        GroqExtractionService(settings())
    assert client_class.call_args.kwargs["base_url"] == GROQ_BASE_URL


def test_openai_client_uses_official_endpoint():
    with patch("freight_agent.extractor.OpenAI") as client_class:
        OpenAIExtractionService(settings("openai"))
    assert "base_url" not in client_class.call_args.kwargs


@pytest.mark.parametrize("service_class", [GroqExtractionService, OpenAIExtractionService])
def test_successful_structured_response(valid_data, service_class):
    parsed = ExtractionFreightDocument.model_validate(valid_data)
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=parsed, output=[])
    provider = "groq" if service_class is GroqExtractionService else "openai"
    assert service_class(settings(provider), client).extract("document") == parsed
    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["text_format"] is ExtractionFreightDocument
    assert kwargs["input"][0]["role"] == "system"
    assert kwargs["input"][1] == {"role": "user", "content": "document"}


def test_missing_groq_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("freight_agent.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        load_settings()


def test_missing_openai_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("freight_agent.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigurationError, match="OPENAI_API_KEY"):
        load_settings()


def test_invalid_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unsupported")
    monkeypatch.setattr("freight_agent.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigurationError, match="groq.*openai"):
        load_settings()


@pytest.mark.parametrize(
    ("provider", "selected_key", "other_key"),
    [
        ("groq", "GROQ_API_KEY", "OPENAI_API_KEY"),
        ("openai", "OPENAI_API_KEY", "GROQ_API_KEY"),
    ],
)
def test_only_selected_provider_key_is_required(
    monkeypatch, provider, selected_key, other_key
):
    monkeypatch.setattr("freight_agent.config.load_dotenv", lambda: None)
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv(selected_key, "test-key")
    monkeypatch.delenv(other_key, raising=False)
    assert load_settings().provider == provider


@pytest.mark.parametrize(
    ("provider", "service_class"),
    [("groq", GroqExtractionService), ("openai", OpenAIExtractionService)],
)
def test_provider_factory(provider, service_class):
    assert isinstance(create_extraction_service(settings(provider)), service_class)


@pytest.mark.parametrize("service_class", [GroqExtractionService, OpenAIExtractionService])
def test_unavailable_response(service_class):
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=None, output=[])
    with pytest.raises(DocumentExtractionError, match="no complete"):
        service_class(settings(), client).extract("document")


@pytest.mark.parametrize("service_class", [GroqExtractionService, OpenAIExtractionService])
def test_api_exception(service_class):
    client = Mock()
    client.responses.parse.side_effect = RuntimeError("do not leak this")
    with pytest.raises(DocumentExtractionError, match="unexpectedly"):
        service_class(settings(), client).extract("document")


@pytest.mark.parametrize(
    ("provider", "service_class", "provider_name"),
    [
        ("groq", GroqExtractionService, "Groq"),
        ("openai", OpenAIExtractionService, "OpenAI"),
    ],
)
def test_provider_api_failure_is_safely_wrapped(provider, service_class, provider_name):
    request = httpx.Request(method="POST", url="https://example.test/responses")
    client = Mock()
    client.responses.parse.side_effect = openai.APIError(
        "provider details must not leak", request=request, body=None
    )
    with pytest.raises(DocumentExtractionError, match=f"{provider_name} API") as exc_info:
        service_class(settings(provider), client).extract("document")
    assert "provider details" not in str(exc_info.value)


def test_providers_return_equivalent_nullable_models(valid_data):
    valid_data["load_number"] = None
    parsed = ExtractionFreightDocument.model_validate(valid_data)
    results = []
    for provider, service_class in (
        ("groq", GroqExtractionService),
        ("openai", OpenAIExtractionService),
    ):
        client = Mock()
        client.responses.parse.return_value = SimpleNamespace(output_parsed=parsed, output=[])
        results.append(service_class(settings(provider), client).extract("document"))
    assert results[0] == results[1]
    assert results[0].load_number is None


def test_refusal_handling():
    refusal = SimpleNamespace(type="refusal", refusal="Cannot comply")
    output = [SimpleNamespace(content=[refusal])]
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=None, output=output)
    with pytest.raises(DocumentExtractionError, match="refused"):
        GroqExtractionService(settings(), client).extract("document")


@pytest.mark.parametrize(
    ("code", "message"),
    [
        ("insufficient_quota", "quota or billing"),
        ("credit_balance_exhausted", "quota or billing"),
        ("tokens_per_minute", "token rate limit"),
        ("rate_limit_exceeded", "request rate limit"),
    ],
)
def test_rate_limit_failures_are_safely_classified(code, message):
    request = httpx.Request(method="POST", url=f"{GROQ_BASE_URL}/responses")
    response = httpx.Response(status_code=429, request=request)
    error = openai.RateLimitError(
        "provider details must not leak",
        response=response,
        body={"code": code},
    )
    client = Mock()
    client.responses.parse.side_effect = error
    with pytest.raises(DocumentExtractionError, match=message) as exc_info:
        GroqExtractionService(settings(), client).extract("document")
    assert "provider details" not in str(exc_info.value)
