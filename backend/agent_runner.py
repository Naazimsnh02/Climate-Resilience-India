"""Shared ADK runner wrapper for exposing the three agents over HTTP.

Each agent gets one InMemoryRunner (created lazily, reused across requests).
Sessions are keyed by (agent_name, session_id) so a farmer's chat history and
an administrator's chat history never bleed into each other. In-memory only -
history is lost on backend restart, which is fine for a hackathon demo but is
the first thing to swap for a persistent SessionService (e.g. VertexAiSessionService)
if this needs to survive redeploys.
"""
from google.adk.runners import InMemoryRunner
from google.genai import types

from agents.triage_agent.agent import root_agent as triage_agent
from agents.allocation_agent.agent import root_agent as allocation_agent
from agents.farmer_advisory_agent.agent import root_agent as farmer_advisory_agent

AGENTS = {
    "triage": triage_agent,
    "allocation": allocation_agent,
    "farmer_advisory": farmer_advisory_agent,
}

_runners: dict[str, InMemoryRunner] = {}
_known_sessions: set[tuple[str, str]] = set()


def _runner_for(agent_name: str) -> InMemoryRunner:
    if agent_name not in AGENTS:
        raise ValueError(f"Unknown agent '{agent_name}'. Valid: {list(AGENTS)}")
    if agent_name not in _runners:
        _runners[agent_name] = InMemoryRunner(agent=AGENTS[agent_name], app_name=agent_name)
    return _runners[agent_name]


async def run_agent(agent_name: str, user_id: str, session_id: str, message: str) -> dict:
    """Runs one turn of a conversation with the named agent and returns the final
    text reply plus the raw tool calls made along the way (for a debug/explainability
    view in the frontend - PLAN.md section 5 wants the "why" surfaced, and showing
    which BigQuery-backed tool ran is part of that).
    """
    runner = _runner_for(agent_name)
    session_key = (agent_name, session_id)
    if session_key not in _known_sessions:
        await runner.session_service.create_session(
            app_name=agent_name, user_id=user_id, session_id=session_id
        )
        _known_sessions.add(session_key)

    content = types.Content(role="user", parts=[types.Part(text=message)])

    final_text_parts: list[str] = []
    tool_calls: list[dict] = []

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        if not event.content or not event.content.parts:
            continue
        for part in event.content.parts:
            if part.function_call:
                tool_calls.append(
                    {"tool": part.function_call.name, "args": dict(part.function_call.args or {})}
                )
            if part.text:
                final_text_parts.append(part.text)

    return {
        "reply": "".join(final_text_parts).strip(),
        "tool_calls": tool_calls,
    }
