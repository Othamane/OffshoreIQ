"""
Agent 1: RFPParserAgent
Responsibility: Parse raw RFP text and extract structured requirements.
Output: skills, certifications, compliance frameworks, sector, languages, summary.
"""

import json
import re
from langchain.schema import HumanMessage, SystemMessage

from app.agents.llm_provider import get_llm
from app.core.logging import logger

SYSTEM_PROMPT = """You are an expert IT staffing analyst specializing in Moroccan nearshore offshoring.
Your task is to analyze RFP (Request for Proposal) documents and extract structured requirements.

You MUST respond with ONLY valid JSON — no preamble, no explanation, no markdown code fences.

Extract:
- skills: list of technical skills required (be specific, e.g., "SAP S/4HANA" not just "SAP")
- certifications: list of required certifications (exact names)
- compliance_frameworks: list of regulatory/compliance requirements (e.g., GDPR, ISO 27001, PCI-DSS)
- sector: ONE of [Banking & Finance, Insurance, Retail, Telecom, Healthcare, Energy, Public Sector, Other]
- languages: required human languages (e.g., French, English, Arabic, Spanish)
- summary: a 2-sentence summary of what the client needs
- seniority: one of [junior, mid, senior, lead]

Example output:
{
  "skills": ["SAP S/4HANA", "Java", "Spring Boot"],
  "certifications": ["SAP S/4HANA Certified"],
  "compliance_frameworks": ["GDPR", "ISO 27001"],
  "sector": "Banking & Finance",
  "languages": ["French", "English"],
  "summary": "The client needs a SAP modernization team for a French bank. GDPR compliance and French fluency are mandatory.",
  "seniority": "senior"
}"""


class RFPParserAgent:
    """Parses raw RFP text into structured requirements using LLM."""

    def __init__(self):
        self.llm = get_llm()
        self.name = "RFPParserAgent"

    def run(self, rfp_text: str) -> dict:
        logger.info("[%s] Parsing RFP (%d chars).", self.name, len(rfp_text))

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Parse this RFP:\n\n{rfp_text}"),
        ]

        response = self.llm.invoke(messages)
        raw = response.content.strip()

        # Strip markdown code fences if LLM adds them
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            parsed = json.loads(raw)
            logger.info(
                "[%s] Extracted: %d skills, %d frameworks, sector=%s",
                self.name,
                len(parsed.get("skills", [])),
                len(parsed.get("compliance_frameworks", [])),
                parsed.get("sector", "unknown"),
            )
            return {"status": "success", "requirements": parsed, "agent": self.name}
        except json.JSONDecodeError as e:
            logger.error("[%s] JSON parse failed: %s | Raw: %s", self.name, e, raw[:200])
            # Fallback: return safe defaults so the pipeline doesn't crash
            return {
                "status": "fallback",
                "requirements": {
                    "skills": [],
                    "certifications": [],
                    "compliance_frameworks": [],
                    "sector": "Other",
                    "languages": ["French", "English"],
                    "summary": rfp_text[:200],
                    "seniority": "mid",
                },
                "agent": self.name,
            }
