"""
main.py
FastAPI Backend for SAR Platform.
Serves 10 endpoints for the UI to interact with the LangGraph pipeline.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
import uuid
from datetime import datetime

from agents.shared.schemas import SARCase, SARStatus
from agents.pipeline import app as pipeline_app
from prediction_engine.simulator import (
    get_structuring_scenario,
    get_layering_scenario,
    get_smurfing_scenario
)
from graph.neo4j.graph_api import get_case_graph

app = FastAPI(title="SAR Platform API")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database for hackathon purposes
# map string case_id -> SARCase object
DB: Dict[str, SARCase] = {}


@app.get("/health")
async def health_check():
    """Basic health endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/submit-transaction")
async def submit_transaction(payload: dict):
    """
    1. Submits raw transaction payload.
    2. Initializes SARCase in PENDING state.
    3. Saves to memory.
    Returns: {"case_id": "..."}
    """
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    case = SARCase(
        case_id=case_id,
        status=SARStatus.PENDING,
        raw_transaction=payload
    )
    # Add initial audit log
    case.audit_trail.append({
        "agent": "System API",
        "action": f"Transaction submitted and case {case_id} initialized.",
        "confidence": 1.0,
        "timestamp": datetime.now().isoformat()
    })
    
    DB[case_id] = case
    return {"case_id": case_id, "status": case.status}


@app.get("/cases")
async def get_cases():
    """Returns a list of all cases and their high-level statuses."""
    return [
        {
            "case_id": c.case_id,
            "status": c.status,
            "risk_tier": c.risk_assessment.risk_tier if c.risk_assessment else "PENDING",
            "subject": c.normalized.subject_name if c.normalized else "Unknown",
            "last_updated": c.audit_trail[-1]["timestamp"] if c.audit_trail else "Unknown"
        }
        for c in DB.values()
    ]


@app.get("/case/{case_id}")
async def get_case(case_id: str):
    """Returns the full SARCase JSON structure."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    return DB[case_id].model_dump()


@app.post("/case/{case_id}/run-pipeline")
async def run_pipeline(case_id: str):
    """
    Synchronously triggers the LangGraph pipeline for the given case.
    Updates the in-memory master state.
    """
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case_state = DB[case_id]
    if case_state.status != SARStatus.PENDING:
        raise HTTPException(status_code=400, detail="Case already processed")
        
    try:
        # Run LangGraph state machine
        final_state = await pipeline_app.ainvoke(case_state)
        # Update state status
        final_state["status"] = SARStatus.IN_REVIEW
        # Save back to DB
        updated_case = SARCase(**final_state)
        DB[case_id] = updated_case
        return {"status": "success", "message": "Pipeline completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@app.post("/case/{case_id}/approve")
async def approve_case(case_id: str):
    """Analyst approves the generated SAR for filing."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case = DB[case_id]
    case.status = SARStatus.APPROVED
    case.analyst_approved_by = "Analyst-1"
    case.audit_trail.append({
        "agent": "Analyst UI",
        "action": "Case approved by Analyst-1",
        "confidence": 1.0,
        "timestamp": datetime.now().isoformat()
    })
    return {"status": "success", "case_status": case.status}


@app.post("/case/{case_id}/dismiss")
async def dismiss_case(case_id: str):
    """Analyst dismisses the alert (false positive)."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case = DB[case_id]
    case.status = SARStatus.DISMISSED
    case.audit_trail.append({
        "agent": "Analyst UI",
        "action": "Case dismissed as false positive",
        "confidence": 1.0,
        "timestamp": datetime.now().isoformat()
    })
    return {"status": "success", "case_status": case.status}


@app.get("/case/{case_id}/audit")
async def get_case_audit(case_id: str):
    """Returns just the audit trail for a case."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"audit_trail": DB[case_id].audit_trail}


@app.get("/case/{case_id}/graph")
async def get_case_graph_endpoint(case_id: str):
    """Fetches nodes and edges for Pyvis visualization."""
    if case_id not in DB:
        # Even if not in memory, we can check Neo4j for it
        pass
    
    # Call Nisarg's graph API
    graph_data = get_case_graph(case_id)
    if "error" in graph_data:
        raise HTTPException(status_code=500, detail=graph_data["error"])
        
    return graph_data


@app.post("/demo/simulate/{scenario}")
async def simulate_scenario(scenario: str):
    """
    Demo endpoint: Generates a raw transaction based on a scenario,
    submits it, and returns the tx dict + case id.
    Options: structuring, layering, smurfing.
    """
    scenario_map = {
        "structuring": get_structuring_scenario,
        "layering": get_layering_scenario,
        "smurfing": get_smurfing_scenario
    }
    
    if scenario not in scenario_map:
        raise HTTPException(status_code=400, detail="Invalid scenario type")
        
    tx_payload = scenario_map[scenario]()
    
    # Auto loop it into the system
    result = await submit_transaction(tx_payload)
    
    return {
        "case_id": result["case_id"],
        "scenario_type": scenario,
        "raw_transaction": tx_payload
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
