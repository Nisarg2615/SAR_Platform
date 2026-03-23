"""
Unit tests for Agent 2 (Risk Assessment)
"""

import pytest
from agents.shared.schemas import SARCase, NormalizedCase, Transaction
from agents.agent1_ingestion.node import agent1_ingest
from agents.agent2_risk.node import agent2_assess_risk
from prediction_engine.simulator import get_structuring_scenario, get_layering_scenario

@pytest.mark.asyncio
async def test_agent2_structuring_risk():
    # Arrange
    scenario = get_structuring_scenario()
    # We only pass the first transaction of the scenario through Agent 1 for this test
    # (In reality, pipeline receives the whole dict, but our schema extracts one tx for demo purposes)
    tx = scenario["transactions"][0]
    state = SARCase(case_id="C-STRUCT", raw_transaction=tx)
    
    # Act
    state = await agent1_ingest(state)
    state = await agent2_assess_risk(state)

    # Assert
    assert state.risk_assessment is not None
    assert state.risk_assessment.risk_score >= 0.0
    assert state.risk_assessment.matched_typology in ["Structuring", "Wire Fraud / General Attempt"]
    assert "transaction_frequency_7d" in state.risk_assessment.shap_values
    assert len(state.audit_trail) == 2  # 1 from agent1, 1 from agent2

@pytest.mark.asyncio
async def test_agent2_layering_risk():
    # Arrange
    scenario = get_layering_scenario()
    tx = scenario["transactions"][0]
    state = SARCase(case_id="C-LAYER", raw_transaction=tx)
    
    # Act
    state = await agent1_ingest(state)
    state = await agent2_assess_risk(state)

    # Assert
    assert state.risk_assessment is not None
    assert state.risk_assessment.matched_typology in ["Layering", "Wire Fraud / General Attempt"]
    assert len(state.risk_assessment.signals) > 0
