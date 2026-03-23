"""
Agent 2 — Risk Assessment Node
Evaluates ingested transactions using an XGBoost ML model to assign risk tiers.
"""

from __future__ import annotations
from datetime import datetime
import uuid

from agents.shared.schemas import SARCase, RiskAssessment, RiskTier, RiskSignal
from prediction_engine.model import XGBRiskEngine
from agents.agent2_risk.typologies import determine_typology

engine = XGBRiskEngine()


async def agent2_assess_risk(state: SARCase) -> SARCase:
    """
    Agent 2 — Risk Assessment.

    Reads:   state.raw_transaction, state.normalized
    Writes:  state.risk_assessment (RiskAssessment)
    Appends: state.audit_trail
    """
    try:
        raw = state.raw_transaction or {}
        
        # 1. Call XGBoost ML Engine
        risk_score, shap_values = engine.predict_risk(raw)
        
        # 2. Determine threshold
        if risk_score >= 0.85:
            tier = RiskTier.RED
        elif risk_score >= 0.60:
            tier = RiskTier.AMBER
        else:
            tier = RiskTier.GREEN
            
        # 3. Typology Engine
        typology_name, conf, raw_signals = determine_typology(raw, shap_values, risk_score)
        
        tx_id = state.normalized.transactions[0].transaction_id if state.normalized else str(uuid.uuid4())
        
        signals = [
            RiskSignal(
                signal_type=typology_name,
                description=sig_txt,
                confidence=conf,
                supporting_transaction_ids=[tx_id]
            )
            for sig_txt in raw_signals
        ]

        # 4. Save to master state
        state.risk_assessment = RiskAssessment(
            case_id=state.case_id,
            risk_tier=tier,
            risk_score=risk_score,
            matched_typology=typology_name,
            typology_confidence=conf,
            signals=signals,
            shap_values=shap_values,
            neo4j_pattern_found=True,
            assessment_timestamp=datetime.now()
        )

        state.audit_trail.append({
            "agent": "Agent 2 - Risk Assessment",
            "action": f"Scored transaction via XGBoost. Score: {risk_score:.3f} ({tier.value.upper()}). Matched typology: {typology_name}.",
            "confidence": 0.95,
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:
        state.error_log.append({
            "agent": "Agent 2 - Risk Assessment",
            "error": f"Risk assessment failed: {e}",
            "timestamp": datetime.now().isoformat()
        })

    return state
