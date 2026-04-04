"""
Multi-Agent Orchestrator using LangGraph StateGraph.
Defines the agent pipeline: Parse → Build Team → Analyze Gaps → Draft Proposal.

State flows sequentially through agents; each agent appends to the trace log.
"""

from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END

from app.agents.rfp_parser_agent import RFPParserAgent
from app.agents.team_builder_agent import TeamBuilderAgent
from app.agents.gap_analyst_agent import GapAnalystAgent
from app.agents.proposal_drafter_agent import ProposalDrafterAgent
from app.services.graphrag_service import GraphRAGService
from app.core.logging import logger


# ── State Definition ───────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    rfp_text: str
    requirements: dict
    team_engineers: list
    gaps: list
    proposal: str
    graph_data: dict
    agent_trace: Annotated[list, operator.add]  # append-only across agents


# ── Agent Node Functions ───────────────────────────────────────────────────────

def parse_rfp_node(state: PipelineState) -> dict:
    agent = RFPParserAgent()
    result = agent.run(state["rfp_text"])
    return {
        "requirements": result.get("requirements", {}),
        "agent_trace": [
            {
                "agent": result["agent"],
                "status": result["status"],
                "output": f"Extracted: {len(result.get('requirements', {}).get('skills', []))} skills, "
                          f"sector={result.get('requirements', {}).get('sector', 'N/A')}",
            }
        ],
    }


def build_team_node(state: PipelineState) -> dict:
    agent = TeamBuilderAgent()
    result = agent.run(state["requirements"])
    engineers = result.get("engineers", [])
    return {
        "team_engineers": engineers,
        "agent_trace": [
            {
                "agent": result["agent"],
                "status": result["status"],
                "output": f"Found {len(engineers)} candidate engineers via multi-hop GraphRAG traversal. "
                          + (f"Top candidate: {engineers[0]['name']} (score: {engineers[0].get('match_score', 0):.2f})" if engineers else "No candidates found."),
            }
        ],
    }


def analyze_gaps_node(state: PipelineState) -> dict:
    agent = GapAnalystAgent()
    result = agent.run(state["requirements"], state["team_engineers"])
    gaps = result.get("gaps", [])
    return {
        "gaps": gaps,
        "agent_trace": [
            {
                "agent": result["agent"],
                "status": result["status"],
                "output": f"Identified {len(gaps)} skill gap(s): "
                          + (", ".join(g["skill"] for g in gaps) if gaps else "None — full coverage!"),
            }
        ],
    }


def draft_proposal_node(state: PipelineState) -> dict:
    agent = ProposalDrafterAgent()
    result = agent.run(state["requirements"], state["team_engineers"], state["gaps"])
    return {
        "proposal": result.get("proposal", ""),
        "agent_trace": [
            {
                "agent": result["agent"],
                "status": result["status"],
                "output": f"Proposal generated ({len(result.get('proposal', ''))} characters).",
            }
        ],
    }


def build_graph_data_node(state: PipelineState) -> dict:
    """Final node: builds graph visualization payload from Neo4j."""
    graph_svc = GraphRAGService()
    engineer_ids = [e["id"] for e in state["team_engineers"]]
    graph_data = graph_svc.build_graph_visualization_data(engineer_ids)
    return {
        "graph_data": graph_data,
        "agent_trace": [
            {
                "agent": "GraphVisualizationAgent",
                "status": "success",
                "output": f"Built visualization: {len(graph_data.get('nodes', []))} nodes, "
                          f"{len(graph_data.get('edges', []))} edges.",
            }
        ],
    }


# ── Graph Builder ──────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("parse_rfp",       parse_rfp_node)
    graph.add_node("build_team",      build_team_node)
    graph.add_node("analyze_gaps",    analyze_gaps_node)
    graph.add_node("draft_proposal",  draft_proposal_node)
    graph.add_node("build_graph_data", build_graph_data_node)

    graph.set_entry_point("parse_rfp")
    graph.add_edge("parse_rfp",       "build_team")
    graph.add_edge("build_team",      "analyze_gaps")
    graph.add_edge("analyze_gaps",    "draft_proposal")
    graph.add_edge("draft_proposal",  "build_graph_data")
    graph.add_edge("build_graph_data", END)

    return graph.compile()


def run_pipeline(rfp_text: str) -> dict:
    """Entry point: run the full multi-agent pipeline for a given RFP."""
    logger.info("Starting OffshoreIQ pipeline...")

    pipeline = build_pipeline()

    initial_state: PipelineState = {
        "rfp_text": rfp_text,
        "requirements": {},
        "team_engineers": [],
        "gaps": [],
        "proposal": "",
        "graph_data": {"nodes": [], "edges": []},
        "agent_trace": [],
    }

    final_state = pipeline.invoke(initial_state)
    logger.info("Pipeline completed. Trace steps: %d", len(final_state["agent_trace"]))
    return final_state
