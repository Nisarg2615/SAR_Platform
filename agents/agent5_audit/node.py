"""
Agent 5 — Audit Trail Writer
LangGraph node: hashes full case state, writes to Neo4j, populates state.audit.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from agents.shared.schemas import SARCase, AuditRecord


def _serialize_state(state: SARCase) -> str:
    """Serialize SARCase to a deterministic JSON string for hashing."""
    # Use model_dump with explicit mode to handle datetime serialization
    data = state.model_dump(mode="json")
    return json.dumps(data, sort_keys=True, default=str)


async def agent5_write_audit(state: SARCase) -> SARCase:
    """
    Agent 5 — Audit Trail.

    Reads:   full SARCase state
    Writes:  state.audit (AuditRecord) with SHA256 immutable hash
    Writes:  Neo4j — SARCase node + AuditEvent node via GraphWriter
    Appends: state.audit_trail
    Never raises.
    """
    try:
        # 1. Serialize and hash the full state
        json_str = _serialize_state(state)
        immutable_hash = hashlib.sha256(json_str.encode()).hexdigest()

        # 2. Build the AuditRecord
        audit_node_id = str(uuid.uuid4())
        state.audit = AuditRecord(
            case_id=state.case_id,
            neo4j_audit_node_id=audit_node_id,
            agent_timeline=state.audit_trail.copy(),
            shap_explanations=state.risk_assessment.shap_values if state.risk_assessment else {},
            data_sources_cited=[
                "XGBoost prediction engine",
                "MiniMax-Text-2.5 LLM",
                "AML compliance rule engine",
                "Neo4j graph database",
            ],
            audit_timestamp=datetime.now(),
            immutable_hash=immutable_hash,
        )

        # 3. Append final entry to audit trail
        final_entry = {
            "agent": "Agent 5 - Audit Trail",
            "action": f"State hashed (SHA256: {immutable_hash[:16]}...) and written to Neo4j",
            "confidence": 1.0,
            "timestamp": datetime.now().isoformat(),
        }
        state.audit_trail.append(final_entry)

        # 4. Write to Neo4j via GraphWriter (lazy import to avoid circular deps)
        try:
            from graph.neo4j.graph_writer import GraphWriter
            gw = GraphWriter()
            gw.write_sar_case(state)
            # Write each audit trail entry as an immutable AuditEvent node
            for entry in state.audit_trail:
                gw.write_audit_event({**entry, "case_id": state.case_id})
            gw.close()
        except Exception as neo4j_err:
            # Neo4j being down must NOT crash the pipeline
            state.error_log.append({
                "agent": "Agent 5 - Audit Trail",
                "error": f"Neo4j write failed (non-fatal): {neo4j_err}",
                "timestamp": datetime.now().isoformat(),
            })

    except Exception as e:
        state.error_log.append({
            "agent": "Agent 5 - Audit Trail",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })

    return state
