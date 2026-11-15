"""Minimal Ollama client for the DHRUVION mission assistant.

The client only handles model discovery and chat completion. It deliberately
does not know anything about mission data: every fact must arrive from the
deterministic tool layer in :mod:`app.ai.tools`. When the model is missing or
times out the caller keeps the deterministic answer and marks the response as a
fallback, so the assistant never invents a result to hide an unavailable model.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from app.ai.exceptions import LLMError, LLMHealth, LLMTimeout, LLMUnavailable
from app.ai.groq_client import GroqClient
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

HEALTH_CACHE_SECONDS = 10.0


class OllamaClient:
    """Thin synchronous wrapper around the Ollama HTTP API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        health_timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.LLM_MODEL
        self.timeout = float(timeout if timeout is not None else settings.LLM_TIMEOUT_S)
        self.health_timeout = float(
            health_timeout if health_timeout is not None else settings.LLM_HEALTH_TIMEOUT_S
        )
        self._lock = threading.Lock()
        self._health: Optional[LLMHealth] = None
        self._health_at = 0.0

    # ------------------------------------------------------------------ health
    def list_models(self, timeout: Optional[float] = None) -> List[str]:
        url = f"{self.base_url}/api/tags"
        try:
            response = httpx.get(url, timeout=timeout or self.health_timeout)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # network, JSON, or HTTP failure
            raise LLMUnavailable(f"Ollama is not reachable at {self.base_url}: {exc}") from exc
        models = []
        for item in payload.get("models", []) or []:
            name = item.get("name") or item.get("model")
            if name:
                models.append(str(name))
        return models

    def health(self, force: bool = False) -> LLMHealth:
        if not settings.LLM_ENABLED:
            health = LLMHealth(
                enabled=False,
                provider=settings.LLM_PROVIDER,
                model=self.model,
                base_url=self.base_url,
                available=False,
                error="LLM_ENABLED is false; deterministic tool responses remain available.",
            )
            self._health = health
            return health

        now = time.time()
        with self._lock:
            if not force and self._health is not None and (now - self._health_at) < HEALTH_CACHE_SECONDS:
                return self._health

        try:
            models = self.list_models()
        except LLMUnavailable as exc:
            health = LLMHealth(
                enabled=True,
                provider=settings.LLM_PROVIDER,
                model=self.model,
                base_url=self.base_url,
                available=False,
                error=str(exc),
            )
        else:
            available = self.model in models
            health = LLMHealth(
                enabled=True,
                provider=settings.LLM_PROVIDER,
                model=self.model,
                base_url=self.base_url,
                available=available,
                models=models,
                error=None if available else (
                    f"Model '{self.model}' is not installed; available models: {', '.join(models) or 'none'}"
                ),
            )

        with self._lock:
            self._health = health
            self._health_at = now
        return health

    # -------------------------------------------------------------------- chat
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        timeout: Optional[float] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a chat request and return the assistant message object."""
        health = self.health()
        if not health.available:
            raise LLMUnavailable(health.error or "Configured model is not available")

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "keep_alive": "10m",
            "options": {"temperature": 0.1, **(options or {})},
        }
        if tools:
            body["tools"] = tools

        url = f"{self.base_url}/api/chat"
        try:
            response = httpx.post(url, json=body, timeout=timeout or self.timeout)
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise LLMTimeout(
                f"Model '{self.model}' timed out after {timeout or self.timeout:g}s"
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"Model request failed: {exc}") from exc
        except ValueError as exc:
            raise LLMError(f"Model returned a non-JSON response: {exc}") from exc

        message = payload.get("message")
        if not isinstance(message, dict):
            raise LLMError("Model response did not include a message object")
        return message


_client: Optional[OllamaClient | GroqClient] = None
_client_lock = threading.Lock()


def get_llm_client() -> OllamaClient | GroqClient:
    global _client
    with _client_lock:
        if _client is None:
            if settings.LLM_PROVIDER == "groq":
                _client = GroqClient()
            elif settings.LLM_PROVIDER == "ollama":
                _client = OllamaClient()
            else:
                _client = OllamaClient()
        return _client


def reset_llm_client() -> None:
    """Drop the cached client (used by tests)."""
    global _client
    with _client_lock:
        _client = None
