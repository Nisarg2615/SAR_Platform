"""
Agent 2 — Typology Definitions
Defines basic logic to map raw transaction metadata and SHAP predictions into defined AML typologies.
"""

from typing import Tuple


def determine_typology(tx_dict: dict, shap_values: dict, risk_score: float) -> Tuple[str, float, list[str]]:
    """
    Determine the most likely AML typology given the transaction data and SHAP values.
    
    Returns:
        (typology_name: str, confidence: float, signals: list[str])
    """
    amount = float(tx_dict.get("amount_usd", 0.0))
    geo = tx_dict.get("geography", "").lower()
    
    signals = []
    
    # 1. Structuring Typology Match
    if 9500 <= amount <= 9999:
        signals.append("Amount falls just below $10k BSA reporting threshold.")
        if "transaction_frequency_7d" in shap_values and shap_values["transaction_frequency_7d"] > 0:
            signals.append("High transaction frequency identified by ML model.")
        return "Structuring", min(0.85 + (risk_score * 0.1), 0.99), signals
        
    # 2. Layering Typology Match
    if amount > 100000 and geo in ["offshore", "cayman islands", "panama"]:
        signals.append("Large volume transaction to high-risk jurisdiction.")
        return "Layering", min(0.90 + (risk_score * 0.05), 0.99), signals
        
    # 3. Smurfing Typology Match
    if 2000 <= amount <= 5000 and tx_dict.get("transaction_type") == "p2p_transfer":
        signals.append("P2P transfer sequence indicative of coordinated smurfing.")
        return "Smurfing", min(0.80 + (risk_score * 0.1), 0.95), signals
        
    # Default fallback
    return "Wire Fraud / General Attempt", max(0.60, risk_score * 0.8), ["Anomalous transaction patterns flagged by XGBoost."]
