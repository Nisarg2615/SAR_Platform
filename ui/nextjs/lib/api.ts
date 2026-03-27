const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface SARCase {
  case_id: string;
  status: 'pending' | 'in_review' | 'filed' | 'dismissed' | 'approved';
  raw_transaction?: Record<string, unknown>;
  normalized?: NormalizedCase;
  risk_assessment?: RiskAssessment;
  narrative?: SARNarrative;
  compliance?: ComplianceResult;
  audit?: AuditRecord;
  analyst_approved_by?: string;
  final_filed_timestamp?: string;
  audit_trail: AuditEntry[];
  error_log: ErrorEntry[];
}

export interface NormalizedCase {
  case_id: string;
  transactions: Transaction[];
  subject_name: string;
  subject_account_ids: string[];
  date_range_start: string;
  date_range_end: string;
  total_amount_usd: number;
  ingestion_timestamp: string;
  presidio_masked: boolean;
}

export interface Transaction {
  transaction_id: string;
  account_id: string;
  counterparty_account_id: string;
  amount_usd: number;
  timestamp: string;
  transaction_type: string;
  channel: string;
  geography: string;
}

export interface RiskAssessment {
  case_id: string;
  risk_tier: 'green' | 'amber' | 'red' | 'critical';
  risk_score: number;
  matched_typology: string;
  typology_confidence: number;
  signals: RiskSignal[];
  shap_values: Record<string, number>;
  neo4j_pattern_found: boolean;
  assessment_timestamp: string;
}

export interface RiskSignal {
  signal_type: string;
  description: string;
  confidence: number;
  supporting_transaction_ids: string[];
}

export interface SARNarrative {
  case_id: string;
  narrative_body?: string;
  summary?: string;
  subject_info?: string;
  part1_report_details: { date_of_sending: string; is_replacement: boolean; date_of_original_report?: string };
  part2_principal_officer: Record<string, string>;
  part3_reporting_branch: Record<string, string>;
  part4_linked_individuals: { name: string; customer_id: string }[];
  part5_linked_entities: { name: string; customer_id: string }[];
  part6_linked_accounts: { account_number: string; account_holder_name: string }[];
  part7_suspicion_details: { reasons_for_suspicion: string[]; grounds_of_suspicion: string };
  part8_action_taken: { under_investigation: boolean; agency_details: string };
  generation_timestamp: string;
}

export interface ComplianceResult {
  case_id: string;
  bsa_compliant: boolean;
  all_fields_complete: boolean;
  fincen_format_valid: boolean;
  compliance_issues: string[];
  validated_timestamp: string;
}

export interface AuditRecord {
  case_id: string;
  neo4j_audit_node_id: string;
  agent_timeline: AuditEntry[];
  shap_explanations: Record<string, number>;
  data_sources_cited: string[];
  audit_timestamp: string;
  immutable_hash: string;
}

export interface AuditEntry {
  agent: string;
  action: string;
  confidence: number;
  timestamp: string;
}

export interface ErrorEntry {
  agent: string;
  error: string;
  timestamp: string;
}

export interface CaseSummary {
  case_id: string;
  status: string;
  risk_tier: string;
  subject: string;
  last_updated: string;
}

export interface AccountCaseSummary {
  case_id: string;
  status: string;
  risk_score: number;
  risk_tier: string;
  typology: string;
  filed_at: string | null;
  analyst: string | null;
  agent_decisions: AuditEntry[];
  immutable_hash: string | null;
  total_amount_usd: number;
}

export interface AccountAuditTrail {
  account_id: string;
  total_cases: number;
  total_sar_required: number;
  total_dismissed: number;
  risk_score_avg: number;
  cases: AccountCaseSummary[];
}

export interface SARReportData {
  report_title: string;
  fincen_bsa_id: string | null;
  filing_institution_name: string;
  filing_institution_address: string;
  filing_date: string;
  report_period_start: string;
  report_period_end: string;
  subject_account_id: string;
  subject_name: string;
  subject_address: string;
  subject_id_type: string;
  subject_id_number: string;
  transaction_ids: string[];
  total_amount_usd: number;
  transaction_types: string[];
  geographies_involved: string[];
  date_range_start: string;
  date_range_end: string;
  typology: string;
  typology_code: string;
  typology_description: string;
  suspicion_reason: string;
  regulatory_references: string[];
  narrative_body: string;
  narrative_supporting_facts: string[];
  risk_score: number;
  risk_tier: string;
  risk_signals: Record<string, unknown>[];
  shap_top_features: Record<string, unknown>[];
  compliance_issues: string[];
  compliance_passed: boolean;
  regulatory_flags: string[];
  agent_decisions: Record<string, unknown>[];
  immutable_hash: string;
  audit_created_at: string;
  analyst_name: string | null;
  analyst_approved_at: string | null;
  analyst_notes: string;
  section_filing_reviewed: boolean;
  section_subject_reviewed: boolean;
  section_typology_reviewed: boolean;
  section_narrative_reviewed: boolean;
}


async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error || `HTTP ${res.status}`);
  }
  return res.json();
}

export const sarApi = {
  health: () => api<{ status: string; timestamp: string }>('/health'),
  getCases: () => api<CaseSummary[]>('/cases'),
  getCase: (id: string) => api<SARCase>(`/case/${id}`),
  submitTransaction: (payload: Record<string, unknown>) =>
    api<{ case_id: string; status: string }>('/submit-transaction', { method: 'POST', body: JSON.stringify(payload) }),
  runPipeline: (id: string) => api<{ status: string; risk_tier: string }>(`/case/${id}/run-pipeline`, { method: 'POST' }),
  getPipelineStatus: (id: string) => api<Record<string, unknown>>(`/case/${id}/pipeline-status`),
  generateNarrative: (id: string) => api<{ narrative_body: string; narrative: SARNarrative }>(`/case/${id}/generate-narrative`, { method: 'POST' }),
  approveCase: (id: string, analystName: string) =>
    api<{ status: string; case_status: string }>(`/case/${id}/approve`, { method: 'POST', body: JSON.stringify({ analyst_name: analystName }) }),
  dismissCase: (id: string) => api<{ status: string }>(`/case/${id}/dismiss`, { method: 'POST' }),
  getGraph: (id: string) => api<{ nodes: unknown[]; edges: unknown[] }>(`/case/${id}/graph`),
  simulateScenario: (scenario: 'structuring' | 'layering' | 'smurfing') =>
    api<{ case_id: string; scenario_type: string; raw_transaction: Record<string, unknown> }>(`/demo/simulate/${scenario}`, { method: 'POST' }),
  getAccountAuditTrail: (accountId: string) =>
    api<AccountAuditTrail>(`/account/${accountId}/audit-trail`),
  getReportData: (id: string) => api<SARReportData>(`/case/${id}/report-data`),
  saveReportData: (id: string, data: SARReportData) =>
    api<SARReportData>(`/case/${id}/report-data`, { method: 'PUT', body: JSON.stringify(data) }),
  downloadPdfFromServer: async (id: string, data: SARReportData): Promise<Blob> => {
    const res = await fetch(`${BASE}/case/${id}/generate-pdf`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.blob();
  },
  refreshPipeline: (limit?: number) => api<{ status: string; message: string; total_cases: number }>(`/api/pipeline/refresh${limit ? `?limit=${limit}` : ''}`, { method: 'POST' }),
  trainModel: () => api<{ status: string; message: string }>('/api/model/train', { method: 'POST' }),
};
