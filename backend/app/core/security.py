import re
from typing import Any

# Regex to catch typical API key patterns (e.g. AIzaSy..., AQ...., sk-ant-..., sk-...)
KEY_PATTERN = re.compile(r"(AIzaSy[a-zA-Z0-9_\-]{30,}|AQ\.[a-zA-Z0-9_\-]{20,}|sk-ant-[a-zA-Z0-9_\-]{10,}|sk-[a-zA-Z0-9_\-]{20,})")

def redact_secrets(text: Any) -> str:
    """Safely redact secret keys and tokens from strings, log messages, and error traces."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return KEY_PATTERN.sub("[REDACTED_API_KEY]", text)

def is_api_key_configured(key: str | None) -> bool:
    """Checks whether a valid API key string is present without exposing it."""
    if not key:
        return False
    stripped = key.strip()
    # Check that it is not a placeholder
    placeholders = {
        "",
        "your_anthropic_api_key_here",
        "your_gemini_api_key_here",
        "your_google_api_key_here",
        "your_key_here",
        "none"
    }
    if stripped.lower() in placeholders:
        return False
    return len(stripped) > 8
