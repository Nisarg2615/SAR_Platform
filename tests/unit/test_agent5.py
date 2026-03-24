import pytest
from datetime import datetime
from agents.shared.schemas import SARCase, RiskAssessment, RiskTier
from agents.agent5_audit.node import agent5_write_audit

pytestmark = pytest.mark.asyncio

async def test_agent5_write_audit():
    case = SARCase(
        case_id="TEST-123",
        risk_assessment=RiskAssessment(
            case_id="TEST-123",
            risk_tier=RiskTier.RED,
            risk_score=0.9,
            matched_typology="Structuring",
            typology_confidence=0.8,
            signals=[],
            shap_values={"amount": 0.4},
            neo4j_pattern_found=True,
            assessment_timestamp=datetime.now()
        ),
        audit_trail=[{"agent": "System", "action": "Init", "confidence": 1.0, "timestamp": datetime.now().isoformat()}]
    )
    
    result = await agent5_write_audit(case)
    
    assert result.audit is not None
    assert len(result.audit.immutable_hash) == 64
    assert len(result.audit_trail) == 2
