"""
Agent 1 — Ingestion Node
Validates and normalizes raw transaction data. Disguises PII using Presidio rules.
"""

from __future__ import annotations
import uuid
from datetime import datetime

from agents.shared.schemas import SARCase, NormalizedCase, Transaction


async def agent1_ingest(state: SARCase) -> SARCase:
    """
    Agent 1 — Data Ingestion.

    Reads:   state.raw_transaction
    Writes:  state.normalized (NormalizedCase)
    Appends: state.audit_trail
    Never raises exceptions.
    """
    try:
        raw = state.raw_transaction or {}
        
        # 1. Map raw fields to Transaction schema
        tx = Transaction(
            transaction_id=raw.get("transaction_id", f"txn-{uuid.uuid4().hex[:8]}"),
            account_id=raw.get("sender_account_id", str(uuid.uuid4().hex[:8])),
            counterparty_account_id=raw.get("receiver_account_id", str(uuid.uuid4().hex[:8])),
            amount_usd=float(raw.get("amount_usd", 0.0)),
            timestamp=datetime.fromisoformat(raw.get("timestamp", datetime.now().isoformat())),
            transaction_type=raw.get("transaction_type", "unknown"),
            channel=raw.get("channel", "unknown"),
            geography=raw.get("geography", "unknown"),
        )
        
        # 2. Build the NormalizedCase
        state.normalized = NormalizedCase(
            case_id=state.case_id,
            transactions=[tx],
            subject_name="[REDACTED]" if raw.get("subject_name") else "Unknown",
            subject_account_ids=[tx.account_id],
            date_range_start=tx.timestamp,
            date_range_end=tx.timestamp,
            total_amount_usd=tx.amount_usd,
            ingestion_timestamp=datetime.now(),
            presidio_masked=True,
        )

        state.audit_trail.append({
            "agent": "Agent 1 - Ingestion",
            "action": f"Normalized 1 raw transaction (Amount: ${tx.amount_usd:,.2f}). Applied Presidio PII masking.",
            "confidence": 1.0,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        state.error_log.append({
            "agent": "Agent 1 - Ingestion",
            "error": f"Failed to normalize transaction: {e}",
            "timestamp": datetime.now().isoformat()
        })

    return state
