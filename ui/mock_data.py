"""Mock data for the SAR UI prototype."""

from agents.shared.schemas import (
    SARCase, SARStatus, NormalizedCase, RiskAssessment, RiskTier, SARNarrative, 
    ComplianceResult, AuditRecord, Transaction, Part1ReportDetails, Part2PrincipalOfficer,
    Part3ReportingBranch, LinkedIndividual, LinkedEntity, LinkedAccount, Part7SuspicionDetails,
    Part8ActionTaken
)
from datetime import datetime
import uuid

tx_id = f"txn-{uuid.uuid4().hex[:8]}"

mock_case_structuring = SARCase(
    case_id="CASE-MOCK-101",
    status=SARStatus.IN_REVIEW,
    raw_transaction={"amount_usd": 9800.0, "transaction_type": "wire", "geography": "offshore", "bank_name": "Barclays India", "bsr_code": "0001234", "branch_name": "Pune Tech Hub"},
    normalized=NormalizedCase(
        case_id="CASE-MOCK-101",
        transactions=[Transaction(
            transaction_id=tx_id,
            account_id="ACC99",
            counterparty_account_id="CP88",
            amount_usd=9800.0,
            timestamp=datetime.now(),
            transaction_type="wire",
            channel="branch",
            geography="domestic"
        )],
        subject_name="[REDACTED]",
        subject_account_ids=["ACC99"],
        date_range_start=datetime.now(),
        date_range_end=datetime.now(),
        total_amount_usd=9800.0,
        ingestion_timestamp=datetime.now(),
        presidio_masked=True
    ),
    risk_assessment=RiskAssessment(
        case_id="CASE-MOCK-101",
        risk_tier=RiskTier.RED,
        risk_score=0.92,
        matched_typology="Structuring",
        typology_confidence=0.88,
        signals=[],
        shap_values={"amount_usd": 0.5, "frequency": 0.3, "geography": 0.1},
        neo4j_pattern_found=True,
        assessment_timestamp=datetime.now()
    ),
    narrative=SARNarrative(
        case_id="CASE-MOCK-101",
        part1_report_details=Part1ReportDetails(date_of_sending=datetime.now().strftime("%Y-%m-%d"), is_replacement=False),
        part2_principal_officer=Part2PrincipalOfficer(
            bank_name="Barclays India", bsr_code="4001234", fiu_id="FIU001", bank_category="A", officer_name="Hackathon PO", designation="PO",
            address="123 Bank St", city_town_district="Pune", state_country="Maharashtra", pin_code="411001", telephone="020-123456", email="po@barclays.com"
        ),
        part3_reporting_branch=Part3ReportingBranch(
            branch_name="Pune Tech Hub", bsr_code="4001234", fiu_id="FIU001", address="123 Bank St", city_town_district="Pune", state_country="Maharashtra", pin_code="411001", telephone="020-123456", email="branch@barclays.com"
        ),
        part4_linked_individuals=[LinkedIndividual(name="[REDACTED]", customer_id="CUST001")],
        part5_linked_entities=[],
        part6_linked_accounts=[LinkedAccount(account_number="ACC99", account_holder_name="[REDACTED]")],
        part7_suspicion_details=Part7SuspicionDetails(
            reasons_for_suspicion=["Value of transaction"],
            grounds_of_suspicion="The subject executed a pattern of transactions indicative of structuring. Specifically, an amount of $9800 was wired, avoiding the $10,000 reporting requirement."
        ),
        part8_action_taken=Part8ActionTaken(under_investigation=False, agency_details=""),
        generation_timestamp=datetime.now()
    ),
    compliance=ComplianceResult(
        case_id="CASE-MOCK-101",
        bsa_compliant=False,
        all_fields_complete=True,
        fincen_format_valid=True,
        compliance_issues=["Structuring Threshold Flag: Transaction amount $9800 is suspicious."],
        validated_timestamp=datetime.now()
    ),
    audit_trail=[
        {"agent": "System API", "action": "Transaction submitted", "confidence": 1.0, "timestamp": datetime.now().isoformat()},
        {"agent": "Agent 1", "action": "Masked PII", "confidence": 1.0, "timestamp": datetime.now().isoformat()},
        {"agent": "Agent 2", "action": "Scored RED tier", "confidence": 0.9, "timestamp": datetime.now().isoformat()},
        {"agent": "Agent 3", "action": "Narrative generated", "confidence": 0.95, "timestamp": datetime.now().isoformat()},
        {"agent": "Agent 4", "action": "Compliance checked", "confidence": 1.0, "timestamp": datetime.now().isoformat()},
        {"agent": "Agent 5", "action": "Audit written", "confidence": 1.0, "timestamp": datetime.now().isoformat()},
    ]
)
