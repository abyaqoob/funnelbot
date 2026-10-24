"""Tests for pluggable LLM fallback providers."""
from unittest.mock import MagicMock, patch

from app.engine.llm_fallback import (
    GeminiLLMProvider,
    GroqLLMProvider,
    NoneLLMProvider,
    get_llm_provider,
)


def test_none_llm_provider():
    provider = NoneLLMProvider()
    assert provider.generate_reply("hello") is None


def test_groq_missing_key_graceful_fallback():
    provider = GroqLLMProvider(api_key=None)
    assert provider.generate_reply("how much is pricing?") is None


def test_groq_api_failure_handled_safely():
    provider = GroqLLMProvider(api_key="mock_invalid_key")
    with patch("httpx.post", side_effect=Exception("Connection timeout")):
        reply = provider.generate_reply("test query")
        assert reply is None  # Never crashes!


def test_groq_successful_call():
    provider = GroqLLMProvider(api_key="mock_valid_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "Our starter package is $499/mo."}}]
    }
    with patch("httpx.post", return_value=mock_resp):
        reply = provider.generate_reply("pricing")
        assert reply == "Our starter package is $499/mo."


def test_gemini_missing_key_graceful_fallback():
    provider = GeminiLLMProvider(api_key=None)
    assert provider.generate_reply("hello") is None


def test_gemini_api_failure_handled_safely():
    provider = GeminiLLMProvider(api_key="mock_key")
    with patch("httpx.post", side_effect=Exception("API limit reached")):
        reply = provider.generate_reply("test query")
        assert reply is None  # Never crashes!


def test_gemini_successful_call():
    provider = GeminiLLMProvider(api_key="mock_key")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "We deploy within 48 hours."}]}}]
    }
    with patch("httpx.post", return_value=mock_resp):
        reply = provider.generate_reply("timeline")
        assert reply == "We deploy within 48 hours."


def test_get_llm_provider_factory():
    assert isinstance(get_llm_provider("none"), NoneLLMProvider)
    assert isinstance(get_llm_provider("groq"), GroqLLMProvider)
    assert isinstance(get_llm_provider("gemini"), GeminiLLMProvider)
    assert isinstance(get_llm_provider("invalid"), NoneLLMProvider)
