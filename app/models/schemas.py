"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field


class RFPRequest(BaseModel):
    rfp_text: str = Field(
        ...,
        min_length=20,
        description="Raw RFP text describing the client's requirements.",
    )


class EngineerMatch(BaseModel):
    id: str
    name: str
    city: str
    years_exp: int
    languages: list[str]
    matching_skills: list[str]
    match_score: float


class SkillGap(BaseModel):
    skill: str
    available: bool
    suggestion: str


class AgentStep(BaseModel):
    agent: str
    status: str
    output: str
    tools_used: list[str] = []  # which tools the LLM called in this step


class RFPResponse(BaseModel):
    rfp_summary: str
    extracted_requirements: dict
    matched_engineers: list[EngineerMatch]
    skill_gaps: list[SkillGap]
    proposal_text: str
    agent_trace: list[AgentStep]
    graph_data: dict
