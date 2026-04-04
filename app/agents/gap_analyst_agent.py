"""
Agent 3: GapAnalystAgent
Responsibility: Identify skill gaps in the recommended team and
suggest actionable paths to fill them (training, subcontracting, etc.)
"""

import json, re
from langchain.schema import HumanMessage, SystemMessage

from app.agents.llm_provider import get_llm
from app.services.graphrag_service import GraphRAGService
from app.core.logging import logger

SYSTEM_PROMPT = """You are a senior IT talent strategist for a Moroccan nearshore firm.
Given a list of UNCOVERED skills (skills required but not present in the proposed team),
provide actionable suggestions for each gap.

Respond ONLY with valid JSON — a list of gap objects:
[
  {
    "skill": "SAP S/4HANA",
    "suggestion": "Subcontract through CGI Morocco who has 3 certified SAP consultants available."
  }
]

Be specific and practical for the Moroccan market (mention specific training providers like
UM6P, ENSIAS, OCP Academy, Simplon.co Morocco, or specific ESN firms).
"""


class GapAnalystAgent:
    """Identifies uncovered skills via graph query, then generates suggestions via LLM."""

    def __init__(self):
        self.llm = get_llm()
        self.graph = GraphRAGService()
        self.name = "GapAnalystAgent"

    def run(self, requirements: dict, team_engineers: list[dict]) -> dict:
        required_skills = requirements.get("skills", [])
        engineer_ids = [e["id"] for e in team_engineers]

        logger.info(
            "[%s] Checking %d required skills against team of %d.",
            self.name, len(required_skills), len(engineer_ids),
        )

        # GraphRAG: find which skills are NOT covered by the team
        uncovered = self.graph.identify_skill_gaps(required_skills, engineer_ids)

        if not uncovered:
            logger.info("[%s] No skill gaps detected.", self.name)
            return {
                "status": "no_gaps",
                "gaps": [],
                "agent": self.name,
            }

        logger.info("[%s] Uncovered skills: %s", self.name, uncovered)

        # LLM: generate actionable suggestions for each gap
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Generate gap suggestions for these uncovered skills:\n{json.dumps(uncovered)}"
            ),
        ]

        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            gaps = json.loads(raw)
        except Exception as e:
            logger.warning("[%s] LLM suggestion failed: %s. Using defaults.", self.name, e)
            gaps = [
                {
                    "skill": skill,
                    "suggestion": "Consider training via Simplon.co Morocco or sourcing from partner ESN firms in Casablanca.",
                }
                for skill in uncovered
            ]

        return {"status": "success", "gaps": gaps, "uncovered_skills": uncovered, "agent": self.name}
