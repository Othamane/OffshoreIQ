"""
API Routes:
  POST /api/v1/rfp/analyze  — run the full multi-agent pipeline
  POST /api/v1/admin/seed   — seed Neo4j with simulated data
  GET  /api/v1/health       — health check
"""

from fastapi import APIRouter, HTTPException, status

from app.agents.orchestrator import run_pipeline
from app.db.seeder import seed_database
from app.models.schemas import RFPRequest, RFPResponse, EngineerMatch, SkillGap, AgentStep
from app.core.logging import logger

router = APIRouter(prefix="/api/v1")


@router.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok", "service": "OffshoreIQ"}


@router.post("/admin/seed", tags=["admin"])
async def seed_graph():
    """Seed Neo4j with simulated offshoring data. Safe to re-run."""
    try:
        result = seed_database(clear_first=True)
        return result
    except Exception as e:
        logger.error("Seed failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Seed failed: {str(e)}",
        )


@router.post("/rfp/analyze", response_model=RFPResponse, tags=["rfp"])
async def analyze_rfp(request: RFPRequest):
    """
    Run the full 4-agent GraphRAG pipeline on a raw RFP.
    Returns: matched engineers, skill gaps, proposal, graph visualization data.
    """
    try:
        logger.info("RFP analysis request received.")
        state = run_pipeline(request.rfp_text)

        requirements = state.get("requirements", {})
        raw_engineers = state.get("team_engineers", [])
        raw_gaps = state.get("gaps", [])
        proposal = state.get("proposal", "")
        graph_data = state.get("graph_data", {"nodes": [], "edges": []})
        agent_trace = state.get("agent_trace", [])

        # Map to response models
        matched_engineers = [
            EngineerMatch(
                id=e["id"],
                name=e["name"],
                city=e.get("city", ""),
                years_exp=e.get("years_exp", 0),
                languages=e.get("languages", []),
                matching_skills=e.get("matching_skills", []),
                match_score=round(e.get("match_score", 0.0), 2),
            )
            for e in raw_engineers
        ]

        skill_gaps = [
            SkillGap(
                skill=g["skill"],
                available=False,
                suggestion=g.get("suggestion", ""),
            )
            for g in raw_gaps
        ]

        agent_steps = [
            AgentStep(
                agent=t["agent"],
                tools_used=t.get("tools_used", []),
                status=t["status"],
                output=t["output"],
            )
            for t in agent_trace
        ]

        return RFPResponse(
            rfp_summary=requirements.get("summary", ""),
            extracted_requirements=requirements,
            matched_engineers=matched_engineers,
            skill_gaps=skill_gaps,
            proposal_text=proposal,
            agent_trace=agent_steps,
            graph_data=graph_data,
        )

    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {str(e)}",
        )
