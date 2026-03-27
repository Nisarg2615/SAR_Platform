"""
main.py
FastAPI Backend for SAR Platform.
Serves 10 endpoints for the UI to interact with the LangGraph pipeline.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(".env.local")

from agents.shared.schemas import SARCase, SARStatus
from agents.pipeline import app as pipeline_app
from agents.agent3_narrative.node import agent3_generate_narrative
from agents.agent6_review.node import agent6_review
from prediction_engine.model import train_and_save_model
from prediction_engine.simulator import (
    get_structuring_scenario,
    get_layering_scenario,
    get_smurfing_scenario
)
from graph.neo4j.graph_api import get_case_graph
from agents.shared.schemas import SARReportData
from reports.typology_definitions import classify_typology
from reports.pdf_generator import generate_sar_pdf
from fastapi.responses import Response

app = FastAPI(title="SAR Platform API", version="1.0.0")

# Setup CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database for hackathon purposes
import json
import os

DB: Dict[str, SARCase] = {}

if os.path.exists("mock_db.json"):
    try:
        with open("mock_db.json", "r") as f:
            data = json.load(f)
            DB = {k: SARCase(**v) for k, v in data.items()}
        print(f"Loaded {len(DB)} mock cases from mock_db.json")
    except Exception as e:
        print(f"Failed to load mock_db.json: {e}")

if os.path.exists("data/batch_results.json"):
    try:
        with open("data/batch_results.json", "r") as f:
            batch_data = json.load(f)
            loaded = 0
            for k, v in batch_data.items():
                if k not in DB:  # don't overwrite mock cases
                    DB[k] = SARCase(**v)
                    loaded += 1
        print(f"Loaded {loaded} batch cases from data/batch_results.json (total DB: {len(DB)})")
    except Exception as e:
        print(f"Failed to load data/batch_results.json: {e}")



class ApproveRequest(BaseModel):
    analyst_name: str = "Analyst-1"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

from agents.orchestrator.health_cache import health_cache
from agents.orchestrator.budget_tracker import budget_tracker
from agents.llm.config import PROVIDER_CONFIGS, AGENT_PRIMARY_PROVIDER, AGENT_MODEL_SIZE

@app.get("/health")
async def health_check():
    """Basic health endpoint."""
    red_count = sum(1 for c in DB.values() if c.risk_assessment and str(c.risk_assessment.risk_tier) in ("red", "critical"))
    
    providers_configured = {}
    provider_health = {}
    
    for p_name, cfg in PROVIDER_CONFIGS.items():
        providers_configured[p_name] = bool(os.getenv(cfg.get("api_key_env", "")))
        provider_health[p_name] = health_cache.is_healthy(p_name)
        
    agent_routing = {}
    for agent_name, primary in AGENT_PRIMARY_PROVIDER.items():
        if not primary:
            continue
        size = AGENT_MODEL_SIZE.get(agent_name, "small")
        cfg = PROVIDER_CONFIGS.get(primary, {})
        model = cfg.get("models", {}).get(size) or cfg.get("models", {}).get("small", "unknown")
        agent_routing[agent_name] = f"{primary}:{model}"

    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "cases": {"total": len(DB), "red": red_count, "other": len(DB) - red_count},
        "orchestrator": {
            "providers_configured": providers_configured,
            "provider_health": provider_health,
            "budget_status": budget_tracker.get_status(),
            "agent_routing": agent_routing
        }
    }


@app.post("/api/model/train")
async def trigger_training():
    """Manually triggers the XGBoost model training."""
    try:
        train_and_save_model()
        return {"status": "success", "message": "XGBoost model trained and saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Model training failed", "detail": str(e)})



# ---------------------------------------------------------------------------
# Transaction submission
# ---------------------------------------------------------------------------

@app.post("/submit-transaction")
async def submit_transaction(payload: dict):
    """
    Submits raw transaction payload.
    Initializes SARCase in PENDING state and stores it.
    Returns: {"case_id": "..."}
    """
    try:
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        case = SARCase(
            case_id=case_id,
            status=SARStatus.PENDING,
            raw_transaction=payload
        )
        case.audit_trail.append({
            "agent": "System API",
            "action": f"Transaction submitted and case {case_id} initialized.",
            "confidence": 1.0,
            "timestamp": datetime.now().isoformat()
        })
        DB[case_id] = case
        return {"case_id": case_id, "status": case.status}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


# ---------------------------------------------------------------------------
# Case listing and retrieval
# ---------------------------------------------------------------------------

@app.get("/cases")
async def get_cases():
    """Returns a list of all cases and their high-level statuses."""
    return [
        {
            "case_id": c.case_id,
            "status": c.status,
            "risk_tier": c.risk_assessment.risk_tier if c.risk_assessment else "pending",
            "subject": c.normalized.subject_name if c.normalized else "Unknown",
            "last_updated": c.audit_trail[-1]["timestamp"] if c.audit_trail else "Unknown"
        }
        for c in DB.values() if c.audit is not None
    ]


@app.get("/case/{case_id}")
async def get_case(case_id: str):
    """Returns the full SARCase JSON structure."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    return DB[case_id].model_dump()


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

@app.post("/case/{case_id}/run-pipeline")
async def run_pipeline(case_id: str):
    """
    Synchronously triggers the full LangGraph pipeline for the given case.
    Updates the in-memory master state.
    """
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")

    case_state = DB[case_id]
    if case_state.status not in [SARStatus.PENDING, SARStatus.IN_REVIEW]:
        raise HTTPException(status_code=400, detail=f"Case already processed (status={case_state.status})")

    try:
        # LangGraph StateGraph compiled with SARCase needs a dict input
        input_dict = case_state.model_dump()
        final_state_dict = await pipeline_app.ainvoke(input_dict)
        # Reconstruct SARCase from the result dict
        updated_case = SARCase(**final_state_dict)
        updated_case.status = SARStatus.IN_REVIEW
        DB[case_id] = updated_case
        return {
            "status": "success",
            "message": "Pipeline completed successfully",
            "case_id": case_id,
            "risk_tier": updated_case.risk_assessment.risk_tier if updated_case.risk_assessment else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Pipeline execution failed", "detail": str(e)})


@app.get("/case/{case_id}/pipeline-status")
async def get_pipeline_status(case_id: str):
    """Returns which agents have completed (non-None outputs in state)."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    case = DB[case_id]
    return {
        "case_id": case_id,
        "status": case.status,
        "agents_completed": {
            "agent1_ingestion": case.normalized is not None,
            "agent2_risk": case.risk_assessment is not None,
            "agent3_narrative": case.narrative is not None,
            "agent4_compliance": case.compliance is not None,
            "agent5_audit": case.audit is not None,
            "agent6_review": case.analyst_approved_by is not None,
        },
        "audit_trail_entries": len(case.audit_trail),
        "error_count": len(case.error_log),
    }


# ---------------------------------------------------------------------------
# Narrative generation (standalone for UI button)
# ---------------------------------------------------------------------------

@app.post("/case/{case_id}/generate-narrative")
async def generate_narrative(case_id: str):
    """
    Triggers Agent 3 narrative generation standalone (for the UI narrative button).
    The case must have passed Agent 2 (risk_assessment must be populated).
    """
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")

    case = DB[case_id]
    if not case.risk_assessment:
        raise HTTPException(
            status_code=400,
            detail="Risk assessment not complete. Run the pipeline first."
        )

    try:
        updated_case = await agent3_generate_narrative(case)
        DB[case_id] = updated_case
        if updated_case.narrative:
            return {
                "status": "success",
                "narrative": updated_case.narrative.model_dump(),
                "narrative_body": updated_case.narrative.narrative_body,
            }
        else:
            errors = [e.get("error") for e in updated_case.error_log if "Agent 3" in e.get("agent", "")]
            raise HTTPException(
                status_code=500,
                detail={"error": "Narrative generation failed", "errors": errors}
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


# ---------------------------------------------------------------------------
# SAR Report Data and PDF Generation (Feature 3)
# ---------------------------------------------------------------------------

@app.get("/case/{case_id}/report-data", response_model=SARReportData)
async def get_report_data(case_id: str):
    """Retrieves or assembles the editable SAR report data."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")

    case = DB[case_id]
    
    # If already saved by PUT previously, return it
    if case.sar_report:
        return case.sar_report
        
    # Otherwise, assemble fresh from the case state
    report = SARReportData.from_sar_case(case)
    
    # Refine typology using the central registry based on triggers
    if case.risk_assessment and case.risk_assessment.signals:
        signal_types = [s.signal_type for s in case.risk_assessment.signals]
        best_name, best_entry = classify_typology(signal_types)
        if best_name != "Unknown":
            report.typology = best_name
            report.typology_code = best_entry.get("code", "")
            report.typology_description = best_entry.get("description", "")
            report.regulatory_references = best_entry.get("regulatory_references", [])
            
    return report

import json
import os

BATCH_RESULTS_PATH = os.path.join(os.path.dirname(__file__), "data", "batch_results.json")

def persist_db_to_disk():
    """Helper to save the current in-memory DB so UI edits are not lost."""
    try:
        combined = {k: v.dict() for k, v in DB.items()}
        with open(BATCH_RESULTS_PATH, "w") as f:
            json.dump(combined, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Failed to persist DB: {e}")

@app.put("/case/{case_id}/report-data", response_model=SARReportData)
async def update_report_data(case_id: str, body: SARReportData):
    """Saves the user-edited SAR report data back to the case."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")

    DB[case_id].sar_report = body
    persist_db_to_disk()
    return body

@app.post("/case/{case_id}/generate-pdf")
async def generate_pdf(case_id: str, report: SARReportData):
    """Generates the 7-page PDF report buffer from the provided data."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
        
    try:
        pdf_bytes = generate_sar_pdf(report, case_id)
        # Return as downloadable PDF file
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="SAR_{case_id}.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": f"Failed to generate PDF: {str(e)}"})


# ---------------------------------------------------------------------------
# Case approval and dismissal
# ---------------------------------------------------------------------------

@app.post("/case/{case_id}/approve")
async def approve_case(case_id: str, body: ApproveRequest = ApproveRequest()):
    """Analyst approves the generated SAR for filing."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")

    try:
        case = DB[case_id]
        case = await agent6_review(case, body.analyst_name)
        DB[case_id] = case
        return {"status": "success", "case_status": case.status, "filed_by": body.analyst_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


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


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

@app.get("/case/{case_id}/audit")
async def get_case_audit(case_id: str):
    """Returns just the audit trail for a case."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"audit_trail": DB[case_id].audit_trail}


# ---------------------------------------------------------------------------
# Account-level audit trail (Feature 2)
# ---------------------------------------------------------------------------

@app.get("/account/{account_id}/audit-trail")
async def get_account_audit_trail(account_id: str):
    """
    Returns all SAR cases associated with the given account_id,
    with full agent decisions and audit hashes. Supports multi-case history.
    """
    matching_cases = []
    for case in DB.values():
        # Check subject_account_ids in normalized, or raw_transaction account_id
        account_ids = []
        if case.normalized:
            account_ids = list(case.normalized.subject_account_ids or [])
        if not account_ids and case.raw_transaction:
            raw_acct = case.raw_transaction.get("account_id", "")
            if raw_acct:
                account_ids = [raw_acct]

        if account_id in account_ids:
            tier = str(case.risk_assessment.risk_tier) if case.risk_assessment else "unknown"
            matching_cases.append({
                "case_id": case.case_id,
                "status": str(case.status),
                "risk_score": case.risk_assessment.risk_score if case.risk_assessment else 0.0,
                "risk_tier": tier,
                "typology": case.risk_assessment.matched_typology if case.risk_assessment else "Unknown",
                "filed_at": str(case.final_filed_timestamp) if case.final_filed_timestamp else None,
                "analyst": case.analyst_approved_by,
                "agent_decisions": case.audit_trail,
                "immutable_hash": case.audit.immutable_hash if case.audit else None,
                "total_amount_usd": case.normalized.total_amount_usd if case.normalized else 0.0,
            })

    if not matching_cases:
        raise HTTPException(status_code=404, detail={"error": f"No cases found for account {account_id}"})

    sar_cases = [c for c in matching_cases if c["risk_tier"] in ("red", "critical")]
    dismissed = [c for c in matching_cases if c["status"] == "dismissed"]
    all_scores = [c["risk_score"] for c in matching_cases if c["risk_score"] > 0]
    avg_score = round(sum(all_scores) / len(all_scores), 3) if all_scores else 0.0

    return {
        "account_id": account_id,
        "total_cases": len(matching_cases),
        "total_sar_required": len(sar_cases),
        "total_dismissed": len(dismissed),
        "risk_score_avg": avg_score,
        "cases": sorted(matching_cases, key=lambda x: x["filed_at"] or "", reverse=True)
    }



# ---------------------------------------------------------------------------
# Graph visualization
# ---------------------------------------------------------------------------

@app.get("/case/{case_id}/graph")
async def get_case_graph_endpoint(case_id: str):
    """Fetches nodes and edges for Pyvis visualization (from Neo4j)."""
    if case_id not in DB:
        raise HTTPException(status_code=404, detail="Case not found")

    graph_data = get_case_graph(case_id)
    if "error" in graph_data and not graph_data.get("nodes"):
        # Neo4j may be offline — return empty graph gracefully
        return {"nodes": [], "edges": [], "warning": graph_data.get("error")}

    return graph_data


# ---------------------------------------------------------------------------
# Pipeline Refresh (Live Data Reload)
# ---------------------------------------------------------------------------

@app.post("/api/pipeline/refresh")
async def refresh_pipeline(limit: int = 300):
    """
    1. Clears current in-memory DB and disk mock_db.json.
    2. Reloads the SAR CSV and a sample of the Fraud CSV.
    3. Re-runs the entire 6-Agent LangGraph for each transaction.
    """
    global DB
    DB.clear()
    
    # Clear physical disk DB
    if os.path.exists("mock_db.json"):
        os.remove("mock_db.json")
    if os.path.exists("data/batch_results.json"):
        os.remove("data/batch_results.json")

    SAR_CSV = "suspicious-activity-reports-sar.csv"
    FRAUD_CSV = "Bank_Transaction_Fraud_Detection.csv"
    
    processed_count = 0
    sar_limit = limit // 2
    fraud_limit = limit - sar_limit
    
    # 1. Process SAR Dataset (Priority)
    if os.path.exists(SAR_CSV):
        try:
            import pandas as pd
            df_sar = pd.read_csv(SAR_CSV).head(sar_limit) 
            for _, row in df_sar.iterrows():
                tx_payload = row.to_dict()
                case_id = f"CASE-SAR-{uuid.uuid4().hex[:4].upper()}"
                case = SARCase(case_id=case_id, status=SARStatus.PENDING, raw_transaction=tx_payload)
                DB[case_id] = case
                # Run pipeline
                input_dict = case.model_dump()
                final_state = await pipeline_app.ainvoke(input_dict)
                DB[case_id] = SARCase(**final_state)
                DB[case_id].status = SARStatus.IN_REVIEW
                processed_count += 1
        except Exception as e:
            print(f"Error refreshing SAR data: {e}")

    # 2. Process Fraud Dataset Sample
    if os.path.exists(FRAUD_CSV):
        try:
            import pandas as pd
            df_fraud = pd.read_csv(FRAUD_CSV).head(fraud_limit)
            for _, row in df_fraud.iterrows():
                tx_payload = row.to_dict()
                case_id = f"CASE-FRD-{uuid.uuid4().hex[:4].upper()}"
                case = SARCase(case_id=case_id, status=SARStatus.PENDING, raw_transaction=tx_payload)
                DB[case_id] = case
                # Run pipeline
                input_dict = case.model_dump()
                final_state = await pipeline_app.ainvoke(input_dict)
                DB[case_id] = SARCase(**final_state)
                DB[case_id].status = SARStatus.IN_REVIEW
                processed_count += 1
        except Exception as e:
            print(f"Error refreshing Fraud data: {e}")

    # Persist the fresh start
    persist_db_to_disk()
    
    return {
        "status": "success",
        "message": f"Successfully cleared DB and re-processed {processed_count} cases.",
        "total_cases": len(DB)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
