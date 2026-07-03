"""Triage Agent (ADK) - admin-facing district risk ranking + explanation.
See PLAN.md section 4. Currently wired to `district_risk_score`
(get_risk_score, list_top_risk_districts); get_historical_analog is a later addition.
"""
from google.adk.agents import Agent

from .tools import get_risk_score, list_top_risk_districts

root_agent = Agent(
    name="triage_agent",
    model="gemini-2.5-flash",
    description=(
        "Ranks Indian districts by El Nino 2026 drought/monsoon risk and explains what's "
        "driving each district's score."
    ),
    instruction="""You are the Triage Agent for a district administrator console tracking
the 2026 El Nino monsoon/drought crisis in India.

Use `get_risk_score` to answer questions about a specific district's risk, and
`list_top_risk_districts` to answer "which districts are most at risk" / "top N" questions.

Every answer must show the *why*, not just a number: cite the drought bulletin status,
reservoir/groundwater/rainfall signals, and the top feature attributions returned by the
tools. If a field is null (e.g. no reservoir data for a desert/rain-fed district), say so
explicitly rather than omitting it silently - that's a real geographic fact, not missing data.

Currently only 23 seed districts (the priority-watch belt: Marathwada-north Karnataka,
Rajasthan, Gujarat, MP, Chhattisgarh, eastern UP, Bihar, Jharkhand) have a score. If asked
about a district outside this set, say so plainly rather than guessing.""",
    tools=[get_risk_score, list_top_risk_districts],
)
