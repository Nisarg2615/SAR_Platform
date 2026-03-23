# SAR Platform — Sprint Task Board
# Deadline: March 26 2026 midnight (hackathon submission)
# Team: 4 engineers — 2-day sprint

---

## 👥 Team Seniority & Ownership

| Rank | Name | Role | Modules Owned |
|---|---|---|---|
| 1 (Most Senior) | **Ricky** | Tech Lead — Backend + ML | `main.py`, `agents/pipeline.py`, `agents/agent1_ingestion/`, `agents/agent2_risk/`, `prediction_engine/` |
| 2 | **Nisarg** | AI Engineer — LLM + Graph | `agents/agent3_narrative/`, `agents/agent4_compliance/`, `graph/neo4j/` |
| 3 | **Anshul** | Full-Stack — UI + Audit | `agents/agent5_audit/`, `agents/agent6_review/`, `ui/` |
| 4 | **Ashwin** | Junior — Infra + Testing | `infra/`, `docker-compose.yml`, `tests/unit/`, `tests/integration/` |

> **Rule:** Only work in your owned modules. Shared files (`agents/shared/schemas.py`, `requirements.txt`) require team agreement before editing.

---

## 📅 DAY 1 — March 24, 2026

### 🔴 Ricky (Lead) — Backend + ML Pipeline
**Branch:** `feat/ricky-day1`
**Difficulty: ★★★★★**

- [ ] **[CRITICAL]** Define all Pydantic schemas in `agents/shared/schemas.py`
  - `SARCase`, `NormalizedCase`, `RiskAssessment`, `SARNarrative`, `ComplianceResult`, `AuditRecord`
  - This blocks everyone — do this FIRST by 10am
- [ ] Build `agents/agent1_ingestion/node.py`
  - Ingest raw transaction dict into `NormalizedCase`
  - Mock Presidio: set `presidio_masked=True`
  - Append to `audit_trail`; never crash — always return state
- [ ] Build `agents/agent2_risk/node.py` + `typologies.py`
  - XGBoost scorer loading from `prediction_engine/model.py`
  - SHAP feature importance extraction
  - Match to 4 AML typologies (structuring, layering, smurfing, wire fraud)
  - Output `RiskAssessment` with `risk_score` (0-1) and `risk_tier` (GREEN/AMBER/RED/CRITICAL)
- [ ] Build `prediction_engine/model.py`
  - XGBoost model training on synthetic data (40 features)
  - SHAP integration for explainability
- [ ] Build `prediction_engine/simulator.py`
  - 3 demo scenarios: Structuring, Layering, Smurfing
  - Each returns a realistic `raw_transaction` dict
- [ ] Wire up `agents/pipeline.py` (LangGraph StateGraph)
  - Connect Agent 1 → gate_1 → Agent 2 → gate_2 → check_if_red → Agent 3 → gate_3 → Agent 4 → gate_4 → Agent 5 → END
  - Implement all 5 validation gates

**Done when:** `pytest tests/unit/test_agent1.py tests/unit/test_agent2.py -v` passes

---

### 🟠 Nisarg — AI Narrative + Graph
**Branch:** `feat/nisarg-day1`
**Difficulty: ★★★★☆**

- [ ] **[BLOCKER]** Wait for Ricky's schemas (expected by 10am Day 1)
- [ ] Build `agents/agent3_narrative/node.py`
  - Call `minimax_client.py` to generate SAR narrative
  - Use prompts from `prompts.py` (never inline prompts)
  - Output: 4-section `SARNarrative` (summary, subject_info, suspicious_activity, law_enforcement_note)
  - Append to `audit_trail`
- [ ] Build `agents/agent3_narrative/minimax_client.py`
  - Minimax API: `https://api.minimax.chat/v1/text/chatcompletion_v2`
  - Model: `MiniMax-Text-01`, temp 0.1, max_tokens 800, timeout 30s
  - Bearer token auth from `MINIMAX_API_KEY` env var
- [ ] Build `agents/agent3_narrative/prompts.py`
  - System prompt: regulatory SAR writing style
  - User prompt template: inject `NormalizedCase` + `RiskAssessment` data
  - Include 3 hardcoded Weaviate SAR templates as context strings
- [ ] Build `agents/agent3_narrative/fallback.py`
  - Template-based fallback (no LLM) activated when Minimax fails
  - Must produce valid `SARNarrative` from `RiskAssessment` fields
- [ ] Build `agents/agent4_compliance/node.py` + `rules.py`
  - 8 compliance check functions (BSA, FinCEN thresholds, geography flags, etc.)
  - Output: `ComplianceResult` with list of `compliance_issues`
  - Always returns a list (can be empty)

**Done when:** `pytest tests/unit/test_agent3.py tests/unit/test_agent4.py -v` passes and Minimax API returns a valid narrative

---

### 🟡 Anshul — UI + Audit + Human Review
**Branch:** `feat/anshul-day1`
**Difficulty: ★★★☆☆**

- [ ] **[BLOCKER]** Wait for Ricky's schemas (expected by 10am Day 1)
- [ ] Build `agents/agent5_audit/node.py`
  - Generate SHA256 `immutable_hash` from full case JSON
  - Output `AuditRecord` with hash + agent timeline
  - Write AuditEvent node to Neo4j (APPEND ONLY — never update/delete)
- [ ] Build `agents/agent6_review/node.py`
  - Accept `analyst_name` string
  - Set `status = FILED`, `analyst_approved_by`, `final_filed_timestamp`
  - Append final audit entry
- [ ] Scaffold `ui/app.py` (Streamlit — 5 pages)
  - Page 1: Submit Transaction (form + demo presets)
  - Page 2: Risk Analysis (score, SHAP bars, typology)
  - Page 3: Graph View (pyvis placeholder)
  - Page 4: SAR Review (narrative + compliance + approve/dismiss buttons)
  - Page 5: Audit Trail (timeline view)
- [ ] Build `ui/api_client.py`
  - Functions wrapping every FastAPI endpoint
  - Handle connection errors gracefully (show error in UI, don't crash)
- [ ] Build `ui/mock_data.py`
  - Mock `SARCase` JSON for offline UI development

**Done when:** Streamlit app launches, all 5 pages render without errors using mock data

---

### 🟢 Ashwin — Infrastructure + Tests
**Branch:** `feat/ashwin-day1`
**Difficulty: ★★☆☆☆**

- [ ] Validate and run `docker-compose.yml`
  - Ensure Neo4j, PostgreSQL, Redis, Kafka, Weaviate all start cleanly
  - Fix any port conflicts or config issues
- [ ] Write `infra/start_all.sh`
  - Start all Docker services
  - Wait for health checks to pass
  - Print colored status output
- [ ] Write `infra/check_services.sh`
  - HTTP/TCP health check every service
  - Output: service name → UP/DOWN with port
- [ ] Initialize Neo4j schema: `graph/neo4j/init_schema.py`
  - Create constraints: unique `account_id`, unique `transaction_id`, unique `case_id`
  - Create indexes on `timestamp`, `risk_score`
- [ ] Write unit test scaffolds in `tests/unit/`
  - `test_agent1.py` — test normalization with sample dict
  - `test_agent2.py` — test risk scoring returns valid tier
  - `test_agent3.py` — test narrative length > 100 chars
  - `test_agent4.py` — test compliance list is always returned
  - `test_agent5.py` — test SHA256 hash is non-empty
- [ ] Confirm `requirements.txt` includes all needed packages

**Done when:** `./infra/start_all.sh` runs cleanly and all Docker services show UP

---

## 📅 DAY 2 — March 25, 2026

### 🔴 Ricky — FastAPI Endpoints + Integration
**Branch:** `feat/ricky-day2`
**Difficulty: ★★★★★**

- [ ] Build `main.py` — all 10 FastAPI endpoints
  - `POST /submit-transaction` — calls prediction engine + creates SARCase
  - `GET /cases` — returns all cases from in-memory store
  - `GET /case/{id}` — returns single case
  - `POST /case/{id}/run-pipeline` — runs full LangGraph pipeline
  - `GET /case/{id}/pipeline-status` — returns completed agents list
  - `POST /case/{id}/generate-narrative` — calls Agent 3 only
  - `POST /case/{id}/approve` — calls Agent 6 (analyst_name in body)
  - `POST /case/{id}/dismiss` — sets status DISMISSED
  - `GET /case/{id}/graph` — returns nodes + edges JSON for pyvis
  - `GET /health` — `{"status": "ok"}`
- [ ] CORS: open all origins for local dev
- [ ] All endpoints catch exceptions, return structured error JSON (no raw 500s)
- [ ] End-to-end test: `curl -X POST /submit-transaction` with structuring scenario → RED case created, pipeline runs, narrative generated

**Done when:** All 10 endpoints return correct responses per `curl` tests

---

### 🟠 Nisarg — Neo4j Graph API + Visualization
**Branch:** `feat/nisarg-day2`
**Difficulty: ★★★★☆**

- [ ] Build `graph/neo4j/graph_api.py`
  - `get_case_graph(case_id)` → returns `{nodes: [...], edges: [...]}`
  - Node types: Account (blue), Transaction (amber), SARCase (red), RiskSignal (orange), AuditEvent (green)
- [ ] Write all Cypher queries in `graph/neo4j/cypher_queries/`
  - `create_account.cypher`
  - `create_transaction.cypher`
  - `create_sar_case.cypher`
  - `create_audit_event.cypher`
  - `get_case_subgraph.cypher`
- [ ] Connect Agent 5's Neo4j writer to use `GraphWriter` class
- [ ] Wire pyvis graph rendering in UI Page 3 (Graph View)
  - Call `GET /case/{id}/graph` → render with pyvis
  - Show node legend (color = type)
- [ ] Full Minimax integration test
  - Verify structured narrative is generated for structuring scenario
  - Verify fallback activates when Minimax key is invalid

**Done when:** Neo4j browser shows correct nodes after running full pipeline on one case

---

### 🟡 Anshul — UI Polish + SAR Narrative Streaming
**Branch:** `feat/anshul-day2`
**Difficulty: ★★★☆☆**

- [ ] Wire UI Page 1 (Submit Transaction) to real API
  - Demo presets populate form fields
  - Submit → spinner → show RED result
- [ ] Wire UI Page 2 (Risk Analysis) to real API
  - Display `risk_score`, SHAP importance bars (use `st.bar_chart`)
  - Show matched typology and risk signals list
- [ ] Wire UI Page 4 (SAR Review) to real API
  - "Generate Narrative" button → stream narrative sections appearing
  - Compliance checklist turning green as each check passes
  - Approve button: text input for analyst name → POST `/case/{id}/approve`
  - Dismiss button: POST `/case/{id}/dismiss`
  - After approve: `st.balloons()` + status shows FILED
- [ ] Wire UI Page 5 (Audit Trail) to real API
  - Timeline of all 5 agent decisions with timestamps
  - SHA256 hash displayed at bottom with copy button
- [ ] Polish all pages: remove spinners stuck, handle error states

**Done when:** Full 6-screen demo flow works end-to-end with real backend

---

### 🟢 Ashwin — Integration Tests + Final Checks
**Branch:** `feat/ashwin-day2`
**Difficulty: ★★☆☆☆**

- [ ] Write `tests/integration/test_full_pipeline.py`
  - Start full pipeline with structuring scenario
  - Assert: `status == FILED` after approve
  - Assert: `audit_trail` has 5+ entries
  - Assert: `immutable_hash` is non-empty SHA256
  - Assert: `risk_score >= 0.85` for structuring scenario
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Run type checking: `python -m mypy agents/`
- [ ] Fix any type errors found by mypy
- [ ] Write `docs/demo_script.md` — word-for-word demo script for 4 minutes
- [ ] Write `docs/pitch_deck_content.md` — slide content outline
- [ ] Final `README.md` review — ensure setup instructions work on fresh machine
- [ ] Confirm no secrets are in any committed file (`git diff --stat origin/main`)

**Done when:** `pytest tests/ -v` passes with 0 failures and demo script is written

---

## 🏁 End-of-Day Sync Routine (Both Days, 9PM)

```bash
# Each person runs:
git add .
git commit -m "feat(dayX-name): summary of what you built"
git push origin feat/your-branch

# Then open a PR to develop on GitHub
# Tag one other person to review
# Merge after 1 approval
```

---

## ✅ Task Completion Checklist

Before marking **any** task done:

| Type | Completion Check |
|---|---|
| Backend endpoint | `curl` returns expected JSON, no errors |
| Agent task | `pytest tests/unit/test_agentN.py -v` passes |
| Neo4j task | `MATCH (n) RETURN n` in browser shows correct nodes |
| UI task | Page works with real data, no stuck spinners |
| Integration | Full pipeline runs on structuring scenario, all fields populated |

---

## 🚫 What is NOT in This Sprint

- Kubernetes deployment (out of scope for hackathon)
- Real Kafka consumer (using asyncio queue + simulator instead)
- Real Presidio (mocked — `presidio_masked=True`)
- Real PostgreSQL persistence (in-memory dict for demo)
- Real Weaviate RAG (3 hardcoded SAR templates as context strings)

These are noted in the pitch as "production architecture" features.

---

## 📞 Blockers & Communication

- Post blockers in team WhatsApp **immediately**
- Do not spend more than **30 minutes** stuck on anything
- Schema changes to `agents/shared/schemas.py` require **all 4 people to agree** first
- Ricky (lead) is the final decision-maker on architecture conflicts
