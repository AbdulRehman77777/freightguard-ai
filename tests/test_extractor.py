from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import openai
import pytest

from freight_agent.config import Settings, load_settings
from freight_agent.exceptions import ConfigurationError, DocumentExtractionError
from freight_agent.extractor import GROQ_BASE_URL, GroqExtractionService
from freight_agent.schemas import ExtractionFreightDocument


def settings():
    return Settings(api_key="test-key", model="openai/gpt-oss-20b", timeout_seconds=1, max_retries=0)


def test_client_uses_groq_endpoint():
    with patch("freight_agent.extractor.OpenAI") as client_class:
        GroqExtractionService(settings())
    assert client_class.call_args.kwargs["base_url"] == GROQ_BASE_URL


def test_successful_structured_response(valid_data):
    parsed = ExtractionFreightDocument.model_validate(valid_data)
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=parsed, output=[])
    assert GroqExtractionService(settings(), client).extract("document") == parsed
    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["text_format"] is ExtractionFreightDocument
    assert kwargs["input"][0]["role"] == "system"
    assert kwargs["input"][1] == {"role": "user", "content": "document"}


def test_missing_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr("freight_agent.config.load_dotenv", lambda: None)
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        load_settings()


def test_unavailable_response():
    client = Mock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=None, output=[])
    with pytest.raises(DocumentExtractionError, match="no complete"):
        GroqExtractionService(settings(), client).extract("document")


def test_api_exception():
    client = Mock()
    client.responses.parse.side_effect = RuntimeError("do not leak this")
    with pytest.raises(DocumentExtractionError, match="unexpectedly"):
        GroqExtractionService(settings(), client).extract("document")


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
