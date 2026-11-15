"""Shared LLM exception and health types for the DHRUVION mission assistant."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class LLMError(Exception):
    """Base error for model communication failures."""


class LLMUnavailable(LLMError):
    """The configured model provider cannot be reached or has no model."""


class LLMTimeout(LLMError):
    """The model did not answer within the configured timeout."""


@dataclass
class LLMHealth:
    enabled: bool
    provider: str
    model: str
    base_url: Optional[str]
    available: bool
    checked_at: float = field(default_factory=time.time)
    error: Optional[str] = None
    models: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "available": self.available,
            "checked_at": self.checked_at,
            "error": self.error,
            "models": list(self.models),
        }
