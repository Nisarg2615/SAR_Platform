"""
Agent 6 — Human Review Node
Accepts analyst input and marks case as FILED or DISMISSED.
"""

from datetime import datetime
from agents.shared.schemas import SARCase, SARStatus

async def agent6_review(state: SARCase, analyst_name: str) -> SARCase:
    """Agent 6 is called directly by the FastAPI endpoint, not the LangGraph pipeline."""
    state.analyst_approved_by = analyst_name
    state.status = SARStatus.FILED
    state.final_filed_timestamp = datetime.now()
    
    state.audit_trail.append({
        "agent": "Agent 6 - Manual Review",
        "action": f"Analyst {analyst_name} reviewed and finalized the SAR as FILED.",
        "confidence": 1.0,
        "timestamp": datetime.now().isoformat()
    })
    
    directive = state.orchestrator_decision.directives.get("agent6_review") if state.orchestrator_decision else None
    if directive:
        from agents.llm.client import llm_call
        llm_res, provider = await llm_call(
            "You are a Review Assistant. Write a 1-sentence approval recommendation.",
            f"Analyst {analyst_name} is approving case {state.case_id}.",
            directive.provider.value,
            directive.model,
            fallback_chain=[p.value for p in directive.fallback_chain]
        )
        if llm_res:
             state.audit_trail.append({"agent": "Agent 6 - AI Recommendation", "action": f"[{provider}]: {llm_res}", "confidence": 1.0, "timestamp": datetime.now().isoformat()})

    return state
