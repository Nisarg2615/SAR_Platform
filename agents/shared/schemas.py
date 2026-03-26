"""
Shared Pydantic v2 schemas.
Data contracts between all 6 agents.
Do not modify without team agreement.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, computed_field


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

    @computed_field  # type: ignore[misc]
    @property
    def narrative_body(self) -> str:
        """Convenience accessor — maps to grounds_of_suspicion."""
        return self.part7_suspicion_details.grounds_of_suspicion

    @computed_field  # type: ignore[misc]
    @property
    def summary(self) -> str:
        """High-level summary from suspicion reasons."""
        reasons = self.part7_suspicion_details.reasons_for_suspicion
        return "; ".join(reasons) if reasons else "Suspicious transaction activity detected."

    @computed_field  # type: ignore[misc]
    @property
    def subject_info(self) -> str:
        """Subject name from linked individuals."""
        if self.part4_linked_individuals:
            return self.part4_linked_individuals[0].name
        return "Unknown"

    @computed_field  # type: ignore[misc]
    @property
    def suspicious_activity(self) -> str:
        """Alias for grounds_of_suspicion."""
        return self.part7_suspicion_details.grounds_of_suspicion

    @computed_field  # type: ignore[misc]
    @property
    def law_enforcement_note(self) -> str:
        """Agency details from Part 8."""
        return self.part8_action_taken.agency_details or "No law enforcement referral at this time."


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


class SARReportData(BaseModel):
    """Full regulatory SAR report — assembled from SARCase, editable by analyst."""
    # Filing Info
    report_title: str = "Suspicious Activity Report"
    fincen_bsa_id: Optional[str] = None
    filing_institution_name: str = "State Bank of India (Demo)"
    filing_institution_address: str = "New Delhi, India"
    filing_date: str = ""
    report_period_start: str = ""
    report_period_end: str = ""

    # Subject Info
    subject_account_id: str = ""
    subject_name: str = "[MASKED — PRESIDIO]"
    subject_address: str = "[MASKED]"
    subject_id_type: str = "Account Reference"
    subject_id_number: str = ""

    # Transaction Summary
    transaction_ids: list[str] = Field(default_factory=list)
    total_amount_usd: float = 0.0
    transaction_types: list[str] = Field(default_factory=list)
    geographies_involved: list[str] = Field(default_factory=list)
    date_range_start: str = ""
    date_range_end: str = ""

    # Fraud Classification
    typology: str = "Unknown"
    typology_code: str = "BSA-UNK"
    typology_description: str = ""
    suspicion_reason: str = ""
    regulatory_references: list[str] = Field(default_factory=list)

    # Narrative
    narrative_body: str = ""
    narrative_supporting_facts: list[str] = Field(default_factory=list)

    # Risk Assessment
    risk_score: float = 0.0
    risk_tier: str = "green"
    risk_signals: list[dict] = Field(default_factory=list)
    shap_top_features: list[dict] = Field(default_factory=list)

    # Compliance
    compliance_issues: list[str] = Field(default_factory=list)
    compliance_passed: bool = True
    regulatory_flags: list[str] = Field(default_factory=list)

    # Audit
    agent_decisions: list[dict] = Field(default_factory=list)
    immutable_hash: str = ""
    audit_created_at: str = ""

    # Analyst Sign-off
    analyst_name: Optional[str] = None
    analyst_approved_at: Optional[str] = None
    analyst_notes: str = ""

    # Review completion flags
    section_filing_reviewed: bool = False
    section_subject_reviewed: bool = False
    section_typology_reviewed: bool = False
    section_narrative_reviewed: bool = False

    @classmethod
    def from_sar_case(cls, case: "SARCase") -> "SARReportData":
        """Assemble SARReportData from a fully or partially processed SARCase."""
        from datetime import datetime
        r = cls()
        r.filing_date = datetime.now().strftime("%Y-%m-%d")
        if case.normalized:
            r.subject_account_id = (case.normalized.subject_account_ids or [""])[0]
            r.subject_name = case.normalized.subject_name
            r.total_amount_usd = case.normalized.total_amount_usd
            r.report_period_start = str(case.normalized.date_range_start)[:10]
            r.report_period_end = str(case.normalized.date_range_end)[:10]
            r.transaction_ids = [t.transaction_id for t in case.normalized.transactions]
            r.transaction_types = list(set(t.transaction_type for t in case.normalized.transactions))
            r.geographies_involved = list(set(t.geography for t in case.normalized.transactions))
        if case.risk_assessment:
            r.risk_score = case.risk_assessment.risk_score
            r.risk_tier = str(case.risk_assessment.risk_tier)
            r.risk_signals = [s.model_dump() for s in case.risk_assessment.signals]
            r.typology = case.risk_assessment.matched_typology
            r.typology_code = "BSA-ST"  # will be refined by typology_definitions.py
            top_shap = sorted(case.risk_assessment.shap_values.items(), key=lambda x: abs(x[1]), reverse=True)[:5]
            r.shap_top_features = [{"feature": k, "value": float(v)} for k, v in top_shap]
        if case.narrative:
            r.narrative_body = case.narrative.part7_suspicion_details.grounds_of_suspicion
            r.narrative_supporting_facts = case.narrative.part7_suspicion_details.reasons_for_suspicion
            r.suspicion_reason = "; ".join(case.narrative.part7_suspicion_details.reasons_for_suspicion)
        if case.compliance:
            r.compliance_issues = case.compliance.compliance_issues
            r.compliance_passed = case.compliance.bsa_compliant
        if case.audit:
            r.immutable_hash = case.audit.immutable_hash
            r.audit_created_at = str(case.audit.audit_timestamp)
        r.agent_decisions = case.audit_trail
        r.analyst_name = case.analyst_approved_by
        r.analyst_approved_at = str(case.final_filed_timestamp) if case.final_filed_timestamp else None
        return r


class ProviderName(str, Enum):
    GROQ       = "groq"
    GEMINI     = "gemini"
    MISTRAL    = "mistral"
    CEREBRAS   = "cerebras"
    FALLBACK   = "template_fallback"

class LLMRoutingDirective(BaseModel):
    agent_name: str
    provider: ProviderName
    model: str
    max_tokens: int = 900
    temperature: float = 0.1
    reason: str = ""
    fallback_chain: list[ProviderName] = []

class OrchestratorDecision(BaseModel):
    decided_at: str
    directives: dict[str, LLMRoutingDirective]
    total_budget_tokens: int = 10000
    tokens_used: int = 0
    provider_health: dict[str, bool] = {}


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
    orchestrator_decision: Optional[OrchestratorDecision] = None
    analyst_approved_by: Optional[str] = None
    final_filed_timestamp: Optional[datetime] = None
    sar_report: Optional[SARReportData] = None
    audit_trail: list[dict] = Field(default_factory=list)  # every agent appends here
    error_log: list[dict] = Field(default_factory=list)    # errors append here, never crash
