import pytest
from app.services.providers import GeminiProvider, get_llm_provider, is_llm_configured
from app.core.security import redact_secrets, is_api_key_configured

def test_gemini_key_validation_and_redaction():
    # Test valid Gemini API key format (AIzaSy...)
    gemini_key = "AIzaSyB1234567890abcdefghijklmnopqrstuv"
    assert is_api_key_configured(gemini_key) is True
    
    # Placeholder keys must return False
    assert is_api_key_configured("your_gemini_api_key_here") is False
    assert is_api_key_configured("your_google_api_key_here") is False
    assert is_api_key_configured("") is False
    
    # Redaction test
    redacted = redact_secrets(f"Call with key {gemini_key} completed")
    assert gemini_key not in redacted
    assert "[REDACTED_API_KEY]" in redacted

def test_gemini_provider_unconfigured_test_connection():
    provider = GeminiProvider(api_key="your_gemini_api_key_here", model="gemini-1.5-flash")
    result = provider.test_connection()
    assert result["configured"] is False
    assert result["connected"] is False
    assert result["provider"] == "gemini"

def test_get_llm_provider_factory():
    provider = get_llm_provider(provider="gemini", model="gemini-1.5-flash")
    assert isinstance(provider, GeminiProvider)
    assert provider.model == "gemini-1.5-flash"


def test_gemini_provider_mocked_success_connection(monkeypatch):
    from unittest.mock import MagicMock
    fake_key = "AIzaSyB1234567890abcdefghijklmnopqrstuv"
    provider = GeminiProvider(api_key=fake_key, model="gemini-1.5-flash")
    
    mock_resp = MagicMock()
    mock_resp.is_error = False
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "pong"}]}}],
        "usageMetadata": {"promptTokenCount": 2, "candidatesTokenCount": 2}
    }
    
    class MockClient:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, *args, **kwargs):
            return mock_resp
            
    import httpx
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: MockClient())
    
    res = provider.test_connection()
    assert res["configured"] is True
    assert res["connected"] is True
    assert res["provider"] == "gemini"
    assert "latency_ms" in res

