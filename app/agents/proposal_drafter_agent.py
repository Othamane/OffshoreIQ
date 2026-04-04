"""
Agent 4: ProposalDrafterAgent
Responsibility: Generate a professional client-facing proposal
using the full context assembled by prior agents.
"""

from langchain.schema import HumanMessage, SystemMessage

from app.agents.llm_provider import get_llm
from app.core.logging import logger

SYSTEM_PROMPT = """You are a senior business development manager at a top Moroccan IT nearshore firm.
Write a professional, client-facing proposal email/document in English.

The proposal must:
1. Open with a confident positioning statement about the firm's nearshore capabilities.
2. Present the recommended team (name, expertise, key achievements from past projects).
3. Explain how the team covers the compliance/regulatory requirements.
4. Address any identified skill gaps and how they'll be mitigated.
5. Close with a call to action for a discovery call.

Tone: professional, concise, confidence-inspiring. Max 400 words.
Do NOT use placeholder brackets like [Client Name] — use "the client" instead.
"""


class ProposalDrafterAgent:
    """Generates a polished client-facing proposal from aggregated agent context."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "ProposalDrafterAgent"

    def run(
        self,
        requirements: dict,
        team_engineers: list[dict],
        gaps: list[dict],
    ) -> dict:
        logger.info(
            "[%s] Drafting proposal for team of %d engineers.", self.name, len(team_engineers)
        )

        # Build a concise context block for the LLM
        team_summary = "\n".join(
            [
                f"- {e['name']} ({e.get('city', 'Morocco')}, {e.get('years_exp', '?')}y exp): "
                f"Skills: {', '.join(e.get('matching_skills', [])[:4])}. "
                f"Past clients: {', '.join(e.get('clients', [])[:2])}. "
                f"Compliance: {', '.join(e.get('compliance_experience', [])[:2])}."
                for e in team_engineers[:4]
            ]
        )

        gap_summary = (
            "No skill gaps identified — full coverage achieved."
            if not gaps
            else "Identified gaps: " + ", ".join(g["skill"] for g in gaps) +
                 ". Mitigation: " + "; ".join(g.get("suggestion", "")[:80] for g in gaps[:2]) + "."
        )

        context = f"""
CLIENT REQUIREMENTS SUMMARY:
{requirements.get('summary', 'Not available.')}

Sector: {requirements.get('sector', 'N/A')}
Required Compliance: {', '.join(requirements.get('compliance_frameworks', []))}
Required Languages: {', '.join(requirements.get('languages', []))}

PROPOSED TEAM:
{team_summary}

SKILL GAP ANALYSIS:
{gap_summary}
"""

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Write the proposal based on this context:\n{context}"),
        ]

        response = self.llm.invoke(messages)
        proposal_text = response.content.strip()

        logger.info("[%s] Proposal generated (%d chars).", self.name, len(proposal_text))

        return {"status": "success", "proposal": proposal_text, "agent": self.name}
