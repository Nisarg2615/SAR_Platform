import os
os.environ["GROQ_API_KEY"] = "dummy"

from agents.shared.schemas import (
    SARCase, SARStatus, RiskTier, NormalizedCase, Transaction, RiskAssessment, RiskSignal,
    SARNarrative, Part1ReportDetails, Part2PrincipalOfficer, Part3ReportingBranch,
    Part7SuspicionDetails, Part8ActionTaken,
    LinkedIndividual, LinkedAccount, ComplianceResult, AuditRecord
)
from datetime import datetime, timedelta
import json
import uuid

def t(days_ago):
    return (datetime.now() - timedelta(days=days_ago)).isoformat()

def make_case(cid, subj, amount, risk_tier, score, typology, status, signals, reasons):
    return SARCase(
        case_id=cid,
        status=status,
        raw_transaction={"mock": "data"},
        normalized=NormalizedCase(
            case_id=cid, transactions=[], subject_name=subj, subject_account_ids=["ACC-123"],
            date_range_start=t(5), date_range_end=t(1), total_amount_usd=amount,
            ingestion_timestamp=t(1), presidio_masked=True
        ),
        risk_assessment=RiskAssessment(
            case_id=cid, risk_tier=RiskTier(risk_tier), risk_score=score,
            matched_typology=typology, typology_confidence=0.95,
            signals=[RiskSignal(signal_type=typ, description=d, confidence=0.9, supporting_transaction_ids=[]) for typ, d in signals],
            shap_values={"amount": 0.15, "velocity": 0.2, "offshore": 0.3},
            neo4j_pattern_found=True, assessment_timestamp=t(1)
        ),
        narrative=SARNarrative(
            case_id=cid,
            part1_report_details=Part1ReportDetails(date_of_sending=t(0)[:10], is_replacement=False),
            part2_principal_officer=Part2PrincipalOfficer(bank_name="TestBank", bsr_code="123", fiu_id="FIU123", bank_category="Public", officer_name="PO", designation="PO", address="123", city_town_district="City", state_country="Country", pin_code="123", telephone="123", email="1@2.com"),
            part3_reporting_branch=Part3ReportingBranch(branch_name="Branch", bsr_code="123", fiu_id="FIU123", address="123", city_town_district="City", state_country="Country", pin_code="123", telephone="123", email="1@2.com"),
            part4_linked_individuals=[LinkedIndividual(name=subj, customer_id="CUST-1")], part5_linked_entities=[],
            part6_linked_accounts=[LinkedAccount(account_number="ACC-1", account_holder_name=subj)],
            part7_suspicion_details=Part7SuspicionDetails(reasons_for_suspicion=reasons, grounds_of_suspicion=f"Narrative regarding {typology} by {subj}."),
            part8_action_taken=Part8ActionTaken(under_investigation=True, agency_details="None"),
            generation_timestamp=t(1)
        ) if status != "pending" else None,
        compliance=ComplianceResult(
            case_id=cid, bsa_compliant=True, all_fields_complete=True, fincen_format_valid=True,
            compliance_issues=[], validated_timestamp=t(1)
        ) if status != "pending" else None,
        audit=AuditRecord(
            case_id=cid, neo4j_audit_node_id="node1", agent_timeline=[], shap_explanations={},
            data_sources_cited=["SWIFT"], audit_timestamp=t(1), immutable_hash=uuid.uuid4().hex
        ) if status != "pending" else None,
        audit_trail=[{"agent":"System", "action":"Created mock case", "confidence":1.0, "timestamp":t(1)}],
        error_log=[]
    ).model_dump(mode="json")

cases = [
    make_case("CASE-AF82BC", "Global Trade Corp", 850000, "critical", 0.98, "TBML (Trade-Based)", "in_review",
              [("invoice_mismatch", "Invoice amounts do not match SWIFT mt700."), ("high_risk_jurisdiction", "Funds routed via shell company in BVI.")],
              ["Over-invoicing of imported goods", "Use of known high-risk correspondent banks"]),
    make_case("CASE-X912KL", "Elena Rostova", 49500, "red", 0.88, "Structuring", "in_review",
              [("velocity_spike", "5 transactions just under 10k in 48h.")],
              ["Multiple deposits just below reporting threshold"]),
    make_case("CASE-M019ZZ", "Crypto Exchange Ltd", 2100000, "red", 0.92, "Crypto Layering", "filed",
              [("unusual_volume", "Inbound fiat immediately converted and transferred out."), ("darknet_exposure", "Wallet hop analysis shows link to sanctioned entities.")],
              ["Rapid fiat-to-crypto conversion", "Interaction with mixer services"]),
    make_case("CASE-Q772BB", "Nexus Imports", 125000, "amber", 0.65, "Smurfing", "in_review",
              [("many_to_one", "Dozens of small cash deposits aggregated into one corporate account.")],
              ["Unexplained aggregation of funds"]),
    make_case("CASE-V441OO", "Local Bakery LLC", 45000, "amber", 0.55, "Cash Intensive", "dismissed",
              [("cash_spike", "30% increase in cash deposits vs historical baseline.")],
              ["Unusual seasonal cash volume"]),
    make_case("CASE-K991WW", "David Chen", 15000, "green", 0.12, "Normal Activity", "pending",
              [("salary_deposit", "Standard monthly payroll logic, but triggered generic rule.")],
              ["Routine salary deposit"]),
    make_case("CASE-B229YY", "Tech Solutions Inc", 300000, "green", 0.25, "B2B Payment", "approved",
              [("large_xfer", "Large B2B payment matches historical invoice payments.")],
              ["Standard corporate invoice settlement"]),
    make_case("CASE-J883UU", "Maria Garcia", 9500, "amber", 0.45, "Structuring", "in_review",
              [("velocity", "Wire transfer immediately followed by cash withdrawal.")],
              ["Immediate withdrawal of wired funds"])
]

with open("mock_db.json", "w") as f:
    json.dump({c["case_id"]: c for c in cases}, f, indent=2)
print("Created mock_db.json with", len(cases), "cases.")
