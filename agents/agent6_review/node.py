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
    
    return state
