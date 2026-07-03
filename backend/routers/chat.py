"""Conversational endpoints fronting the three ADK agents (PLAN.md section 4).
One route per agent rather than a single generic /chat, since each agent has a
distinct audience (admin vs. citizen) and the frontend should never be able to
address the allocation agent from the farmer-facing UI or vice versa.
"""
import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.agent_runner import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    session_id: str | None = Field(default=None, description="Omit to start a new conversation.")


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls: list[dict]


async def _handle(agent_name: str, req: ChatRequest) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    result = await run_agent(agent_name, req.user_id, session_id, req.message)
    return ChatResponse(reply=result["reply"], session_id=session_id, tool_calls=result["tool_calls"])


@router.post("/triage", response_model=ChatResponse)
async def chat_triage(req: ChatRequest):
    """Admin-facing: district risk ranking and explanation."""
    return await _handle("triage", req)


@router.post("/allocation", response_model=ChatResponse)
async def chat_allocation(req: ChatRequest):
    """Admin-facing: constraint-aware resource allocation across districts."""
    return await _handle("allocation", req)


@router.post("/farmer_advisory", response_model=ChatResponse)
async def chat_farmer_advisory(req: ChatRequest):
    """Citizen-facing: sowing timing and crop-switch advice."""
    return await _handle("farmer_advisory", req)
