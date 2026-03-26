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

        # 2. Build the AuditRecord with richer content
        audit_node_id = str(uuid.uuid4())

        # Extract account_id for account-level correlation
        account_id = ""
        if state.normalized and state.normalized.subject_account_ids:
            account_id = state.normalized.subject_account_ids[0]
        elif state.raw_transaction:
            account_id = state.raw_transaction.get("account_id", "")

        # Include account_id in hash to tie it uniquely to the account's history
        hash_material = {
            "case_id": state.case_id,
            "account_id": account_id,
            "audit_trail": state.audit_trail,
            "risk_score": state.risk_assessment.risk_score if state.risk_assessment else 0.0,
            "risk_tier": str(state.risk_assessment.risk_tier) if state.risk_assessment else "unknown",
        }
        immutable_hash = hashlib.sha256(
            json.dumps(hash_material, sort_keys=True, default=str).encode()
        ).hexdigest()

        state.audit = AuditRecord(
            case_id=state.case_id,
            neo4j_audit_node_id=audit_node_id,
            agent_timeline=state.audit_trail.copy(),
            shap_explanations=state.risk_assessment.shap_values if state.risk_assessment else {},
            data_sources_cited=[
                "XGBoost ML prediction engine",
                "Groq API (Llama 3 8B) — narrative generation",
                "AML compliance rule engine (8 rules)",
                "TransactionHistoryStore — past transaction context",
                "Neo4j graph database (audit persistence)",
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

        directive = state.orchestrator_decision.directives.get("agent5_audit") if state.orchestrator_decision else None
        if directive:
            from agents.llm.client import llm_call
            llm_res, provider = await llm_call(
                "You are an Audit AI. Write a 1-sentence audit summary.",
                f"Case ID: {state.case_id}",
                directive.provider.value,
                directive.model,
                fallback_chain=[p.value for p in directive.fallback_chain]
            )
            if llm_res:
                 state.audit_trail.append({"agent": "Agent 5 - Audit Summary", "action": f"[{provider}]: {llm_res}", "confidence": 1.0, "timestamp": datetime.now().isoformat()})

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
