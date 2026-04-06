"""
Agent 2: TeamBuilderAgent — Real LLM Agent with Bound Tools

This is a genuine LLM agent: the LLM receives a system prompt describing
available tools, decides which to call and in what order, receives tool
results back, and reasons toward a final answer. This is the ReAct pattern.

Tools available to the LLM:
  - semantic_project_search     : True GraphRAG step 1 — vector similarity
  - graph_traverse_from_projects: True GraphRAG step 2 — graph enrichment
  - find_engineers_by_skills    : exact skill match via Cypher
  - find_engineers_by_compliance: compliance experience via 3-hop traversal
  - find_engineers_by_sector    : sector experience via 4-hop traversal
  - get_engineer_profile        : full profile for a specific engineer
"""

import json
import re
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from app.agents.llm_provider import get_llm
from app.services.graphrag_service import GraphRAGService
from app.services.embedding_service import (
    semantic_search_projects,
    graphrag_find_engineers_from_projects,
)
from app.core.logging import logger

_graph = GraphRAGService()

# ── Tool Definitions ───────────────────────────────────────────────────────────
# These are real LangChain tools bound to the LLM.
# The LLM sees their names, descriptions, and argument schemas.
# It decides autonomously which to call based on the RFP requirements.

@tool
def semantic_project_search(query: str) -> str:
    """
    GraphRAG Step 1: Semantic vector search over project descriptions.
    Use this FIRST to find projects semantically similar to the RFP.
    Returns project IDs and similarity scores.
    Input: a natural language description of what the client needs.
    """
    results = semantic_search_projects(query, top_k=5)
    if not results:
        return json.dumps({"projects": [], "note": "No semantic matches found or vector index not ready."})
    return json.dumps({"projects": results})


@tool
def graph_traverse_from_projects(project_ids: list[str]) -> str:
    """
    GraphRAG Step 2: Graph traversal starting from semantically matched projects.
    Use this AFTER semantic_project_search to find engineers connected to those projects.
    Input: list of project IDs from semantic_project_search.
    Returns engineers with their skills, compliance experience, and sector history.
    """
    engineers = graphrag_find_engineers_from_projects(project_ids)
    return json.dumps({"engineers": engineers[:8]})


@tool
def find_engineers_by_skills(skills: list[str]) -> str:
    """
    Find engineers who have specific technical skills at intermediate proficiency or above.
    Use this to find engineers matching explicit skill requirements from the RFP.
    Input: list of skill names e.g. ["SAP S/4HANA", "Java", "GDPR Compliance"]
    """
    results = _graph.find_engineers_by_skills(skills)
    return json.dumps({"engineers": results[:8]})


@tool
def find_engineers_by_compliance(frameworks: list[str]) -> str:
    """
    Find engineers with hands-on experience in specific compliance frameworks,
    verified through actual project records (not self-declared).
    3-hop graph query: Engineer → WORKED_ON → Project → REQUIRED_COMPLIANCE → Framework.
    Input: list of frameworks e.g. ["GDPR", "ISO 27001", "PCI-DSS"]
    """
    results = _graph.find_engineers_by_compliance(frameworks)
    return json.dumps({"engineers": results[:8]})


@tool
def find_engineers_by_sector(sector: str) -> str:
    """
    Find engineers who have delivered projects for clients in a specific industry sector.
    4-hop graph query: Engineer → WORKED_ON → Project → FOR_CLIENT → Client → IN_SECTOR → Sector.
    Input: one of [Banking & Finance, Insurance, Retail, Telecom, Healthcare, Energy, Public Sector]
    """
    results = _graph.find_engineers_by_sector_experience(sector)
    return json.dumps({"engineers": results[:8]})


@tool
def get_engineer_profile(engineer_id: str) -> str:
    """
    Get the complete profile of a specific engineer including all skills,
    certifications, project history, clients, and compliance experience.
    Use this to get full detail before making a final recommendation.
    Input: engineer ID string e.g. "eng001"
    """
    profile = _graph.get_engineer_full_profile(engineer_id)
    return json.dumps({"profile": profile})


TOOLS = [
    semantic_project_search,
    graph_traverse_from_projects,
    find_engineers_by_skills,
    find_engineers_by_compliance,
    find_engineers_by_sector,
    get_engineer_profile,
]

SYSTEM_PROMPT = """You are an expert IT staffing agent for a Moroccan nearshore firm.
Your goal: find the best team of engineers that matches the client's RFP requirements.

You have access to these tools:
- semantic_project_search: GraphRAG step 1 — find similar past projects by semantic similarity
- graph_traverse_from_projects: GraphRAG step 2 — find engineers from those projects
- find_engineers_by_skills: find engineers by exact skill match
- find_engineers_by_compliance: find engineers with verified compliance experience
- find_engineers_by_sector: find engineers with sector-specific project history
- get_engineer_profile: get full detail on a specific engineer

STRATEGY — always follow this order:
1. Call semantic_project_search with the RFP description to find similar past projects (GraphRAG entry)
2. Call graph_traverse_from_projects with those project IDs to find candidate engineers
3. Supplement with find_engineers_by_skills, find_engineers_by_compliance, find_engineers_by_sector
4. Call get_engineer_profile for the top 3-5 most promising candidates
5. Return your final ranked team recommendation as JSON

Your FINAL response (after all tool calls) must be valid JSON only:
{
  "recommended_engineers": [
    {
      "id": "eng001",
      "name": "Name",
      "match_score": 0.92,
      "matching_skills": ["SAP S/4HANA", "Java"],
      "reasoning": "Why this engineer fits"
    }
  ],
  "tool_calls_made": ["semantic_project_search", "graph_traverse_from_projects", ...]
}"""


class TeamBuilderAgent:
    """
    Real LLM Agent: binds graph tools to the LLM via LangChain tool binding.
    The LLM autonomously decides which tools to call and in what order (ReAct pattern).
    """

    def __init__(self):
        self.llm = get_llm().bind_tools(TOOLS)
        self.tools_by_name = {t.name: t for t in TOOLS}
        self.name = "TeamBuilderAgent"
        self.max_iterations = 8  # prevent infinite loops

    def run(self, requirements: dict) -> dict:
        logger.info("[%s] Starting agentic team search.", self.name)

        rfp_summary = (
            f"Sector: {requirements.get('sector', 'N/A')}. "
            f"Skills needed: {', '.join(requirements.get('skills', []))}. "
            f"Compliance: {', '.join(requirements.get('compliance_frameworks', []))}. "
            f"Languages: {', '.join(requirements.get('languages', []))}. "
            f"Certifications: {', '.join(requirements.get('certifications', []))}."
        )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Find the best team for this RFP:\n{rfp_summary}"),
        ]

        tool_calls_log = []

        # ── Agentic loop: LLM calls tools until it produces a final answer ────
        for iteration in range(self.max_iterations):
            response = self.llm.invoke(messages)
            messages.append(response)

            # No tool calls → LLM has produced its final answer
            if not response.tool_calls:
                logger.info("[%s] Agent finished after %d iterations.", self.name, iteration + 1)
                break

            # Execute each tool the LLM decided to call
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id   = tool_call["id"]

                logger.info("[%s] LLM calling tool: %s(%s)", self.name, tool_name, tool_args)
                tool_calls_log.append(tool_name)

                if tool_name in self.tools_by_name:
                    try:
                        result = self.tools_by_name[tool_name].invoke(tool_args)
                    except Exception as e:
                        result = json.dumps({"error": str(e)})
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                # Feed tool result back to LLM as a ToolMessage
                messages.append(ToolMessage(content=result, tool_call_id=tool_id))
        else:
            logger.warning("[%s] Max iterations reached.", self.name)

        # ── Parse final LLM output ──────────────────────────────────────────────
        final_text = response.content if hasattr(response, "content") else ""
        engineers, scores = self._parse_final_output(final_text, requirements)

        logger.info(
            "[%s] Recommended %d engineers. Tools used: %s",
            self.name, len(engineers), tool_calls_log
        )

        return {
            "status": "success",
            "engineers": engineers,
            "agent": self.name,
            "tools_used": tool_calls_log,
        }

    def _parse_final_output(self, text: str, requirements: dict) -> tuple[list, list]:
        """Parse the LLM's final JSON output into engineer profiles."""
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", text.strip())
            clean = re.sub(r"\s*```$", "", clean)
            parsed = json.loads(clean)
            raw_engineers = parsed.get("recommended_engineers", [])

            # Enrich with full profiles from graph
            enriched = []
            for e in raw_engineers[:5]:
                profile = _graph.get_engineer_full_profile(e.get("id", ""))
                if profile:
                    profile["match_score"]    = e.get("match_score", 0.5)
                    profile["matching_skills"] = e.get("matching_skills", [])
                    profile["reasoning"]      = e.get("reasoning", "")
                    enriched.append(profile)
            return enriched, []

        except Exception as ex:
            logger.warning("[%s] Could not parse final output: %s. Falling back.", self.name, ex)
            return self._fallback_search(requirements), []

    def _fallback_search(self, requirements: dict) -> list[dict]:
        """Rule-based fallback if LLM output can't be parsed."""
        skills = requirements.get("skills", [])
        if not skills:
            return []
        candidates = _graph.find_engineers_by_skills(skills)
        results = []
        for c in candidates[:5]:
            profile = _graph.get_engineer_full_profile(c["id"])
            if profile:
                profile["match_score"]     = min(0.4 + c.get("matchCount", 0) * 0.1, 0.85)
                profile["matching_skills"] = c.get("matchedSkills", [])
                results.append(profile)
        return results
