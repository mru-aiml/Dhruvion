"""Mission assistant endpoints.

The assistant uses allowlisted tools backed by the same services as the rest of
the API. When the model is unavailable the endpoint still returns deterministic,
evidence-based results instead of failing the whole request.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.ai.agent import get_assistant
from app.ai.schemas import AssistantHealthResponse, AssistantRequest, AssistantResponse

router = APIRouter(tags=["assistant"])


@router.post("/assistant/ask", response_model=AssistantResponse)
def assistant_ask(payload: AssistantRequest):
    return get_assistant().ask(payload)


@router.get("/assistant/health", response_model=AssistantHealthResponse)
def assistant_health():
    return get_assistant().health()
