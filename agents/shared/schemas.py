"""
Shared Pydantic v2 schemas.
Data contracts between all 6 agents.
Do not modify without team agreement.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    GREEN = "green"
    AMBER = "amber"
    RED = "red"
    CRITICAL = "critical"


class SARStatus(str, Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    FILED = "filed"
    DISMISSED = "dismissed"


class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    counterparty_account_id: str
    amount_usd: float = Field(ge=0)
    timestamp: datetime
    transaction_type: str
    channel: str
    geography: str


class NormalizedCase(BaseModel):
    """Output of Agent 1 — Data Ingestion"""
    case_id: str
    transactions: list[Transaction]
    subject_name: str
    subject_account_ids: list[str]
    date_range_start: datetime
    date_range_end: datetime
    total_amount_usd: float
    ingestion_timestamp: datetime
    presidio_masked: bool = Field(default=True)


class RiskSignal(BaseModel):
    signal_type: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_transaction_ids: list[str]


class RiskAssessment(BaseModel):
    """Output of Agent 2 — Risk Assessment"""
    case_id: str
    risk_tier: RiskTier
    risk_score: float = Field(ge=0.0, le=1.0)
    matched_typology: str
    typology_confidence: float = Field(ge=0.0, le=1.0)
    signals: list[RiskSignal]
    shap_values: dict = Field(default_factory=dict)
    neo4j_pattern_found: bool
    assessment_timestamp: datetime


class Part1ReportDetails(BaseModel):
    date_of_sending: str
    is_replacement: bool
    date_of_original_report: Optional[str] = None

class Part2PrincipalOfficer(BaseModel):
    bank_name: str
    bsr_code: str
    fiu_id: str
    bank_category: str
    officer_name: str
    designation: str
    address: str
    city_town_district: str
    state_country: str
    pin_code: str
    telephone: str
    email: str

class Part3ReportingBranch(BaseModel):
    branch_name: str
    bsr_code: str
    fiu_id: str
    address: str
    city_town_district: str
    state_country: str
    pin_code: str
    telephone: str
    email: str

class LinkedIndividual(BaseModel):
    name: str
    customer_id: str

class LinkedEntity(BaseModel):
    name: str
    customer_id: str

class LinkedAccount(BaseModel):
    account_number: str
    account_holder_name: str

class Part7SuspicionDetails(BaseModel):
    reasons_for_suspicion: list[str]
    grounds_of_suspicion: str

class Part8ActionTaken(BaseModel):
    under_investigation: bool
    agency_details: str

class SARNarrative(BaseModel):
    """Output of Agent 3 — Narrative Generation (FIU-IND STR Format)"""
    case_id: str
    part1_report_details: Part1ReportDetails
    part2_principal_officer: Part2PrincipalOfficer
    part3_reporting_branch: Part3ReportingBranch
    part4_linked_individuals: list[LinkedIndividual]
    part5_linked_entities: list[LinkedEntity]
    part6_linked_accounts: list[LinkedAccount]
    part7_suspicion_details: Part7SuspicionDetails
    part8_action_taken: Part8ActionTaken
    generation_timestamp: datetime


class ComplianceResult(BaseModel):
    """Output of Agent 4 — Compliance Validation"""
    case_id: str
    bsa_compliant: bool
    all_fields_complete: bool
    fincen_format_valid: bool
    compliance_issues: list[str]
    validated_timestamp: datetime


class AuditRecord(BaseModel):
    """Output of Agent 5 — Audit Trail"""
    case_id: str
    neo4j_audit_node_id: str
    agent_timeline: list[dict]
    shap_explanations: dict
    data_sources_cited: list[str]
    audit_timestamp: datetime
    immutable_hash: str


class SARCase(BaseModel):
    """Master state object — flows through all 6 agents"""
    case_id: str
    status: SARStatus = SARStatus.PENDING
    raw_transaction: Optional[dict] = None          # set before pipeline starts
    normalized: Optional[NormalizedCase] = None
    risk_assessment: Optional[RiskAssessment] = None
    narrative: Optional[SARNarrative] = None
    compliance: Optional[ComplianceResult] = None
    audit: Optional[AuditRecord] = None
    analyst_approved_by: Optional[str] = None
    final_filed_timestamp: Optional[datetime] = None
    audit_trail: list[dict] = Field(default_factory=list)  # every agent appends here
    error_log: list[dict] = Field(default_factory=list)    # errors append here, never crash
