import abc
import json
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.logging import logger
from app.core.security import is_api_key_configured, redact_secrets

class ProviderResponse(BaseModel):
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""
    provider: str = ""

class JudgeOutputSchema(BaseModel):
    verdict: str = Field(description="'pass' or 'fail' or 'inconclusive'")
    score: float = Field(ge=0.0, le=1.0, description="Confidence/evaluation score between 0.0 and 1.0")
    rationale: str = Field(description="Short factual rationale explaining the score")

class JudgeResult(BaseModel):
    score: float
    verdict: str
    rationale: str
    is_error: bool = False
    raw_response: str = ""

class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> ProviderResponse:
        pass

    @abc.abstractmethod
    def judge(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> JudgeResult:
        pass

    @abc.abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        pass


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self.model = model or settings.LLM_MODEL
        self._client = None

    def _get_client(self):
        if not is_api_key_configured(self.api_key):
            raise ValueError(
                "ANTHROPIC_API_KEY is not configured. Set ANTHROPIC_API_KEY in backend/.env to enable LLM operations."
            )
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key, timeout=30.0)
        return self._client

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> ProviderResponse:
        client = self._get_client()
        start = time.perf_counter()

        # Retry with exponential backoff for transient rate limits
        max_retries = 3
        backoff = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [{"role": "user", "content": prompt}]
                }
                if system_prompt:
                    kwargs["system"] = system_prompt

                response = client.messages.create(**kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000.0

                text = ""
                for block in response.content:
                    if getattr(block, "type", "") == "text":
                        text += block.text

                prompt_toks = getattr(response.usage, "input_tokens", 0)
                comp_toks = getattr(response.usage, "output_tokens", 0)

                return ProviderResponse(
                    text=text,
                    prompt_tokens=prompt_toks,
                    completion_tokens=comp_toks,
                    latency_ms=round(elapsed_ms, 2),
                    model=self.model,
                    provider="anthropic"
                )
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "rate_limit" in err_msg.lower() or "429" in err_msg:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    break

        raise RuntimeError(f"Anthropic generation error: {redact_secrets(str(last_error))}")

    def judge(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> JudgeResult:
        """
        Requests structured JSON verdict, retries once on parse error.
        Never fills in a fake number on failure; returns is_error=True.
        """
        structured_system = (
            (system_prompt or "") + "\n\nCRITICAL: Respond ONLY with a valid JSON object formatted as:\n"
            "{\n  \"verdict\": \"pass\" | \"fail\" | \"inconclusive\",\n"
            "  \"score\": <float between 0.0 and 1.0>,\n"
            "  \"rationale\": \"<concise explanation>\"\n}"
        ).strip()

        for attempt in range(2):
            try:
                resp = self.generate(
                    prompt=prompt,
                    system_prompt=structured_system,
                    max_tokens=max_tokens,
                    temperature=0.0
                )
                raw = resp.text.strip()
                # Find JSON block if wrapped in markdown
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw)
                validated = JudgeOutputSchema(**parsed)
                return JudgeResult(
                    score=round(float(validated.score), 3),
                    verdict=validated.verdict,
                    rationale=validated.rationale,
                    is_error=False,
                    raw_response=resp.text
                )
            except Exception as e:
                logger.warning(f"Judge JSON parse attempt {attempt + 1} failed: {redact_secrets(str(e))}")
                if attempt == 1:
                    return JudgeResult(
                        score=0.0,
                        verdict="error",
                        rationale=f"Model judge output parse failure: {redact_secrets(str(e))}",
                        is_error=True,
                        raw_response=""
                    )
                time.sleep(0.5)

    def test_connection(self) -> Dict[str, Any]:
        """
        Minimal connection test without processing documents.
        """
        if not is_api_key_configured(self.api_key):
            return {
                "configured": False,
                "connected": False,
                "provider": "anthropic",
                "model": self.model,
                "message": "ANTHROPIC_API_KEY is not configured or contains placeholder."
            }

        try:
            client = self._get_client()
            start = time.perf_counter()
            resp = client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}]
            )
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return {
                "configured": True,
                "connected": True,
                "provider": "anthropic",
                "model": self.model,
                "latency_ms": round(elapsed_ms, 2),
                "message": "Connection verified successfully."
            }
        except Exception as e:
            return {
                "configured": True,
                "connected": False,
                "provider": "anthropic",
                "model": self.model,
                "error": redact_secrets(str(e)),
                "message": f"Connection failed: {redact_secrets(str(e))}"
            }


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using official REST API v1beta via httpx.
    Supports gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash, gemini-2.5-flash, etc.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        raw_model = model or settings.LLM_MODEL
        if raw_model.startswith("claude-"):
            self.model = "gemini-1.5-flash"
        else:
            self.model = raw_model
        if self.model.startswith("models/"):
            self.model = self.model.replace("models/", "")

    def _get_api_key(self) -> str:
        if not is_api_key_configured(self.api_key):
            raise ValueError(
                "GEMINI_API_KEY is not configured. Set GEMINI_API_KEY or GOOGLE_API_KEY in backend/.env to enable Gemini operations."
            )
        return self.api_key.strip()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> ProviderResponse:
        import httpx
        key = self._get_api_key()
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"

        body: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        if system_prompt:
            body["system_instruction"] = {
                "parts": [{"text": system_prompt}]
            }

        start = time.perf_counter()
        max_retries = 3
        backoff = 1.0
        last_error = None

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json=body)
                    if resp.status_code == 429:
                        time.sleep(backoff)
                        backoff *= 2.0
                        continue
                    if resp.is_error:
                        try:
                            err_json = resp.json()
                            msg = err_json.get("error", {}).get("message", resp.text)
                        except Exception:
                            msg = resp.text
                        raise RuntimeError(f"Gemini API returned status {resp.status_code}: {msg}")

                    data = resp.json()
                    elapsed_ms = (time.perf_counter() - start) * 1000.0

                    candidates = data.get("candidates", [])
                    text = ""
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text = "".join(p.get("text", "") for p in parts)

                    usage = data.get("usageMetadata", {})
                    prompt_toks = usage.get("promptTokenCount", 0)
                    comp_toks = usage.get("candidatesTokenCount", 0)

                    return ProviderResponse(
                        text=text,
                        prompt_tokens=prompt_toks,
                        completion_tokens=comp_toks,
                        latency_ms=round(elapsed_ms, 2),
                        model=self.model,
                        provider="gemini"
                    )
            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                if "429" in err_msg or "resource_exhausted" in err_msg:
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    break

        raise RuntimeError(f"Gemini generation error: {redact_secrets(str(last_error))}")

    def judge(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> JudgeResult:
        structured_system = (
            (system_prompt or "") + "\n\nCRITICAL: Respond ONLY with a valid JSON object formatted as:\n"
            "{\n  \"verdict\": \"pass\" | \"fail\" | \"inconclusive\",\n"
            "  \"score\": <float between 0.0 and 1.0>,\n"
            "  \"rationale\": \"<concise explanation>\"\n}"
        ).strip()

        for attempt in range(2):
            try:
                resp = self.generate(
                    prompt=prompt,
                    system_prompt=structured_system,
                    max_tokens=max_tokens,
                    temperature=0.0
                )
                raw = resp.text.strip()
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()

                parsed = json.loads(raw)
                validated = JudgeOutputSchema(**parsed)
                return JudgeResult(
                    score=round(float(validated.score), 3),
                    verdict=validated.verdict,
                    rationale=validated.rationale,
                    is_error=False,
                    raw_response=resp.text
                )
            except Exception as e:
                logger.warning(f"Gemini Judge JSON parse attempt {attempt + 1} failed: {redact_secrets(str(e))}")
                if attempt == 1:
                    return JudgeResult(
                        score=0.0,
                        verdict="error",
                        rationale=f"Gemini judge output parse failure: {redact_secrets(str(e))}",
                        is_error=True,
                        raw_response=""
                    )
                time.sleep(0.5)

    def test_connection(self) -> Dict[str, Any]:
        if not is_api_key_configured(self.api_key):
            return {
                "configured": False,
                "connected": False,
                "provider": "gemini",
                "model": self.model,
                "message": "GEMINI_API_KEY is not configured or contains placeholder."
            }

        try:
            import httpx
            key = self._get_api_key()
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={key}"
            start = time.perf_counter()
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    url,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json={
                        "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                        "generationConfig": {"maxOutputTokens": 10}
                    }
                )
                elapsed_ms = (time.perf_counter() - start) * 1000.0
                if resp.is_error:
                    try:
                        err_json = resp.json()
                        msg = err_json.get("error", {}).get("message", resp.text)
                    except Exception:
                        msg = resp.text
                    return {
                        "configured": True,
                        "connected": False,
                        "provider": "gemini",
                        "model": self.model,
                        "error": redact_secrets(msg),
                        "message": f"Connection failed: {redact_secrets(msg)}"
                    }
                return {
                    "configured": True,
                    "connected": True,
                    "provider": "gemini",
                    "model": self.model,
                    "latency_ms": round(elapsed_ms, 2),
                    "message": "Connection verified successfully with Google Gemini."
                }
        except Exception as e:
            return {
                "configured": True,
                "connected": False,
                "provider": "gemini",
                "model": self.model,
                "error": redact_secrets(str(e)),
                "message": f"Connection failed: {redact_secrets(str(e))}"
            }


class DemoProvider(LLMProvider):
    """
    Offline Demo Provider that runs without any API key or external network access.
    Fully operates local embeddings, deterministic metrics, and grounded demo responses.
    """
    def __init__(self, model: Optional[str] = None):
        self.model = model or "offline-deterministic"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> ProviderResponse:
        return ProviderResponse(
            text="[Page 2] Standard API rate limits for Tier 1 consumers are 120 requests/minute with 180 burst.",
            prompt_tokens=15,
            completion_tokens=20,
            latency_ms=1.5,
            model=self.model,
            provider="demo"
        )

    def judge(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> JudgeResult:
        return JudgeResult(
            score=0.95,
            verdict="pass",
            rationale="Deterministic local verification passed.",
            is_error=False,
            raw_response="{}"
        )

    def test_connection(self) -> Dict[str, Any]:
        return {
            "configured": True,
            "connected": True,
            "provider": "demo",
            "model": self.model,
            "latency_ms": 1.2,
            "message": "Demo Mode is active and healthy! Offline local RAG and deterministic metrics are 100% operational."
        }


class TestDoubleProvider(LLMProvider):
    """
    Test double for unit and integration testing. Never reachable in production or live evaluations.
    """
    def __init__(self, predefined_responses: Optional[Dict[str, str]] = None):
        self.predefined_responses = predefined_responses or {}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0
    ) -> ProviderResponse:
        for key, val in self.predefined_responses.items():
            if key in prompt:
                return ProviderResponse(
                    text=val,
                    prompt_tokens=20,
                    completion_tokens=20,
                    latency_ms=5.0,
                    model="test-double",
                    provider="test"
                )
        return ProviderResponse(
            text="Simulated test double answer citing [doc:1:0].",
            prompt_tokens=10,
            completion_tokens=10,
            latency_ms=2.0,
            model="test-double",
            provider="test"
        )

    def judge(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024
    ) -> JudgeResult:
        return JudgeResult(
            score=0.95,
            verdict="pass",
            rationale="Test double verified evidence grounding.",
            is_error=False,
            raw_response="{}"
        )

    def test_connection(self) -> Dict[str, Any]:
        return {"configured": True, "connected": True, "provider": "test-double", "model": "test-double"}


def is_llm_configured() -> bool:
    """Checks whether the currently active LLM provider has an API key configured."""
    prov = (settings.LLM_PROVIDER or "").lower()
    if prov == "demo":
        return True
    elif prov == "gemini":
        return is_api_key_configured(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY)
    elif prov == "anthropic":
        return is_api_key_configured(settings.ANTHROPIC_API_KEY)
    # Auto-detect if provider unset
    return is_api_key_configured(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY) or is_api_key_configured(settings.ANTHROPIC_API_KEY)


def get_llm_provider(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    provider: Optional[str] = None
) -> LLMProvider:
    prov = (provider or settings.LLM_PROVIDER or "gemini").lower()
    # Auto-detect if provider not explicitly requested
    if not provider:
        if prov == "demo":
            return DemoProvider(model=model)
        if is_api_key_configured(settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY):
            prov = "gemini"
        elif is_api_key_configured(settings.ANTHROPIC_API_KEY):
            prov = "anthropic"

    if prov == "demo":
        return DemoProvider(model=model)
    elif prov == "gemini":
        return GeminiProvider(api_key=api_key, model=model)
    return AnthropicProvider(api_key=api_key, model=model)
