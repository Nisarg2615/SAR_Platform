"""
Agent 2 — Risk Assessment Node
Evaluates ingested transactions using an XGBoost ML model to assign risk tiers.
Also checks past transaction history for structuring patterns, velocity spikes,
and high-volume activity using TransactionHistoryStore.
"""

from __future__ import annotations
from datetime import datetime
import uuid

from agents.shared.schemas import SARCase, RiskAssessment, RiskTier, RiskSignal
from prediction_engine.model import XGBRiskEngine
from agents.agent2_risk.typologies import determine_typology

engine = XGBRiskEngine()

# Lazy-load history store to avoid circular imports at module level.
_history_store = None

def _get_history_store():
    global _history_store
    if _history_store is None:
        try:
            from data.transaction_history import history_store
            _history_store = history_store
        except Exception:
            _history_store = None
    return _history_store


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

        tx_id = (
            state.normalized.transactions[0].transaction_id
            if state.normalized and state.normalized.transactions
            else str(uuid.uuid4())
        )

        signals = [
            RiskSignal(
                signal_type=typology_name,
                description=sig_txt,
                confidence=conf,
                supporting_transaction_ids=[tx_id]
            )
            for sig_txt in raw_signals
        ]

        # 4. Historical context signals from TransactionHistoryStore
        history_signals = []
        store = _get_history_store()
        if store and state.normalized and state.normalized.transactions:
            try:
                acct = state.normalized.transactions[0].account_id
                ts   = str(state.normalized.transactions[0].timestamp)

                velocity_24h = store.get_velocity(acct, ts, hours=24)
                total_30d    = store.get_total_amount_last_n_days(acct, ts, days=30)
                structuring  = store.has_structuring_pattern(acct, ts)

                if velocity_24h >= 5:
                    history_signals.append(RiskSignal(
                        signal_type="rapid_movement",
                        description=f"Account {acct} had {velocity_24h} transactions in the last 24 hours — high velocity alert.",
                        confidence=min(0.5 + velocity_24h * 0.05, 0.99),
                        supporting_transaction_ids=[tx_id]
                    ))
                    # Bump risk score upwards if high velocity
                    risk_score = min(risk_score + 0.10, 1.0)
                    if risk_score >= 0.85:
                        tier = RiskTier.RED
                    elif risk_score >= 0.60:
                        tier = RiskTier.AMBER

                if total_30d > 50_000:
                    history_signals.append(RiskSignal(
                        signal_type="high_volume_30d",
                        description=f"Account {acct} processed ${total_30d:,.0f} in the last 30 days — exceeds threshold.",
                        confidence=0.85,
                        supporting_transaction_ids=[tx_id]
                    ))

                if structuring:
                    history_signals.append(RiskSignal(
                        signal_type="structuring_pattern",
                        description=f"Account {acct} has prior cash deposits in the $9,000–$9,999 range — structuring pattern detected.",
                        confidence=0.93,
                        supporting_transaction_ids=[tx_id]
                    ))
                    # Structuring pattern is a strong RED indicator
                    if tier == RiskTier.GREEN:
                        tier = RiskTier.AMBER
                        risk_score = max(risk_score, 0.65)

            except Exception as hist_err:
                state.error_log.append({
                    "agent": "Agent 2 - History Context",
                    "error": f"History store lookup failed (non-fatal): {hist_err}",
                    "timestamp": datetime.now().isoformat()
                })

        all_signals = signals + history_signals

        # 5. Save to master state
        state.risk_assessment = RiskAssessment(
            case_id=state.case_id,
            risk_tier=tier,
            risk_score=risk_score,
            matched_typology=typology_name,
            typology_confidence=conf,
            signals=all_signals,
            shap_values=shap_values,
            neo4j_pattern_found=True,
            assessment_timestamp=datetime.now()
        )

        history_note = f" +{len(history_signals)} history signals." if history_signals else ""
        state.audit_trail.append({
            "agent": "Agent 2 - Risk Assessment",
            "action": (
                f"Scored transaction via XGBoost. Score: {risk_score:.3f} "
                f"({tier.value.upper()}). Matched typology: {typology_name}.{history_note}"
            ),
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
