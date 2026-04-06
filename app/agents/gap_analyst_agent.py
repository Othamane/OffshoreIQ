"""
Agent 3: GapAnalystAgent — Real LLM Agent with Bound Tools

The LLM autonomously calls the identify_skill_gaps tool, inspects results,
and then decides whether to call it again with adjusted parameters or proceed
to generating suggestions. This demonstrates conditional tool use.
"""

import json
import re
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from app.agents.llm_provider import get_llm
from app.services.graphrag_service import GraphRAGService
from app.core.logging import logger

_graph = GraphRAGService()


@tool
def identify_skill_gaps(required_skills: list[str], engineer_ids: list[str]) -> str:
    """
    Given a list of required skills and the IDs of proposed team engineers,
    find which required skills are not covered by any engineer in the team.
    Uses a Neo4j set-difference query across the graph.
    Input: required_skills (list of skill names), engineer_ids (list of engineer IDs)
    Returns: list of uncovered skill names
    """
    uncovered = _graph.identify_skill_gaps(required_skills, engineer_ids)
    return json.dumps({"uncovered_skills": uncovered, "gap_count": len(uncovered)})


@tool
def get_team_skill_coverage(engineer_ids: list[str]) -> str:
    """
    Get the full combined skill set of a proposed team.
    Useful to understand what the team covers before identifying gaps.
    Input: list of engineer IDs
    """
    if not engineer_ids:
        return json.dumps({"team_skills": []})
    query = """
    UNWIND $eids AS eid
    MATCH (eng:Engineer {id: eid})-[r:HAS_SKILL]->(s:Skill)
    RETURN DISTINCT s.name AS skill, r.proficiency AS proficiency
    ORDER BY s.name
    """
    from app.db.neo4j_db import db
    results = db.run_query(query, {"eids": engineer_ids})
    return json.dumps({"team_skills": results})


GAP_TOOLS = [identify_skill_gaps, get_team_skill_coverage]

SYSTEM_PROMPT = """You are a talent gap analyst for a Moroccan nearshore IT firm.
Your goal: identify skill gaps in a proposed team and provide actionable Morocco-specific suggestions.

Available tools:
- get_team_skill_coverage: see what skills the proposed team already covers
- identify_skill_gaps: find which required skills are missing from the team

STRATEGY:
1. Call get_team_skill_coverage to understand what the team has
2. Call identify_skill_gaps with the required skills and engineer IDs
3. Analyze the gaps and generate suggestions

Your FINAL response must be valid JSON only:
{
  "gaps": [
    {
      "skill": "Power BI",
      "suggestion": "Specific Morocco-based suggestion: training provider, ESN firm, or subcontracting option"
    }
  ],
  "coverage_summary": "Brief summary of what the team covers well"
}

For suggestions, be specific to the Moroccan market:
- Training: Simplon.co Maroc, UM6P (Mohammed VI Polytechnic), ENSIAS, ENSA schools, OCP Academy
- ESN firms: CGI Morocco, Capgemini Maroc, SQLI Maroc, Devoteam Maroc, Intelcia
- Remote talent: mention specific Moroccan tech communities (Dev'ils, GDG Casablanca, Morocco JUG)
If there are no gaps, return: {"gaps": [], "coverage_summary": "Full coverage achieved."}"""


class GapAnalystAgent:
    """Real LLM agent that autonomously uses graph tools to detect and explain skill gaps."""

    def __init__(self):
        self.llm = get_llm().bind_tools(GAP_TOOLS)
        self.tools_by_name = {t.name: t for t in GAP_TOOLS}
        self.name = "GapAnalystAgent"
        self.max_iterations = 5

    def run(self, requirements: dict, team_engineers: list[dict]) -> dict:
        required_skills = requirements.get("skills", [])
        engineer_ids    = [e["id"] for e in team_engineers]

        logger.info(
            "[%s] Analyzing gaps: %d required skills, team of %d.",
            self.name, len(required_skills), len(engineer_ids),
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=(
                f"Analyze skill gaps for this team.\n"
                f"Required skills: {json.dumps(required_skills)}\n"
                f"Team engineer IDs: {json.dumps(engineer_ids)}\n"
                f"Find what's missing and provide actionable suggestions."
            )),
        ]

        for iteration in range(self.max_iterations):
            response = self.llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id   = tool_call["id"]
                logger.info("[%s] LLM calling tool: %s", self.name, tool_name)

                if tool_name in self.tools_by_name:
                    try:
                        result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                messages.append(ToolMessage(content=result, tool_call_id=tool_id))

        # Parse final output
        final_text = response.content if hasattr(response, "content") else ""
        gaps, summary = self._parse_output(final_text, required_skills, engineer_ids)

        logger.info("[%s] Found %d gaps.", self.name, len(gaps))
        return {
            "status": "no_gaps" if not gaps else "success",
            "gaps": gaps,
            "coverage_summary": summary,
            "agent": self.name,
        }

    def _parse_output(self, text: str, required_skills: list, engineer_ids: list) -> tuple[list, str]:
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", text.strip())
            clean = re.sub(r"\s*```$", "", clean)
            parsed = json.loads(clean)
            return parsed.get("gaps", []), parsed.get("coverage_summary", "")
        except Exception:
            # Fallback: run gap query directly
            uncovered = _graph.identify_skill_gaps(required_skills, engineer_ids)
            gaps = [
                {
                    "skill": skill,
                    "suggestion": "Consider training via Simplon.co Maroc or sourcing from partner ESN firms in Casablanca.",
                }
                for skill in uncovered
            ]
            return gaps, ""
