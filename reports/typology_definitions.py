"""
AML Typology Definitions Registry
Defines the mapping between ML signals and regulatory fraud typologies.
"""

TYPOLOGY_REGISTRY = {
    "Structuring": {
        "code": "BSA-ST",
        "description": "Multiple cash transactions deliberately kept below the $10,000 CTR reporting threshold under 31 U.S.C. § 5324.",
        "regulatory_references": ["31 U.S.C. § 5324", "31 CFR 1010.314", "FinCEN Advisory FIN-2014-A001"],
        "signals": ["structuring_pattern", "cash_deposit", "below_threshold"]
    },
    "Layering": {
        "code": "BSA-LAY",
        "description": "Rapid movement of funds through multiple accounts and jurisdictions to obscure the trail of illicit proceeds.",
        "regulatory_references": ["18 U.S.C. § 1956", "FATF Recommendation 1", "BSA 31 U.S.C. § 5318"],
        "signals": ["round_trip", "wire_transfer", "rapid_movement"]
    },
    "Rapid Movement": {
        "code": "BSA-RM",
        "description": "Unusually high transaction velocity within 24 hours, inconsistent with stated account purpose.",
        "regulatory_references": ["31 CFR 1020.320", "FinCEN SAR Activity Review 2024"],
        "signals": ["rapid_movement", "velocity_spike", "velocity_alert", "high_volume_30d"]
    },
    "High-Risk Geography": {
        "code": "BSA-GEO",
        "description": "Transactions involving FATF, OFAC, or FinCEN-designated high-risk jurisdictions.",
        "regulatory_references": ["OFAC SDN List", "FATF High-Risk Jurisdictions", "31 CFR 1010.670"],
        "signals": ["high_risk_jurisdiction", "high_risk_geography", "offshore"]
    },
    "Smurfing": {
        "code": "BSA-SM",
        "description": "Use of multiple accounts or individuals to conduct sub-threshold cash transactions for a single beneficial owner.",
        "regulatory_references": ["31 U.S.C. § 5324", "18 U.S.C. § 1956(a)(1)"],
        "signals": ["many_to_one", "structuring_pattern", "multiple_accounts"]
    },
    "TBML": {
        "code": "BSA-TBML",
        "description": "Trade-Based Money Laundering: over/under invoicing of imports or exports to move value across borders.",
        "regulatory_references": ["FinCEN Advisory FIN-2010-A001", "FATF Trade-Based Money Laundering"],
        "signals": ["invoice_mismatch", "high_risk_jurisdiction", "wire_transfer"]
    },
    "Crypto Layering": {
        "code": "BSA-CRYPTO",
        "description": "Rapid fiat-to-crypto conversion or interaction with mixer services / sanctioned wallets.",
        "regulatory_references": ["FinCEN Guidance FIN-2019-G001", "OFAC Virtual Currency Advisory"],
        "signals": ["darknet_exposure", "unusual_volume", "crypto"]
    }
}

def classify_typology(signals: list[str]) -> tuple[str, dict]:
    """Return (typology_name, typology_entry) best matching the given signal types."""
    scores = {}
    for name, entry in TYPOLOGY_REGISTRY.items():
        overlap = len(set(signals) & set(entry["signals"]))
        if overlap > 0:
            scores[name] = overlap
    if not scores:
        return "Unknown", {
            "code": "BSA-UNK",
            "description": "Unknown or unclassified suspicious activity.",
            "regulatory_references": [],
            "signals": []
        }
    best = max(scores, key=scores.get)
    return best, TYPOLOGY_REGISTRY[best]
