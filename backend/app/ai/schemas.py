"""Structured schemas for the DHRUVION mission assistant."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolCallRecord(BaseModel):
    tool: str
    status: str
    arguments: Dict[str, Any] = {}
    duration_ms: Optional[float] = None
    error: Optional[str] = None


class Observation(BaseModel):
    tool: str
    label: str
    value: Any = None
    unit: Optional[str] = None
    provenance: Optional[str] = None
    source: Optional[str] = None
    coverage: Optional[str] = None


class Confidence(BaseModel):
    level: str = "low"
    basis: str = ""
    limitations: List[str] = []


class AssistantRequest(BaseModel):
    message: str
    mission_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


class AssistantResponse(BaseModel):
    # Existing contract fields (kept for the current frontend).
    message: str
    intent: str
    recommendation: Optional[Dict[str, Any]] = None
    tool_activity: List[ToolCallRecord] = []
    evidence: List[Any] = []
    warnings: List[str] = []
    sources: List[Any] = []
    actions: List[str] = []

    # Additive structured fields.
    answer: str = ""
    tools_used: List[str] = []
    observations: List[Observation] = []
    units: Dict[str, str] = {}
    limitations: List[str] = []
    confidence: Confidence = Confidence()
    fallback: bool = False
    model: Optional[str] = None
    mission_id: Optional[str] = None
    grounding: Dict[str, Any] = {}


class AssistantHealthResponse(BaseModel):
    status: str
    llm_enabled: bool
    provider: str
    model: str
    available: bool
    base_url: Optional[str] = None
    error: Optional[str] = None
    tools: List[str] = []
    fallback_available: bool = True
