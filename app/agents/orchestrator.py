"""
Multi-Agent Orchestrator using LangGraph StateGraph.

Each agent is now a real LLM agent with bound tools (ReAct pattern).
The orchestrator wires the agents sequentially and accumulates their traces.

Flow: ParseRFP → BuildTeam (GraphRAG + tools) → AnalyzeGaps (tools) → DraftProposal → BuildGraphData
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
    agent_trace: Annotated[list, operator.add]  # append-only across all nodes


# ── Node Functions ─────────────────────────────────────────────────────────────

def parse_rfp_node(state: PipelineState) -> dict:
    agent = RFPParserAgent()
    result = agent.run(state["rfp_text"])
    req = result.get("requirements", {})
    return {
        "requirements": req,
        "agent_trace": [{
            "agent": result["agent"],
            "status": result["status"],
            "output": (
                f"Extracted {len(req.get('skills', []))} skills, "
                f"sector={req.get('sector', 'N/A')}, "
                f"compliance={req.get('compliance_frameworks', [])}"
            ),
            "tools_used": [],
        }],
    }


def build_team_node(state: PipelineState) -> dict:
    """
    Real agentic node: LLM autonomously calls GraphRAG tools (vector search +
    graph traversal + skill/compliance/sector queries) to find engineers.
    """
    agent = TeamBuilderAgent()
    result = agent.run(state["requirements"])
    engineers = result.get("engineers", [])
    tools_used = result.get("tools_used", [])
    return {
        "team_engineers": engineers,
        "agent_trace": [{
            "agent": result["agent"],
            "status": result["status"],
            "output": (
                f"Found {len(engineers)} engineers via {len(tools_used)} tool calls "
                f"({', '.join(tools_used)}). "
                + (f"Top: {engineers[0]['name']} ({engineers[0].get('match_score', 0):.2f})" if engineers else "No candidates.")
            ),
            "tools_used": tools_used,
        }],
    }


def analyze_gaps_node(state: PipelineState) -> dict:
    """Real agentic node: LLM calls graph tools to detect and explain skill gaps."""
    agent = GapAnalystAgent()
    result = agent.run(state["requirements"], state["team_engineers"])
    gaps = result.get("gaps", [])
    return {
        "gaps": gaps,
        "agent_trace": [{
            "agent": result["agent"],
            "status": result["status"],
            "output": (
                f"{len(gaps)} gap(s): {', '.join(g['skill'] for g in gaps)}"
                if gaps else "No gaps — full coverage!"
            ),
            "tools_used": ["identify_skill_gaps", "get_team_skill_coverage"],
        }],
    }


def draft_proposal_node(state: PipelineState) -> dict:
    agent = ProposalDrafterAgent()
    result = agent.run(state["requirements"], state["team_engineers"], state["gaps"])
    return {
        "proposal": result.get("proposal", ""),
        "agent_trace": [{
            "agent": result["agent"],
            "status": result["status"],
            "output": f"Proposal generated ({len(result.get('proposal', ''))} chars).",
            "tools_used": [],
        }],
    }


def build_graph_data_node(state: PipelineState) -> dict:
    graph_svc = GraphRAGService()
    engineer_ids = [e["id"] for e in state["team_engineers"]]
    graph_data = graph_svc.build_graph_visualization_data(engineer_ids)
    return {
        "graph_data": graph_data,
        "agent_trace": [{
            "agent": "GraphVisualizationAgent",
            "status": "success",
            "output": (
                f"Visualization built: {len(graph_data.get('nodes', []))} nodes, "
                f"{len(graph_data.get('edges', []))} edges."
            ),
            "tools_used": [],
        }],
    }


# ── Graph Builder ──────────────────────────────────────────────────────────────

def build_pipeline() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("parse_rfp",        parse_rfp_node)
    graph.add_node("build_team",       build_team_node)
    graph.add_node("analyze_gaps",     analyze_gaps_node)
    graph.add_node("draft_proposal",   draft_proposal_node)
    graph.add_node("build_graph_data", build_graph_data_node)

    graph.set_entry_point("parse_rfp")
    graph.add_edge("parse_rfp",        "build_team")
    graph.add_edge("build_team",       "analyze_gaps")
    graph.add_edge("analyze_gaps",     "draft_proposal")
    graph.add_edge("draft_proposal",   "build_graph_data")
    graph.add_edge("build_graph_data", END)

    return graph.compile()


def run_pipeline(rfp_text: str) -> dict:
    logger.info("Starting OffshoreIQ MAS pipeline...")
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
    logger.info("Pipeline complete. Trace steps: %d", len(final_state["agent_trace"]))
    return final_state
