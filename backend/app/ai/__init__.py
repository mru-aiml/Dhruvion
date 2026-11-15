"""Mission-aware AI assistant package."""

from app.ai.agent import MissionAssistant, get_assistant
from app.ai.llm_client import OllamaClient, get_llm_client
from app.ai.schemas import (
    AssistantHealthResponse,
    AssistantRequest,
    AssistantResponse,
    Confidence,
    Observation,
    ToolCallRecord,
)
from app.ai.tools import TOOL_NAMES, TOOL_SPECS, ToolOutcome, ollama_tools, run_tool

__all__ = [
    "MissionAssistant",
    "get_assistant",
    "OllamaClient",
    "get_llm_client",
    "AssistantHealthResponse",
    "AssistantRequest",
    "AssistantResponse",
    "Confidence",
    "Observation",
    "ToolCallRecord",
    "TOOL_NAMES",
    "TOOL_SPECS",
    "ToolOutcome",
    "ollama_tools",
    "run_tool",
]
