"""
Unit tests for Agent 1 (Ingestion)
"""

import pytest
from datetime import datetime
from agents.shared.schemas import SARCase
from agents.agent1_ingestion.node import agent1_ingest

@pytest.mark.asyncio
async def test_agent1_successful_ingestion():
    # Arrange
    raw = {
        "transaction_id": "TX-999",
        "amount_usd": 15000.0,
        "subject_name": "Rick Sanchez",
        "geography": "US"
    }
    state = SARCase(case_id="C-123", raw_transaction=raw)

    # Act
    result = await agent1_ingest(state)

    # Assert
    assert result.normalized is not None
    assert result.normalized.total_amount_usd == 15000.0
    assert result.normalized.presidio_masked is True
    assert result.normalized.subject_name == "[REDACTED]"
    assert len(result.normalized.transactions) == 1
    assert result.normalized.transactions[0].transaction_id == "TX-999"
    assert "Applied Presidio" in result.audit_trail[0]["action"]

@pytest.mark.asyncio
async def test_agent1_handles_empty_input():
    # Arrange
    state = SARCase(case_id="C-456", raw_transaction={})

    # Act
    result = await agent1_ingest(state)

    # Assert
    assert result.normalized is not None
    assert result.normalized.total_amount_usd == 0.0
    assert result.normalized.subject_name == "Unknown"
    assert len(result.error_log) == 0  # Shouldn't fail, uses defaults
