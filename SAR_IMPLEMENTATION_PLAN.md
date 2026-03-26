# SAR Platform — Enhanced Modular Implementation Plan
# For AI Agent Execution: One Task at a Time
# Based on MASTER_CONTEXT.md + Full Codebase Review (Last updated: March 26 2026)
# Total Features: 5 major features → 30 numbered subtasks
#
# CODEBASE FACTS (read before starting any task):
#   Backend:  FastAPI at /main.py — DB is in-memory dict `DB: Dict[str, SARCase]`
#   Frontend: Next.js 14/16 App Router at /ui/nextjs/
#     Pages:  app/page.tsx (dashboard), app/app/cases/ (list), app/app/cases/[id]/ (detail)
#             app/app/demo/ (demo center)
#     API:    /ui/nextjs/lib/api.ts — sarApi client, all FastAPI calls go through here
#     Styles: /ui/nextjs/app/globals.css — CSS utility classes (.surface, .card, .badge-*)
#     AppShell: /ui/nextjs/components/AppShell.tsx — sidebar + layout wrapper
#   Agents:  /agents/pipeline.py — LangGraph StateGraph
#             /agents/agent3_narrative/minimax_client.py — LLM client (currently Groq only)
#   Mock DB: /mock_db.json — loaded at startup into in-memory DB (main.py line 40–51)
#   Schemas: /agents/shared/schemas.py — ALL Pydantic models, coordinate before editing
#
# IMPORTANT — Do NOT mention Streamlit (ui/app.py) anywhere in implementation.
#              The active frontend is ui/nextjs ONLY.

---

## HOW TO USE THIS PLAN

- Execute ONE subtask at a time. Do not move to the next until current subtask passes its DONE CHECK.
- Each subtask lists: what files to touch, exact instructions, and a DONE CHECK.
- After every subtask, commit: `feat(task-N-X): short description`
- Always read `agents/shared/schemas.py` before touching any agent file.
- When modifying `lib/api.ts`, keep all functions in the `sarApi` object.
- When modifying `main.py`, maintain the `DB: Dict[str, SARCase]` pattern.

---

## FEATURE 1 — Transaction Dataset (150–200 Transactions with Pipeline Processing)

**Goal:** Replace hardcoded/sparse mock_db.json data with a rich synthetic dataset of 150–200
realistic bank transactions. Each is processed through the full 6-agent pipeline one at a time.
Past transactions are checked to detect patterns (structuring, velocity). SAR Required / Not
Required determined per transaction and persisted to DB + JSON.

**Backend files:** `data/`, `scripts/`, `agents/agent2_risk/node.py`, `main.py`
**Frontend files:** None in Feature 1 — this is backend only.

---

### TASK 1-A — Create the Transaction Dataset File

**File to create:** `data/transactions_dataset.py`
**File to create:** `data/__init__.py` (empty)

**Instructions:**
1. Create directory `data/` and both files.
2. In `transactions_dataset.py`, define a Python list `TRANSACTIONS` with exactly 160 dicts.
3. Each dict must have exactly these keys:
   - `transaction_id` (str, unique: "TXN-0001" to "TXN-0160")
   - `account_id` (str: one of 20 rotating IDs "ACC-001" to "ACC-020")
   - `counterparty_account_id` (str)
   - `amount_usd` (float)
   - `transaction_type` (str: "wire_transfer" | "cash_deposit" | "cash_withdrawal" | "check" | "ach")
   - `geography` (str: country code — "US", "MX", "NG", "AE", "RU", "IR", "PA", "KY")
   - `timestamp` (str: ISO format, spread across 90 days from "2025-10-01" to "2025-12-31")
   - `channel` (str: "branch" | "online" | "atm" | "mobile")
   - `notes` (str: short description)
4. Distribute typologies/patterns intentionally:
   - **40 transactions** → Structuring (ACC-001 to ACC-005, cash deposits $9,100–$9,900, repeated by same account)
   - **30 transactions** → Layering (wire_transfers through AE, PA, KY, then returning to origin account)
   - **25 transactions** → Rapid Movement (5+ transactions in 24h by same account, high velocity)
   - **20 transactions** → High-Risk Geography (wires to/from NG, RU, IR geography field)
   - **45 transactions** → Clean / Legitimate (normal payroll, invoices, domestic transfers, score GREEN)
5. Add a top-level docstring that summarizes counts per typology.
6. Pure Python only — no external imports.

**DONE CHECK:**
```bash
python -c "from data.transactions_dataset import TRANSACTIONS; print(len(TRANSACTIONS))"
# Must print 160
```

---

### TASK 1-B — Add Past-Transaction Context Loader

**File to create:** `data/transaction_history.py`

**Instructions:**
1. Define class `TransactionHistoryStore`:
   - `__init__(self, transactions: list[dict])`: indexes all transactions by `account_id` in memory.
   - `get_history(self, account_id: str, before_timestamp: str) -> list[dict]`: all past txns before given ISO timestamp, sorted oldest-first.
   - `get_velocity(self, account_id: str, before_timestamp: str, hours: int = 24) -> int`: count of txns in last N hours before `before_timestamp`.
   - `get_total_amount_last_n_days(self, account_id: str, before_timestamp: str, days: int = 30) -> float`: sum of amounts in last N days.
2. At module bottom, create a singleton:
   ```python
   from data.transactions_dataset import TRANSACTIONS
   history_store = TransactionHistoryStore(TRANSACTIONS)
   ```

**DONE CHECK:**
```python
from data.transaction_history import history_store
result = history_store.get_history("ACC-001", "2025-11-01T00:00:00")
print(len(result))  # must print a number without error
```

---

### TASK 1-C — Inject History Context into Agent 2 (Risk Assessment)

**File to modify:** `agents/agent2_risk/node.py`

**Instructions:**
1. At top of file, add:
   ```python
   from data.transaction_history import history_store
   ```
2. Inside the agent function body, after reading `state.normalized`, add:
   ```python
   if state.normalized and state.normalized.transactions:
       acct = state.normalized.transactions[0].account_id
       ts   = str(state.normalized.transactions[0].timestamp)
       velocity_24h  = history_store.get_velocity(acct, ts, hours=24)
       total_30d     = history_store.get_total_amount_last_n_days(acct, ts, days=30)
       past_txns     = history_store.get_history(acct, ts)
       # Structuring signal: any past txn within $500 below $10,000
       structuring_past = any(
           9000 <= float(t.get("amount_usd", 0)) < 10000 for t in past_txns
       )
       if velocity_24h >= 5:
           # append RiskSignal for rapid_movement
       if total_30d > 50_000:
           # append RiskSignal for high_volume_30d
       if structuring_past:
           # append RiskSignal for structuring_pattern
   ```
3. Append each new `RiskSignal` object to `state.risk_assessment.signals`.
4. Do NOT change function signature. Do NOT remove existing risk logic.

**DONE CHECK:**
```bash
pytest tests/unit/test_agent2.py -v
# All tests pass. Also submit a structuring transaction manually and confirm new signals appear in the API response.
```

---

### TASK 1-D — Batch Pipeline Runner Script

**File to create:** `scripts/run_batch_pipeline.py`
**File to create:** `scripts/__init__.py` (empty)

**Instructions:**
1. Import `TRANSACTIONS` from `data.transactions_dataset`.
2. Import and call `submit_transaction` and `run_pipeline` from `main.py` logic directly (or via HTTP to localhost:8000).
3. Write `async def main()` that:
   - Loops through every transaction ONE AT A TIME (no concurrency).
   - For each: POSTs to `http://localhost:8000/submit-transaction` → gets case_id.
   - POSTs to `http://localhost:8000/case/{case_id}/run-pipeline`.
   - GETs `/case/{case_id}` to retrieve the result.
   - Prints: `[TXN-XXXX] case=CASE-XXXXXX risk=0.87 tier=RED sar_required=True`
4. Collect all SARCase dicts. Write to `data/batch_results.json`.
5. Print a summary: `=== BATCH COMPLETE: 160 processed, 72 SAR required, 88 clean ===`
6. Each iteration wrapped in try/except — single failure must not stop the batch.
7. `if __name__ == "__main__": asyncio.run(main())`

**DONE CHECK:**
```bash
python scripts/run_batch_pipeline.py
# Runs to completion, prints summary, produces data/batch_results.json with 160 entries
```

---

### TASK 1-E — Load Batch Results into FastAPI DB on Startup

**File to modify:** `main.py`

**Context:** Currently `main.py` already loads `mock_db.json` at startup (lines 40–51).

**Instructions:**
1. After the existing `mock_db.json` load block, add a secondary load from `data/batch_results.json` (if it exists):
   ```python
   if os.path.exists("data/batch_results.json"):
       try:
           with open("data/batch_results.json", "r") as f:
               batch_data = json.load(f)
               for k, v in batch_data.items():
                   if k not in DB:  # don't overwrite mock cases
                       DB[k] = SARCase(**v)
           print(f"Loaded {len(batch_data)} batch cases from data/batch_results.json")
       except Exception as e:
           print(f"Failed to load batch_results.json: {e}")
   ```
2. Keep the `mock_db.json` load above it unchanged.

**DONE CHECK:**
```bash
# Run scripts/run_batch_pipeline.py first to produce batch_results.json
# Then restart uvicorn and curl:
curl http://localhost:8000/cases | python -m json.tool | grep case_id | wc -l
# Must print 168+ (8 mock + 160 batch)
```

---

## FEATURE 2 — Audit Trail for SAR-Required Accounts

**Goal:** Account-level audit trail that persists across all SAR cases for a given account.
Queried by account_id. Shows complete multi-case history with all 6 agent decisions,
timestamps, immutable hash, and analyst actions. Shown in the Next.js UI.

**Backend files:** `graph/neo4j/`, `agents/agent5_audit/`, `main.py`
**Frontend files:** `ui/nextjs/app/app/cases/[id]/page.tsx` (add Audit tab enhancement)
                   `ui/nextjs/lib/api.ts` (add new endpoint call)

---

### TASK 2-A — Extend Neo4j Schema for Account-Level Audit

**File to modify:** `graph/neo4j/init_schema.py`

**Instructions:**
1. Add constraint:
   ```cypher
   CREATE CONSTRAINT account_id_unique IF NOT EXISTS
   FOR (a:Account) REQUIRE a.account_id IS UNIQUE
   ```
2. Add to `GraphWriter` a method `upsert_account_audit_summary(account_id: str, case: SARCase)` that creates/updates an `AccountAuditSummary` node:
   ```
   AccountAuditSummary {
     account_id: str,
     total_sar_cases: int,
     total_dismissed: int,
     first_flagged_at: datetime,
     last_flagged_at: datetime,
     risk_score_avg: float
   }
   ```
3. If Neo4j is not running (connection refused), the method must silently return — no crash.

**DONE CHECK:** `python graph/neo4j/init_schema.py` runs without error. In Neo4j browser (if running): `CALL db.constraints()` shows new constraint.

---

### TASK 2-B — Extend Agent 5 to Write Full Account Audit Trail

**File to modify:** `agents/agent5_audit/node.py`

**Instructions:**
1. After existing Neo4j writes, add calls to `upsert_account_audit_summary`.
2. Ensure `AuditRecord` (in schemas.py) is extended at the schema level (coordinate with team) to include:
   - `account_id: str = ""`
   - `agent_decisions: list[dict] = Field(default_factory=list)` (copy of `state.audit_trail`)
3. The SHA256 hash must cover: `json.dumps({"case_id": ..., "audit_trail": ..., "risk_score": ...}, sort_keys=True)`.

**DONE CHECK:** Submit a RED transaction. The `audit` field in `GET /case/{id}` contains `agent_decisions` list with all 6 entries, and `immutable_hash` is a 64-char hex string.

---

### TASK 2-C — New FastAPI Endpoint: Account Audit Trail

**File to modify:** `main.py`

**Instructions:**
1. Add endpoint `GET /account/{account_id}/audit-trail`:
   - Search `DB.values()` for all cases where `normalized.subject_account_ids` contains `account_id`.
   - Return:
     ```json
     {
       "account_id": "ACC-001",
       "total_sar_cases": 3,
       "total_dismissed": 1,
       "cases": [
         {
           "case_id": "...",
           "status": "FILED",
           "risk_score": 0.91,
           "risk_tier": "RED",
           "filed_at": "...",
           "analyst": "...",
           "agent_decisions": [...],
           "immutable_hash": "sha256:..."
         }
       ]
     }
     ```
   - If no cases found, return 404.
2. No Neo4j dependency needed — query from `DB` dict in-memory first.

**DONE CHECK:**
```bash
# After batch run, a RED account like ACC-001 should have entries:
curl http://localhost:8000/account/ACC-001/audit-trail
```

---

### TASK 2-D — Frontend: Account Audit Trail in Next.js

**File to modify:** `ui/nextjs/lib/api.ts`
**File to modify:** `ui/nextjs/app/app/cases/[id]/page.tsx`

**Sub-task 2-D-i — Add API call in api.ts:**
```typescript
getAccountAuditTrail: async (accountId: string) => {
  const res = await fetch(`${API}/account/${accountId}/audit-trail`);
  if (!res.ok) throw new Error('Not found');
  return res.json();
}
```

**Sub-task 2-D-ii — Enhance the Audit Trail tab in case detail page:**
- The Audit Trail tab already shows `state.audit_trail` entries (lines ~425–469 in `app/app/cases/[id]/page.tsx`).
- BELOW the existing timeline, add an "Account History" section:
  - Show a button: "View All Cases for This Account".
  - On click, call `sarApi.getAccountAuditTrail(account_id)` using `data.normalized?.subject_account_ids[0]`.
  - Display each historical case as a collapsible row (use a `<details>` element) showing: Case ID, Risk Tier badge, Status badge, filed date.
  - Inside each row, show a numbered list of agent decisions with confidence scores.
  - At the bottom: monospace SHA256 hash.
- Use existing inline `style={{}}` patterns — do NOT introduce new CSS classes.

**DONE CHECK:** Open `/app/cases/[id]` for a RED case. Go to Audit Trail tab. Click "View All Cases for This Account". Multiple case entries appear if the account was in the batch.

---

## FEATURE 3 — Professional SAR Report Generation (Editable UI + Rich PDF)

**Goal:** The current SAR Report tab has a read-only accordion for the 8-part STR. This must
be replaced with: (1) a fully editable form in the Next.js UI where analysts can edit every
field, and (2) a Python-generated PDF served by FastAPI that includes ALL regulatory fields,
complete audit trail, fraud typology classification table, and professional formatting on 7
pages via ReportLab.

**Backend files:** `agents/shared/schemas.py`, `reports/pdf_generator.py`,
                   `reports/typology_definitions.py`, `main.py`
**Frontend files:** `ui/nextjs/app/app/cases/[id]/page.tsx` (SAR Report tab rewrite)
                    `ui/nextjs/lib/api.ts` (new API calls)

---

### TASK 3-A — Define the Full SAR Report Data Model

**File to modify:** `agents/shared/schemas.py`
**⚠️ SHARED FILE — coordinate with all team members before editing**

**Instructions:**
Add `SARReportData` Pydantic model **after** the existing `SARNarrative` model:

```python
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
```

Also add to `SARCase`:
```python
sar_report: Optional[SARReportData] = None
```

**DONE CHECK:**
```bash
python -c "from agents.shared.schemas import SARReportData; print('OK')"
```

---

### TASK 3-B — Typology Definitions Registry

**File to create:** `reports/__init__.py` (empty)
**File to create:** `reports/typology_definitions.py`

**Instructions:**
1. Create `reports/typology_definitions.py` with `TYPOLOGY_REGISTRY` dict:
```python
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
        "signals": ["rapid_movement", "velocity_spike", "velocity_alert"]
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
```
2. Add helper:
```python
def classify_typology(signals: list[str]) -> tuple[str, dict]:
    """Return (typology_name, typology_entry) best matching the given signal types."""
    scores = {}
    for name, entry in TYPOLOGY_REGISTRY.items():
        overlap = len(set(signals) & set(entry["signals"]))
        if overlap > 0:
            scores[name] = overlap
    if not scores:
        return "Unknown", {}
    best = max(scores, key=scores.get)
    return best, TYPOLOGY_REGISTRY[best]
```

**DONE CHECK:**
```bash
python -c "from reports.typology_definitions import classify_typology; print(classify_typology(['structuring_pattern', 'cash_deposit']))"
# Must print ('Structuring', {...})
```

---

### TASK 3-C — ReportLab PDF Generator (Backend)

**File to create:** `reports/pdf_generator.py`

**Pre-requisite:** Add `reportlab>=4.0` to `requirements.txt` and run `pip install reportlab`.

**Instructions:**
Create `reports/pdf_generator.py` with function:
```python
def generate_sar_pdf(report: SARReportData, case_id: str) -> bytes:
```

The PDF must have 7 clearly titled sections (each starting a new page where appropriate):

**PAGE 1 — Cover + Filing Info**
- Title: "SUSPICIOUS ACTIVITY REPORT" (large, bold, navy #1a2f5e)
- Sub: Filing Institution Name, Address
- Filing Date, Report Period, BSA Reference (case_id)
- Grey watermark text: "CONFIDENTIAL — FOR REGULATORY USE ONLY"
- Section: Subject Information table (Account ID | Name | Address | ID Type | ID Number)
  - Note: "[Personal data masked per Presidio PII policy]"

**PAGE 2 — Transaction Summary + Typology Classification**
- Table: Transaction ID | Type | Amount (USD) | Geography | Date (one row per txn)
- Bold "TOTAL" row at bottom with summed amount
- Date range shown above table
- Below table: Fraud Typology section:
  - Typology name (bold, large, e.g. "STRUCTURING")
  - Code, description paragraph
  - Regulatory references as bullet list
  - Suspicion Reason paragraph

**PAGE 3 — Risk Assessment**
- Risk Score displayed large (e.g. 0.91), red if > 0.7, amber if > 0.4, green otherwise
- Risk Tier badge text
- Risk Signals table: Signal Type | Description | Confidence
- SHAP Feature Importance: top 5 as text bar chart (e.g. `amount_usd  ████████░░  0.32`)

**PAGE 4 — SAR Narrative**
- Narrative body (full text, wrapped)
- Supporting Facts as numbered list

**PAGE 5 — Compliance Review**
- Compliance Passed: bold YES (green) or NO (red)
- Compliance Issues: bulleted list (or "None — All checks passed")
- Regulatory Flags: bulleted list

**PAGE 6 — Complete Audit Trail**
- Section header: "IMMUTABLE AGENT DECISION LOG"
- Table: Agent | Action | Confidence | Timestamp (alternating row background)
- SHA256 hash in monospace
- Footer: "This audit trail is cryptographically verified and append-only."

**PAGE 7 — Analyst Sign-off**
- Analyst Name + Approval Timestamp
- Analyst Notes (or "No additional notes provided")
- Signature line placeholder
- "Filed under FinCEN BSA regulations. Retention period: 5 years minimum."
- Case ID + generation timestamp footer

**Implementation notes:**
- Use `reportlab.platypus.SimpleDocTemplate` + Platypus flowables (Paragraph, Table, Spacer).
- Color palette: Navy header `#1a2f5e`, red flag `#c0392b`, grey body `#4a4a4a`, white bg.
- Return `bytes` — do NOT write to disk.

**DONE CHECK:**
```bash
python -c "
from agents.shared.schemas import SARReportData
from reports.pdf_generator import generate_sar_pdf
pdf_bytes = generate_sar_pdf(SARReportData(), 'CASE-TEST')
print(f'PDF size: {len(pdf_bytes)} bytes — OK' if len(pdf_bytes) > 1000 else 'FAIL')
"
```

---

### TASK 3-D — New FastAPI Endpoints for Report Data and PDF

**File to modify:** `main.py`

**Instructions:**
Add 3 new endpoints (add them near the existing `/generate-narrative` endpoint):

```python
GET  /case/{case_id}/report-data    → returns SARReportData (assembled from SARCase)
PUT  /case/{case_id}/report-data    → accepts SARReportData body, saves to case.sar_report
POST /case/{case_id}/generate-pdf   → accepts SARReportData body, calls pdf_generator, returns PDF bytes
```

For GET:
- Call `SARReportData.from_sar_case(DB[case_id])`
- Also run typology auto-classification: `classify_typology([s.signal_type for s in case.risk_assessment.signals])`
- Return the assembled model as JSON

For PUT:
- Accept `SARReportData` as body model
- Store: `DB[case_id].sar_report = body`
- Return the stored model

For POST (`/generate-pdf`):
- Accept `SARReportData` as body model
- Call `generate_sar_pdf(body, case_id)` → `pdf_bytes`
- Return: `Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=SAR_{case_id}.pdf"})`

**DONE CHECK:**
```bash
curl http://localhost:8000/case/{any_red_case_id}/report-data
# Returns full JSON with typology populated, narrative_body non-empty (if pipeline ran), etc.
```

---

### TASK 3-E — Next.js: Editable SAR Report UI

**File to modify:** `ui/nextjs/app/app/cases/[id]/page.tsx`
**File to modify:** `ui/nextjs/lib/api.ts`

**Context:** The current SAR Report tab (lines ~289–388 in `cases/[id]/page.tsx`) shows a
read-only accordion with `<Sec>` components. This must be replaced with an editable form.

**Sub-task 3-E-i — Add API functions in `lib/api.ts`:**
```typescript
getReportData: async (caseId: string): Promise<SARReportData> => {
  const res = await fetch(`${API}/case/${caseId}/report-data`);
  return res.json();
},
saveReportData: async (caseId: string, data: SARReportData): Promise<SARReportData> => {
  const res = await fetch(`${API}/case/${caseId}/report-data`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
},
downloadPdfFromServer: async (caseId: string, data: SARReportData): Promise<Blob> => {
  const res = await fetch(`${API}/case/${caseId}/generate-pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.blob();
},
```
Also add `SARReportData` TypeScript interface to the top of `api.ts` matching the Pydantic model fields.

**Sub-task 3-E-ii — Replace the SAR Report tab content in `cases/[id]/page.tsx`:**

Remove the old read-only `<Sec>` + `<KV>` accordion and replace with editable form.

State to add at the top of the component:
```typescript
const [reportData, setReportData] = useState<SARReportData | null>(null);
const [reportLoading, setReportLoading] = useState(false);
const [saving, setSaving] = useState(false);
const [pdfDownloading, setPdfDownloading] = useState(false);
```

When the SAR Report tab is active and `data.risk_assessment` exists, auto-load `report-data`:
```typescript
useEffect(() => {
  if (tab === 'SAR Report' && data?.risk_assessment && !reportData) {
    setReportLoading(true);
    sarApi.getReportData(id).then(setReportData).finally(() => setReportLoading(false));
  }
}, [tab, data]);
```

Render the editable form inside the SAR Report tab section using four collapsible sections via `<details>/<summary>` HTML elements (or useState toggles). Each section has:

- **Section A — Filing & Institution Info**
  - Text inputs: Filing Institution Name, Filing Date, Report Period Start/End
  - Checkbox: "✅ Filing Info Reviewed" → sets `section_filing_reviewed`

- **Section B — Subject & Transaction Info** (mostly read-only, but analyst can annotate)
  - Show: Account ID (read-only), Total Amount (read-only), Date Range (read-only)
  - Geographies and Transaction Types shown as comma-separated pills
  - Checkbox: "✅ Transactions Reviewed" → sets `section_subject_reviewed`

- **Section C — Fraud Typology**
  - Dropdown for `typology` (use the keys from `TYPOLOGY_REGISTRY`: Structuring, Layering, Rapid Movement, High-Risk Geography, Smurfing, TBML, Crypto Layering, Unknown)
  - Auto-fill `typology_code`, `typology_description`, `regulatory_references` when dropdown changes (hard-code the mapping in the frontend)
  - Textarea for `suspicion_reason` (editable)
  - Checkbox: "✅ Typology Reviewed" → sets `section_typology_reviewed`

- **Section D — AI Narrative** (fully editable)
  - Large `<textarea>` for `narrative_body` (pre-filled from Groq, fully editable), min-height 200px
  - Analyst notes textarea
  - Checkbox: "✅ Narrative Reviewed" → sets `section_narrative_reviewed`

Buttons at the bottom:
- **"💾 Save Draft"** → calls `sarApi.saveReportData(id, reportData)` (PUT), shows "Saved ✓" for 2s
- **"📄 Download PDF"** (only enabled when all 4 review boxes are checked):
  - Calls `sarApi.downloadPdfFromServer(id, reportData)`
  - Triggers browser download: `const url = URL.createObjectURL(blob); a.click()`

Show a review progress indicator: `{reviewed}/{4} sections reviewed` with a thin progress bar.

**Style rules:**
- Use inline `style={{}}` props for all backgrounds/borders (matching existing patterns in the file)
- Input fields: use existing `.input-dark` CSS class
- Textareas: `className="input-dark"` + `style={{ width: '100%', resize: 'vertical' }}`
- Section headers: same style as existing `<h3>` elements in the file

**DONE CHECK:**
1. Navigate to `/app/cases/{any_red_case_id}` → go to SAR Report tab.
2. Confirm report data loads (all fields pre-populated from backend).
3. Edit the narrative body → click Save Draft → confirm PUT request goes through (check network tab).
4. Check all 4 reviewed boxes → confirm Download PDF button activates.
5. Click Download PDF → confirm a multi-page PDF downloads with professional formatting.

---

## FEATURE 4 — Multi-API LLM Support (Modular Provider Architecture)

**Goal:** Replace the single Groq dependency in `agents/agent3_narrative/minimax_client.py`
with a modular multi-provider architecture. The unified client tries providers in order from
a config. Each provider is an isolated adapter file. Fallback to template if all fail.

**Backend files:** `agents/agent3_narrative/` (new subdirectory structure)
**Frontend files:** None (backend only, but health endpoint updated)

---

### TASK 4-A — Create the LLM Provider Config

**File to create:** `agents/agent3_narrative/llm_config.py`

**Instructions:**
```python
import os

LLM_CONFIG = {
    "primary": os.getenv("LLM_PRIMARY_PROVIDER", "groq"),
    "fallback_chain": ["groq", "openai", "anthropic", "gemini"],
    "temperature": 0.1,
    "max_tokens": 900,
    "providers": {
        "groq": {
            "model": "llama3-8b-8192",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key_env": "GROQ_API_KEY"
        },
        "openai": {
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY"
        },
        "anthropic": {
            "model": "claude-3-haiku-20240307",
            "base_url": None,
            "api_key_env": "ANTHROPIC_API_KEY"
        },
        "gemini": {
            "model": "gemini-1.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key_env": "GEMINI_API_KEY"
        }
    }
}
```

**DONE CHECK:**
```bash
python -c "from agents.agent3_narrative.llm_config import LLM_CONFIG; print(LLM_CONFIG['primary'])"
# Prints "groq"
```

---

### TASK 4-B — Create Groq Provider Adapter

**File to create:** `agents/agent3_narrative/providers/__init__.py` (empty)
**File to create:** `agents/agent3_narrative/providers/groq_adapter.py`

**Instructions:**
```python
import openai, os
from agents.agent3_narrative.llm_config import LLM_CONFIG

async def call_groq(system_prompt: str, user_prompt: str) -> str:
    cfg = LLM_CONFIG["providers"]["groq"]
    key = os.getenv(cfg["api_key_env"], "")
    if not key:
        raise ValueError("GROQ_API_KEY not set")
    client = openai.AsyncOpenAI(base_url=cfg["base_url"], api_key=key)
    resp = await client.chat.completions.create(
        model=cfg["model"],
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=LLM_CONFIG["temperature"],
        max_tokens=LLM_CONFIG["max_tokens"],
        timeout=20,
    )
    return resp.choices[0].message.content or ""
```

**DONE CHECK:** File imports without error.

---

### TASK 4-C — Create OpenAI Provider Adapter

**File to create:** `agents/agent3_narrative/providers/openai_adapter.py`

**Instructions:** Same structure as groq_adapter.py. Function name: `call_openai`. Use `cfg["base_url"]` = openai official URL. Raise ValueError if key missing.

**DONE CHECK:** Imports without error.

---

### TASK 4-D — Create Anthropic Provider Adapter

**File to create:** `agents/agent3_narrative/providers/anthropic_adapter.py`

**Pre-requisite:** `pip install anthropic` and add `anthropic` to `requirements.txt`.

**Instructions:**
```python
import anthropic, os
from agents.agent3_narrative.llm_config import LLM_CONFIG

async def call_anthropic(system_prompt: str, user_prompt: str) -> str:
    cfg = LLM_CONFIG["providers"]["anthropic"]
    key = os.getenv(cfg["api_key_env"], "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.AsyncAnthropic(api_key=key)
    msg = await client.messages.create(
        model=cfg["model"],
        max_tokens=LLM_CONFIG["max_tokens"],
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return msg.content[0].text
```

**DONE CHECK:** Imports without error.

---

### TASK 4-E — Create Gemini Provider Adapter

**File to create:** `agents/agent3_narrative/providers/gemini_adapter.py`

**Instructions:** Gemini supports OpenAI-compatible API. Use `openai.AsyncOpenAI` with Gemini's base URL and `GEMINI_API_KEY`. Function: `call_gemini(system_prompt, user_prompt) -> str`. Raise ValueError if key missing.

**DONE CHECK:** Imports without error.

---

### TASK 4-F — Rewrite Unified Multi-Provider Client

**File to modify:** `agents/agent3_narrative/minimax_client.py`
**Action:** Rename current file to `minimax_client_LEGACY.py`, then create new `minimax_client.py`.

**Instructions:**
The new file must keep the same external function signature so Agent 3's `node.py` import `from agents.agent3_narrative.minimax_client import generate_narrative` works unchanged.

```python
import os, logging
from agents.agent3_narrative.llm_config import LLM_CONFIG
from agents.agent3_narrative.prompts import SYSTEM_PROMPT, build_user_prompt
from agents.agent3_narrative.fallback import generate_fallback_narrative
from agents.agent3_narrative.providers.groq_adapter import call_groq
from agents.agent3_narrative.providers.openai_adapter import call_openai
from agents.agent3_narrative.providers.anthropic_adapter import call_anthropic
from agents.agent3_narrative.providers.gemini_adapter import call_gemini

PROVIDER_MAP = {
    "groq":      call_groq,
    "openai":    call_openai,
    "anthropic": call_anthropic,
    "gemini":    call_gemini,
}

async def generate_narrative(state) -> str:
    sys_p  = SYSTEM_PROMPT
    user_p = build_user_prompt(state)
    
    # build ordered list: primary first, then remaining fallback chain
    chain = [LLM_CONFIG["primary"]] + [
        p for p in LLM_CONFIG["fallback_chain"] if p != LLM_CONFIG["primary"]
    ]
    
    for provider in chain:
        api_key_env = LLM_CONFIG["providers"].get(provider, {}).get("api_key_env", "")
        if not os.getenv(api_key_env, ""):
            logging.debug(f"[LLM] Skipping {provider} — API key not set")
            continue
        try:
            call_fn = PROVIDER_MAP.get(provider)
            if call_fn is None:
                continue
            result = await call_fn(sys_p, user_p)
            if result and len(result) >= 50:
                logging.info(f"[LLM] Narrative generated via provider: {provider}")
                return result
        except Exception as e:
            logging.warning(f"[LLM] Provider {provider} failed: {e}")
    
    logging.error("[LLM] All providers failed — using template fallback")
    return generate_fallback_narrative(state)
```

**DONE CHECK:**
```bash
python -c "from agents.agent3_narrative.minimax_client import generate_narrative; print('OK')"
# Then submit test transaction. Check FastAPI logs for "[LLM] Narrative generated via provider: groq"
```

---

### TASK 4-G — Update Health Endpoint to Show LLM Provider Status

**File to modify:** `main.py`

**Instructions:**
Update `GET /health` response to include LLM provider config:
```python
from agents.agent3_narrative.llm_config import LLM_CONFIG

@app.get("/health")
async def health_check():
    provider_status = {
        name: bool(os.getenv(cfg["api_key_env"], ""))
        for name, cfg in LLM_CONFIG["providers"].items()
    }
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "llm": {
            "primary_provider": LLM_CONFIG["primary"],
            "fallback_chain": LLM_CONFIG["fallback_chain"],
            "providers_configured": provider_status
        }
    }
```

**DONE CHECK:**
```bash
curl http://localhost:8000/health
# Returns JSON with groq: true (or based on which keys are set)
```

---

### TASK 4-H — Update .env.example and .env.local Documentation

**File to modify:** `.env.example`
**File to update (document only, do NOT commit actual keys):** `.env.local`

**Instructions:**
Add to `.env.example`:
```
# LLM Provider Configuration
# Set LLM_PRIMARY_PROVIDER to: groq | openai | anthropic | gemini
LLM_PRIMARY_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here
```

**DONE CHECK:** `.env.example` shows all 5 new variables. The GROQ_API_KEY already set in `.env.local` is picked up by the new config system.

---

## MASTER CHECKLIST — Before Final Demo

Run through this checklist in order. Every item must be ✅ before demo.

```
FEATURE 1 — Dataset & History
[ ] Task 1-A: 160 transactions in data/transactions_dataset.py, importable
[ ] Task 1-B: TransactionHistoryStore works, get_history + get_velocity correct
[ ] Task 1-C: Agent 2 injects past transaction context — new risk signals appear
[ ] Task 1-D: scripts/run_batch_pipeline.py runs to completion, batch_results.json produced
[ ] Task 1-E: FastAPI loads batch_results.json at startup, /cases returns 160+ entries

FEATURE 2 — Account Audit Trail
[ ] Task 2-A: Neo4j schema extended, AccountAuditSummary node created (or graceful skip if offline)
[ ] Task 2-B: Agent 5 writes agent_decisions + account_id to AuditRecord
[ ] Task 2-C: GET /account/{account_id}/audit-trail returns multi-case JSON
[ ] Task 2-D: Next.js Audit Trail tab shows "View All Cases for This Account" section

FEATURE 3 — Professional SAR Report
[ ] Task 3-A: SARReportData Pydantic model added to schemas.py, from_sar_case() works
[ ] Task 3-B: typology_definitions.py created, classify_typology() returns correct typology
[ ] Task 3-C: reports/pdf_generator.py generates valid 7-page PDF (> 20KB)
[ ] Task 3-D: /report-data GET/PUT + /generate-pdf POST endpoints work
[ ] Task 3-E: Next.js SAR Report tab shows editable form, save draft works, PDF downloads from server

FEATURE 4 — Multi-LLM Providers
[ ] Task 4-A: llm_config.py created, reads LLM_PRIMARY_PROVIDER from env
[ ] Task 4-B: groq_adapter.py created, call_groq function works
[ ] Task 4-C: openai_adapter.py created, call_openai function works
[ ] Task 4-D: anthropic_adapter.py created, call_anthropic function works
[ ] Task 4-E: gemini_adapter.py created, call_gemini function works
[ ] Task 4-F: minimax_client.py rewritten — fallback chain tested
[ ] Task 4-G: /health endpoint returns LLM provider status JSON
[ ] Task 4-H: .env.example updated with all 5 LLM env vars

FULL INTEGRATION TEST
[ ] Run batch pipeline → confirm 160+ cases appear in /app/cases
[ ] Open a RED case → go to SAR Report tab → edit narrative → save draft
[ ] Check all 4 review boxes → click Download PDF → confirm 7-page PDF
[ ] Go to Audit Trail tab → click "View All Cases for This Account" → confirm multi-case list
[ ] Check /health → confirm LLM provider status shows groq: true
```

---

## SCHEMA CHANGES SUMMARY

Changes to `agents/shared/schemas.py` require ALL team members to agree:

1. Add `SARReportData` model (Task 3-A)
2. Add `sar_report: Optional[SARReportData] = None` to `SARCase` (Task 3-A)
3. Add `account_id: str = ""` and `agent_decisions: list[dict]` to `AuditRecord` (Task 2-B)

---

## NEW FILES CREATED BY THIS PLAN

```
data/__init__.py                                     (Task 1-A)
data/transactions_dataset.py                         (Task 1-A)
data/transaction_history.py                          (Task 1-B)
data/batch_results.json                              (generated by Task 1-D)
scripts/__init__.py                                  (Task 1-D)
scripts/run_batch_pipeline.py                        (Task 1-D)
reports/__init__.py                                  (Task 3-B)
reports/typology_definitions.py                      (Task 3-B)
reports/pdf_generator.py                             (Task 3-C)
agents/agent3_narrative/llm_config.py               (Task 4-A)
agents/agent3_narrative/providers/__init__.py        (Task 4-B)
agents/agent3_narrative/providers/groq_adapter.py   (Task 4-B)
agents/agent3_narrative/providers/openai_adapter.py (Task 4-C)
agents/agent3_narrative/providers/anthropic_adapter.py (Task 4-D)
agents/agent3_narrative/providers/gemini_adapter.py (Task 4-E)
agents/agent3_narrative/minimax_client_LEGACY.py    (Task 4-F, renamed from original)
```

## MODIFIED FILES BY THIS PLAN

```
agents/agent2_risk/node.py               (Task 1-C)
agents/agent5_audit/node.py              (Task 2-B)
agents/shared/schemas.py                 (Task 3-A) — coordinate with team
main.py                                  (Tasks 1-E, 2-C, 3-D, 4-G)
graph/neo4j/init_schema.py               (Task 2-A)
ui/nextjs/lib/api.ts                     (Tasks 2-D, 3-E)
ui/nextjs/app/app/cases/[id]/page.tsx   (Tasks 2-D, 3-E)
agents/agent3_narrative/minimax_client.py (Task 4-F)
requirements.txt                         (Tasks 3-C, 4-D — add reportlab, anthropic)
.env.example                             (Task 4-H)
```

---

*End of Enhanced Implementation Plan — SAR Platform v3*
*Enhanced: March 26 2026 01:00 IST*
*Covers: Next.js 14/16 App Router frontend, Groq multi-provider LLM, ReportLab PDF, Account-level audit trail*
