"""
agents/pipeline.py
LangGraph Orchestrator for the SAR Platform.
Wires the agents together based on RiskTier.
"""

from langgraph.graph import StateGraph, START, END

from agents.shared.schemas import SARCase, RiskTier
from agents.agent1_ingestion.node import agent1_ingest
from agents.agent2_risk.node import agent2_assess_risk
from agents.agent3_narrative.node import agent3_generate_narrative
from agents.agent4_compliance.node import agent4_check_compliance
from agents.agent5_audit.node import agent5_write_audit


def check_tier(state: SARCase) -> str:
    """Conditional edge logic: route based on RiskTier."""
    if not state.risk_assessment:
        return "narrative" # Failsafe
    if state.risk_assessment.risk_tier in [RiskTier.RED, RiskTier.AMBER, RiskTier.CRITICAL]:
        return "narrative"
    return "skip"


from typing import Any

def build_pipeline() -> Any:
    """Constructs the SAR LangGraph pipeline."""
    workflow = StateGraph(SARCase)
    
    # Add Nodes
    workflow.add_node("agent1", agent1_ingest)
    workflow.add_node("agent2", agent2_assess_risk)
    workflow.add_node("agent3", agent3_generate_narrative)
    workflow.add_node("agent4", agent4_check_compliance)
    workflow.add_node("agent5", agent5_write_audit)
    
    # Define Edges
    workflow.add_edge(START, "agent1")
    workflow.add_edge("agent1", "agent2")
    
    # Conditional Routing after Agent 2
    workflow.add_conditional_edges(
        "agent2",
        check_tier,
        {
            "narrative": "agent3",
            "skip": "agent5"
        }
    )
    
    workflow.add_edge("agent3", "agent4")
    workflow.add_edge("agent4", "agent5")
    workflow.add_edge("agent5", END)
    
    return workflow.compile()


# Export compiled app
app = build_pipeline()
