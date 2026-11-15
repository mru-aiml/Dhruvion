"""Groq client for the DHRUVION mission assistant.

Uses Groq's OpenAI-compatible chat completions API. The backend remains the
source of truth: Groq only phrases tool evidence produced by the deterministic
allowlisted tools.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.logging_config import get_logger
from app.ai.exceptions import LLMError, LLMHealth, LLMTimeout, LLMUnavailable

logger = get_logger(__name__)


class GroqClient:
    """Synchronous OpenAI-compatible client for Groq."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self.timeout = float(timeout if timeout is not None else settings.LLM_TIMEOUT_S)

    # ------------------------------------------------------------------ auth
    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key or ''}",
        }

    # ----------------------------------------------------------------- health
    def list_models(self, timeout: Optional[float] = None) -> List[str]:
        url = f"{self.base_url}/models"
        try:
            response = httpx.get(url, headers=self._headers(), timeout=timeout or self.timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise LLMUnavailable(f"Groq is not reachable at {self.base_url}: {exc}") from exc
        models: List[str] = []
        for item in payload.get("data", []) or []:
            name = item.get("id") or item.get("model")
            if name:
                models.append(str(name))
        return models

    def health(self, force: bool = False) -> LLMHealth:
        if not settings.LLM_ENABLED:
            return LLMHealth(
                enabled=False,
                provider="groq",
                model=self.model,
                base_url=self.base_url,
                available=False,
                error="LLM_ENABLED is false; deterministic tool responses remain available.",
            )
        if not self.api_key:
            return LLMHealth(
                enabled=True,
                provider="groq",
                model=self.model,
                base_url=self.base_url,
                available=False,
                error="GROQ_API_KEY is not configured; falling back to deterministic responses.",
            )
        try:
            models = self.list_models()
        except LLMUnavailable as exc:
            return LLMHealth(
                enabled=True,
                provider="groq",
                model=self.model,
                base_url=self.base_url,
                available=False,
                error=str(exc),
            )
        available = self.model in models or any(
            str(model).split("/")[-1] == self.model for model in models
        )
        return LLMHealth(
            enabled=True,
            provider="groq",
            model=self.model,
            base_url=self.base_url,
            available=available,
            models=models,
            error=None if available else f"Model '{self.model}' is not available in the Groq catalogue.",
        )

    # -------------------------------------------------------------------- chat
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: Optional[float] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        health = self.health()
        if not health.available:
            raise LLMUnavailable(health.error or "Configured Groq model is not available")

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": int((options or {}).get("num_predict") or settings.LLM_MAX_TOKENS),
            "stream": False,
        }
        if tools:
            body["tools"] = tools

        url = f"{self.base_url}/chat/completions"
        try:
            response = httpx.post(
                url,
                json=body,
                headers=self._headers(),
                timeout=timeout or self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeout(f"Groq model '{self.model}' timed out after {timeout or self.timeout:g}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Groq model request failed: {exc}") from exc
        except ValueError as exc:
            raise LLMError(f"Groq returned a non-JSON response: {exc}") from exc

        choices = payload.get("choices") or []
        message = choices[0].get("message", {}) if choices else {}
        content = str(message.get("content") or "").strip()
        if not content:
            raise LLMError("Groq returned an empty explanation")
        return {"role": "assistant", "content": content, "model": self.model}
