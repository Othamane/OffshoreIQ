"""
Agent 2: TeamBuilderAgent
Responsibility: Traverse Neo4j graph (GraphRAG) to find best-fit engineers.
This agent does the heavy graph lifting — multi-hop Cypher queries.
"""

from app.agents.llm_provider import get_llm
from app.services.graphrag_service import GraphRAGService
from app.core.logging import logger
from langchain.schema import HumanMessage, SystemMessage
import json, re

SCORING_PROMPT = """You are a technical staffing expert. Given these candidate engineers and RFP requirements, 
score each engineer from 0.0 to 1.0 based on fit.

Consider: skill match count, years of experience, compliance experience, sector experience, language fit.

Respond with ONLY valid JSON — a list of objects with engineer id and score:
[{"id": "eng001", "score": 0.92}, ...]

Requirements:
{requirements}

Candidates:
{candidates}"""


class TeamBuilderAgent:
    """Uses GraphRAG multi-hop traversal to find and score engineer matches."""

    def __init__(self):
        self.llm = get_llm()
        self.graph = GraphRAGService()
        self.name = "TeamBuilderAgent"

    def run(self, requirements: dict) -> dict:
        logger.info("[%s] Starting team search.", self.name)

        skills = requirements.get("skills", [])
        compliance = requirements.get("compliance_frameworks", [])
        sector = requirements.get("sector", "")
        certs = requirements.get("certifications", [])

        # ── Multi-hop GraphRAG queries ──────────────────────────────────────────
        skill_matches = {}
        if skills:
            for eng in self.graph.find_engineers_by_skills(skills):
                eid = eng["id"]
                if eid not in skill_matches:
                    skill_matches[eid] = eng
                    skill_matches[eid]["graph_signals"] = []
                skill_matches[eid]["graph_signals"].append(
                    f"Skill match: {eng['matchedSkills']}"
                )

        compliance_matches = {}
        if compliance:
            for eng in self.graph.find_engineers_by_compliance(compliance):
                eid = eng["id"]
                compliance_matches[eid] = eng

        sector_matches = {}
        if sector:
            for eng in self.graph.find_engineers_by_sector_experience(sector):
                eid = eng["id"]
                sector_matches[eid] = eng

        cert_matches = {}
        if certs:
            for eng in self.graph.find_engineers_by_certifications(certs):
                eid = eng["id"]
                cert_matches[eid] = eng

        # ── Merge all candidate IDs ─────────────────────────────────────────────
        all_candidate_ids = set(skill_matches) | set(compliance_matches) | set(sector_matches) | set(cert_matches)

        if not all_candidate_ids:
            logger.warning("[%s] No candidates found.", self.name)
            return {"status": "no_candidates", "engineers": [], "agent": self.name}

        # ── Fetch full profiles for top candidates ──────────────────────────────
        profiles = []
        for eid in list(all_candidate_ids)[:10]:  # cap at 10 for LLM context
            profile = self.graph.get_engineer_full_profile(eid)
            if profile:
                profile["skill_match_count"] = len(
                    skill_matches.get(eid, {}).get("matchedSkills", [])
                )
                profile["has_compliance_exp"] = eid in compliance_matches
                profile["has_sector_exp"] = eid in sector_matches
                profile["has_cert"] = eid in cert_matches
                profiles.append(profile)

        # ── LLM scoring ──────────────────────────────────────────────────────────
        scored = self._score_candidates(requirements, profiles)

        # Attach score to profiles
        score_map = {s["id"]: s["score"] for s in scored}
        for p in profiles:
            p["match_score"] = score_map.get(p["id"], 0.0)
            p["matching_skills"] = skill_matches.get(p["id"], {}).get("matchedSkills", [])

        profiles.sort(key=lambda x: x["match_score"], reverse=True)
        top_team = profiles[:5]  # recommend top 5

        logger.info(
            "[%s] Recommended %d engineers. Top score: %.2f",
            self.name,
            len(top_team),
            top_team[0]["match_score"] if top_team else 0.0,
        )

        return {"status": "success", "engineers": top_team, "agent": self.name}

    def _score_candidates(self, requirements: dict, profiles: list[dict]) -> list[dict]:
        """Ask the LLM to score candidates based on profile + requirements."""
        simplified = [
            {
                "id": p["id"],
                "name": p["name"],
                "years_exp": p["years_exp"],
                "skills": [s["skill"] for s in p.get("skills", []) if s["skill"]],
                "certifications": p.get("certifications", []),
                "compliance_experience": p.get("compliance_experience", []),
                "clients": p.get("clients", []),
                "skill_match_count": p.get("skill_match_count", 0),
            }
            for p in profiles
        ]

        prompt_text = (
    SCORING_PROMPT
    .replace("{requirements}", json.dumps(requirements, indent=2))
    .replace("{candidates}", json.dumps(simplified, indent=2))
        )
        messages = [
    SystemMessage(content=prompt_text),
    HumanMessage(content="Score these candidates now."),
    ]

        try:
            response = self.llm.invoke(messages)
            raw = response.content.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except Exception as e:
            logger.warning("[%s] LLM scoring failed: %s. Using rule-based fallback.", self.name, e)
            # Rule-based fallback scoring
            return [
                {
                    "id": p["id"],
                    "score": min(
                        0.4 + (p.get("skill_match_count", 0) * 0.1)
                        + (0.1 if p.get("has_compliance_exp") else 0)
                        + (0.1 if p.get("has_sector_exp") else 0),
                        1.0,
                    ),
                }
                for p in profiles
            ]
