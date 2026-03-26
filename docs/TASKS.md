# SAR Platform — Sprint Task Board
# Deadline: March 26 2026 midnight (hackathon submission)
# Team: 4 engineers — 2-day sprint

> ⚠️ Anshul and Ashwin: ALL your tasks are done entirely inside your code editor.
> You do NOT need to sign into any external service, create any account, or visit any website.
> Every service runs locally via Docker. The LLM is free and built into OpenCode.

---

## 👥 Team Seniority & Module Ownership

| Rank | Name | Role | Modules |
|---|---|---|---|
| 1 — Tech Lead | **Ricky** | Backend + ML • hardest tasks • final architecture decisions | `main.py`, `agents/pipeline.py`, `agents/agent1_ingestion/`, `agents/agent2_risk/`, `prediction_engine/` |
| 2 — Senior | **Nisarg** | AI + Graph • works independently • owns LLM pipeline | `agents/agent3_narrative/`, `agents/agent4_compliance/`, `agents/agent5_audit/`, `graph/neo4j/` |
| 3 | **Anshul** | UI + Audit • works under Ricky and Nisarg for API contracts | `agents/agent6_review/`, `ui/` |
| 4 — Junior | **Ashwin** | Infra + Tests • pure code editor work • no external sign-ins | `infra/`, `docker-compose.yml`, `tests/unit/`, `tests/integration/` |

---

## 🔧 ASHWIN — Before You Start (Important)

You work **100% inside your code editor and terminal**. All services run locally.

```bash
# Your only setup steps:
git clone https://github.com/Rickykapoor/Sar-platform.git
cd Sar-platform
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local      # values are already correct — don't change them
docker compose up -d            # starts everything
```

You own the Docker setup and tests. You never need to log into GitHub web, Minimax, AWS, or anything else. Everything is local.

---

## 🖥 ANSHUL — Before You Start (Important)

You work **100% inside your code editor**. The FastAPI backend is already spec'd — you just call it from the UI using `ui/api_client.py`.

```bash
# Your only setup steps (same as Ashwin):
git clone https://github.com/Rickykapoor/Sar-platform.git
cd Sar-platform && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local
docker compose up -d
```

Use `ui/mock_data.py` to build your pages before Ricky's backend is ready.
When Ricky's endpoints are live, switch `api_client.py` to hit real `localhost:8000`.
You do NOT need to understand the ML or Neo4j code — just call the API.

---

## 📅 DAY 1 — March 24, 2026

---

### 🔴 RICKY — Schemas + Core Pipeline
**Branch:** `feat/ricky-day1`
**Difficulty: ★★★★★ — Most critical tasks, blocks everyone else**

> ⏰ **Must complete schemas by 10am** — Nisarg and Anshul are blocked until then.

- [ ] **[FIRST — 10am deadline]** Define ALL Pydantic models in `agents/shared/schemas.py`
  - `SARCase`, `SARStatus` (enum: PENDING/IN_REVIEW/FILED/DISMISSED)
  - `NormalizedCase` (includes `presidio_masked: bool`, `transactions: list`)
  - `RiskAssessment` (includes `risk_score: float`, `risk_tier: RiskTier`, `risk_signals: list`, `shap_values: dict`)
  - `SARNarrative` (includes `narrative_body: str` > 100 chars, `summary`, `subject_info`, `suspicious_activity`, `law_enforcement_note`)
  - `ComplianceResult` (includes `compliance_issues: list` — always a list, never None)
  - `AuditRecord` (includes `immutable_hash: str`, `agent_timeline: list`)
  - Post in WhatsApp when done: "✅ schemas.py ready"

- [ ] Build `agents/agent1_ingestion/node.py`
  - Follow the exact agent function signature: `async def agent1_ingest(state: SARCase) -> SARCase`
  - Read `state.raw_transaction`, normalize into `NormalizedCase`
  - Set `presidio_masked=True` (Presidio is mocked for demo)
  - Populate `normalized.transactions` list from raw input
  - Append to `state.audit_trail` (required)
  - Never `raise` — always catch + `state.error_log.append` + `return state`

- [ ] Build `agents/agent2_risk/node.py` + `typologies.py`
  - Load XGBoost model from `prediction_engine/model.py`
  - Run SHAP to get feature importance dict
  - Match against 4 AML typologies in `typologies.py`: Structuring, Layering, Smurfing, Wire Fraud
  - Output `RiskAssessment` with score (0.0–1.0) and tier
  - Append to `state.audit_trail`

- [ ] Build `prediction_engine/model.py`
  - Train XGBoost on synthetic transaction data (40 features: amount, frequency, geography_score, hour_of_day, etc.)
  - Save model to disk: `prediction_engine/xgb_model.pkl`
  - Load on startup, reuse per request
  - SHAP: `shap.TreeExplainer` → return top-5 feature names + values as dict

- [ ] Build `prediction_engine/simulator.py`
  - 3 demo scenario functions: `get_structuring_scenario()`, `get_layering_scenario()`, `get_smurfing_scenario()`
  - Each returns a realistic `raw_transaction` dict
  - Structuring: amount=9800 USD, multiple same-day transactions

- [ ] Wire `agents/pipeline.py` (LangGraph StateGraph)
  - Order: START → agent1 → gate1 → agent2 → gate2 → check_if_red → agent3 → gate3 → agent4 → gate4 → agent5 → END
  - Each gate is a function that checks state, routes to error or continues
  - `check_if_red`: GREEN tier → skip to END; RED/AMBER → continue to agent3
  - Entry point: `async def run_pipeline(raw_transaction: dict) -> SARCase`

**Done when:** `pytest tests/unit/test_agent1.py tests/unit/test_agent2.py -v` passes

---

### 🟠 NISARG — LLM Narrative + Graph + Compliance
**Branch:** `feat/nisarg-day1`
**Difficulty: ★★★★☆**

> ⏳ **Wait for Ricky's schemas message in WhatsApp (expected ~10am), then start immediately.**
> While waiting: read `MASTER_CONTEXT.md`, understand the `SARNarrative` and `ComplianceResult` models you'll produce.

- [ ] Build `agents/agent3_narrative/prompts.py`
  - `SYSTEM_PROMPT`: regulatory SAR writing style, professional, FinCEN format
  - `build_user_prompt(state: SARCase) -> str`: inject NormalizedCase + RiskAssessment fields
  - Include 3 hardcoded SAR example texts as static context (simulate Weaviate RAG)
  - NO prompts in `node.py` — always import from this file

- [ ] Build `agents/agent3_narrative/minimax_client.py`
  - Use OpenCode's free model — no API key:
    ```python
    import openai
    client = openai.AsyncOpenAI(base_url="http://localhost:4000/v1", api_key="opencode-free")
    ```
  - Model: `minimax/MiniMax-Text-2.5`, temp 0.1, max_tokens 800
  - Always wrap in try/except → call `generate_fallback_narrative(state)` on any failure
  - Never let this crash — it must always return a string

- [ ] Build `agents/agent3_narrative/fallback.py`
  - `generate_fallback_narrative(state: SARCase) -> str`
  - Pure string template — no LLM involved
  - Pulls from `state.risk_assessment` fields
  - Must produce narrative_body longer than 100 characters

- [ ] Build `agents/agent3_narrative/node.py`
  - Calls `minimax_client.generate_narrative(state)` → gets string
  - Parse into 4 sections: summary, subject_info, suspicious_activity, law_enforcement_note
  - Populate `state.narrative = SARNarrative(...)`
  - Append to `state.audit_trail`

- [ ] Build `agents/agent4_compliance/rules.py`
  - 8 functions, each takes `SARCase`, returns `Optional[str]` (None = passed, string = issue description)
  - Rules: BSA threshold ($10k), FinCEN 314a match check, geography high-risk flag, structuring threshold ($9.5k–$10k), unusual transaction frequency, round number flag, dormant account activity, multiple jurisdiction flag
  - Keep each function < 20 lines

- [ ] Build `agents/agent4_compliance/node.py`
  - Run all 8 rules, collect non-None results into list
  - `state.compliance = ComplianceResult(compliance_issues=results)`
  - Append to `state.audit_trail`

**Done when:** `pytest tests/unit/test_agent3.py tests/unit/test_agent4.py -v` passes

---

### 🟡 ANSHUL — UI Scaffold + Agent 5 + Agent 6
**Branch:** `feat/anshul-day1`
**Difficulty: ★★★☆☆ — Pure coding, no external sign-ins**

> ⏳ **Wait for Ricky's schemas message (expected ~10am), then start.**
> Build UI pages using mock data first — you don't need Ricky's API to be live.

- [ ] Build `agents/agent5_audit/node.py`
  - Receive full state, serialize entire `SARCase` to JSON string
  - `import hashlib; hash = hashlib.sha256(json_str.encode()).hexdigest()`
  - `state.audit = AuditRecord(immutable_hash=hash, agent_timeline=state.audit_trail.copy())`
  - Append final entry to `state.audit_trail`
  - Write AuditEvent node to Neo4j via `GraphWriter` (Nisarg's class — ask him for the interface)

- [ ] Build `agents/agent6_review/node.py`
  - Accepts `analyst_name: str` as input
  - `state.analyst_approved_by = analyst_name`
  - `state.status = SARStatus.FILED`
  - `state.final_filed_timestamp = datetime.now()`
  - Append to `state.audit_trail`
  - Note: Agent 6 is NOT in the LangGraph pipeline — it's called directly by the FastAPI `/case/{id}/approve` endpoint

- [ ] Build `ui/mock_data.py`
  - One realistic `SARCase`-shaped dict for each of the 5 UI pages
  - Include structuring scenario fake data: risk_score=0.92, tier="RED", narrative text, compliance issues, audit trail with 5 entries

- [ ] Build `ui/api_client.py`
  - One Python function per FastAPI endpoint (10 functions total)
  - All functions use `httpx.AsyncClient` or `requests` to call `localhost:8000`
  - Each handles `ConnectionError` gracefully: return `None` and log the error, never crash the UI

- [ ] Scaffold `ui/app.py` — 5 Streamlit pages using mock data
  - Page 1: Submit Transaction — form with fields + 3 preset buttons (Structuring, Layering, Smurfing)
  - Page 2: Risk Analysis — show risk_score, tier badge, SHAP bar chart, typology name, risk signals list
  - Page 3: Graph View — placeholder pyvis iframe area (Nisarg wires real data in Day 2)
  - Page 4: SAR Review — narrative text area, compliance checklist (green ✅ / red ❌), Approve + Dismiss buttons
  - Page 5: Audit Trail — `st.expander` per agent, timestamp, SHA256 hash at bottom

**Done when:** `streamlit run ui/app.py` opens, all 5 pages render using mock data, no errors in console

---

### 🟢 ASHWIN — Docker + Infra + Test Scaffolds
**Branch:** `feat/ashwin-day1`
**Difficulty: ★★☆☆☆ — Pure editor + terminal work, zero external sign-ins**

> ✅ You can start immediately — your tasks don't depend on schemas.

- [ ] Verify `docker-compose.yml` starts cleanly
  - `docker compose up -d`
  - Wait 2 minutes, then `docker compose ps` — all must show "running"
  - If anything fails: read `docker compose logs <service>`, fix in `docker-compose.yml`
  - Common Neo4j fix: give it more memory — `NEO4J_server_memory_heap_max__size: 1G`

- [ ] Write `infra/start_all.sh`
  ```bash
  #!/bin/bash
  set -e
  echo "🚀 Starting SAR Platform services..."
  docker compose up -d
  echo "⏳ Waiting for services to be ready..."
  sleep 30
  echo "✅ All services started. Run ./infra/check_services.sh to verify."
  ```

- [ ] Write `infra/check_services.sh`
  - Check each service with `curl` or `nc -z localhost <port>`
  - Print: `✅ Neo4j localhost:7474 UP` or `❌ Neo4j localhost:7474 DOWN`
  - Non-zero exit code if any service is DOWN

- [ ] Write `graph/neo4j/init_schema.py` (coordinate with Nisarg for the GraphWriter class placement)
  - Connect to Neo4j using `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` from `.env.local`
  - Create uniqueness constraints:
    - `CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE`
    - `CREATE CONSTRAINT IF NOT EXISTS FOR (t:Transaction) REQUIRE t.transaction_id IS UNIQUE`
    - `CREATE CONSTRAINT IF NOT EXISTS FOR (s:SARCase) REQUIRE s.case_id IS UNIQUE`
  - Create indexes on `timestamp`, `risk_score`
  - Print "Schema initialized" when done

- [ ] Write unit test scaffolds — `tests/unit/`
  - `test_agent1.py`: call `agent1_ingest` with sample raw_transaction dict → assert `state.normalized is not None` and `state.normalized.presidio_masked == True`
  - `test_agent2.py`: call `agent2_assess_risk` → assert `0.0 <= state.risk_assessment.risk_score <= 1.0` and tier in valid set
  - `test_agent3.py`: call `agent3_generate_narrative` → assert `len(state.narrative.narrative_body) > 100`
  - `test_agent4.py`: call `agent4_check_compliance` → assert `isinstance(state.compliance.compliance_issues, list)`
  - `test_agent5.py`: call `agent5_write_audit` → assert `len(state.audit.immutable_hash) == 64` (SHA256 hex)
  - Use `pytest.mark.asyncio` for all async tests

- [ ] Confirm `requirements.txt` includes: `pytest`, `pytest-asyncio`, `pyvis`, `python-dotenv`, `neo4j`, `openai`, `xgboost`, `shap`, `streamlit`, `langgraph`, `langchain`, `fastapi`, `uvicorn`, `pydantic`, `httpx`

**Done when:** `docker compose up -d && ./infra/check_services.sh` shows all services UP and `pytest tests/unit/ -v` runs (even if some tests are skipped pending agent code)

---

## 📅 DAY 2 — March 25, 2026

---

### 🔴 RICKY — All 10 FastAPI Endpoints
**Branch:** `feat/ricky-day2`
**Difficulty: ★★★★★**

> First, pull from develop: `git checkout develop && git pull origin develop && git checkout -b feat/ricky-day2`

- [ ] Build `main.py` — FastAPI application with all 10 endpoints
  - `from fastapi.middleware.cors import CORSMiddleware` → allow all origins
  - In-memory store: `cases: dict[str, SARCase] = {}`
  - `POST /submit-transaction`: call `prediction_engine/model.py`, create `SARCase`, store it, run pipeline if RED
  - `GET /cases`: return `list(cases.values())`
  - `GET /case/{id}`: return `cases[id]` or 404
  - `POST /case/{id}/run-pipeline`: asyncio call to `run_pipeline(...)`, store result
  - `GET /case/{id}/pipeline-status`: return list of agents that have non-None outputs in state
  - `POST /case/{id}/generate-narrative`: call Agent 3 only (for the UI narrative button)
  - `POST /case/{id}/approve`: body has `analyst_name: str`, call Agent 6 logic
  - `POST /case/{id}/dismiss`: set `status = DISMISSED`
  - `GET /case/{id}/graph`: call `graph/neo4j/graph_api.py → get_case_graph(case_id)`
  - `GET /health`: `return {"status": "ok"}`
  - All endpoints: catch exceptions, return `{"error": str(e), "detail": ...}` — never raw 500

- [ ] End-to-end smoke test:
  ```bash
  curl -X POST http://localhost:8000/submit-transaction \
    -H "Content-Type: application/json" \
    -d '{"amount_usd": 9800, "transaction_type": "wire", "geography": "offshore", "account_id": "ACC001"}'
  ```
  Should return a full `SARCase` JSON with `risk_tier: "RED"` and pipeline complete.

**Done when:** All 10 `curl` commands return correct JSON responses

---

### 🟠 NISARG — Neo4j Graph API + Full Integration
**Branch:** `feat/nisarg-day2`
**Difficulty: ★★★★☆**

> First: `git checkout develop && git pull origin develop && git checkout -b feat/nisarg-day2`

- [ ] Build `graph/neo4j/graph_api.py`
  - `get_case_graph(case_id: str) -> dict`: returns `{"nodes": [...], "edges": [...]}`
  - Node format: `{"id": str, "label": str, "type": str, "color": str}`
  - Colors: Account=blue, Transaction=amber, SARCase=red, RiskSignal=orange, AuditEvent=green
  - Edge format: `{"source": str, "target": str, "relationship": str}`

- [ ] Write all Cypher files in `graph/neo4j/cypher_queries/`:
  - `create_account.cypher` — MERGE Account node
  - `create_transaction.cypher` — MERGE Transaction node + SENT/RECEIVED_BY rels
  - `create_sar_case.cypher` — CREATE SARCase node + CONTAINS rel
  - `create_audit_event.cypher` — CREATE AuditEvent + HAS_AUDIT rel (APPEND ONLY)
  - `get_case_subgraph.cypher` — MATCH all nodes connected to a SARCase by case_id

- [ ] Connect Agent 5 to `GraphWriter` class:
  - `GraphWriter(neo4j_driver)` — takes driver from `NEO4J_URI` env var
  - Methods: `write_sar_case(state: SARCase)`, `write_audit_event(event: dict)`
  - RULE: AuditEvent nodes are APPEND ONLY. NEVER UPDATE or DELETE.

- [ ] Wire pyvis rendering in `ui/app.py` Page 3 (coordinate with Anshul):
  - Call `GET /case/{id}/graph` → get nodes/edges JSON
  - Build pyvis `Network`, add nodes with colors, render to HTML string
  - Display with `st.components.v1.html(html_str, height=500)`

- [ ] Integration test: Run full pipeline on structuring scenario, check Neo4j browser shows all node types

**Done when:** Neo4j browser `MATCH (n) RETURN n` shows Account, Transaction, SARCase, RiskSignal, AuditEvent nodes after pipeline run

---

### 🟡 ANSHUL — Wire UI to Real API + Polish
**Branch:** `feat/anshul-day2`
**Difficulty: ★★★☆☆ — Editor-only, no external sign-ins**

> First: `git checkout develop && git pull origin develop && git checkout -b feat/anshul-day2`
> This requires Ricky's Day 2 endpoints to be merged first — pull from develop when they confirm.

- [ ] Wire Page 1 (Submit Transaction) to real API
  - 3 preset buttons (Structuring / Layering / Smurfing) → call `prediction_engine/simulator.py` scenario dicts (ask Ricky for the function names)
  - Submit button → call `api_client.submit_transaction(form_data)`
  - Show spinner while waiting → display RED/AMBER/GREEN badge when response arrives

- [ ] Wire Page 2 (Risk Analysis) to real API
  - `st.metric("Risk Score", value=case.risk_assessment.risk_score)`
  - SHAP bar chart: `st.bar_chart(case.risk_assessment.shap_values)`
  - Show matched typology as `st.info()`, risk signals as `st.warning()` items

- [ ] Wire Page 4 (SAR Review) to real API
  - "Generate Narrative" button → `POST /case/{id}/generate-narrative` → stream response into `st.empty()` updating every 100ms
  - Compliance checklist: iterate `compliance.compliance_issues` → green ✅ if empty, red ❌ per issue
  - Analyst name text input + "Approve and File" button → `POST /case/{id}/approve` → `st.balloons()`
  - "Dismiss" button → `POST /case/{id}/dismiss` → show DISMISSED badge

- [ ] Wire Page 5 (Audit Trail) to real API
  - `for entry in case.audit_trail`: `st.expander(entry["agent"])` → show action, confidence, timestamp
  - SHA256 hash at bottom with monospace font, copy-to-clipboard button
  - Show "Immutable — cannot be modified" label

- [ ] Error state handling on all pages:
  - If API returns error → `st.error("Backend error: ...")` — never blank white page
  - If API is unreachable → `st.warning("Backend offline — showing mock data")`

**Done when:** All 6 demo screens work in sequence using the live backend — no mock data

---

### 🟢 ASHWIN — Integration Tests + Type Fixes + Docs
**Branch:** `feat/ashwin-day2`
**Difficulty: ★★☆☆☆ — Editor + terminal only**

> First: `git checkout develop && git pull origin develop && git checkout -b feat/ashwin-day2`
> Requires all Day 2 branches merged into develop first — merge yours last.

- [ ] Write `tests/integration/test_full_pipeline.py`
  ```python
  @pytest.mark.asyncio
  async def test_full_structuring_pipeline():
      # 1. POST /submit-transaction with structuring scenario
      # 2. Assert response status 200, case_id present
      # 3. GET /case/{id} — assert risk_tier == "RED"
      # 4. POST /case/{id}/run-pipeline
      # 5. GET /case/{id} — assert all 5 agent outputs non-None
      # 6. Assert len(audit_trail) >= 5
      # 7. Assert len(audit.immutable_hash) == 64
      # 8. Assert risk_score >= 0.85
      # 9. POST /case/{id}/approve with analyst_name="TestAnalyst"
      # 10. GET /case/{id} — assert status == "FILED"
  ```

- [ ] Run full test suite and fix any failures:
  ```bash
  pytest tests/ -v 2>&1 | tee test_results.txt
  ```

- [ ] Run mypy and fix type errors:
  ```bash
  python -m mypy agents/ --ignore-missing-imports 2>&1 | tee mypy_results.txt
  ```
  Fix all `error:` lines (ignore `note:` lines). Common fixes: add `Optional[...]`, add return type hints.

- [ ] Write `docs/demo_script.md`
  - Word-for-word script for the 4-minute demo
  - Line by line: "Click the Structuring Demo button. [CLICK] You can see the transaction details populate automatically..."
  - Include exact sentences for each of the 6 screens

- [ ] Write `docs/pitch_deck_content.md`
  - 6 slides: Problem, Solution, Architecture, Demo flow, Business Impact, Team
  - Bullet points per slide — not full paragraphs

- [ ] Final check: `git log --all -p | grep -i "minimax_api_key\|password\|secret"` — confirm zero hardcoded secrets

**Done when:** `pytest tests/ -v` → 0 failures; `python -m mypy agents/` → 0 errors; demo script written

---

## 🏁 End-of-Day Sync — Both Days, 9PM Exactly

```bash
git add .
git commit -m "feat(day1-yourname): what you built today"
git push origin feat/yourname-day1

# Open PR on GitHub → target: develop
# Tag someone to review (Ricky reviews all PRs)
# Merge only after 1 approval
```

**Merge order (Ricky controls this — don't merge out of order):**
```
Day 1: Ashwin → Ricky → Nisarg → Anshul
Day 2: Ricky → Nisarg → Anshul → Ashwin
```

---

## ✅ "Done" Criteria Reference

| Task Type | It's done when... |
|---|---|
| Backend endpoint | `curl` returns expected JSON, no errors |
| Agent task | `pytest tests/unit/test_agentN.py -v` passes |
| Neo4j task | `MATCH (n) RETURN n` in browser shows correct nodes |
| UI task | Page works with real API data, no stuck spinners |
| Integration | Full structuring pipeline runs, all fields populated, `status == FILED` |
