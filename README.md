# 🏦 SAR Platform — AI-Powered Suspicious Activity Report Generator

> An AI-powered, multi-agent system for automating bank Suspicious Activity Reports (SAR) — built for speed, accuracy, and regulatory compliance.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.4-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2.45-purple)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 📖 What This Does

The SAR Platform processes every bank transaction through two intelligent loops:

**🔵 Outer Loop — Prediction Engine**
Every transaction → ML ensemble (XGBoost + SHAP) → scores it **GREEN / AMBER / RED**
RED transactions automatically enter the SAR pipeline.

**🔴 Inner Loop — 6-Agent SAR Pipeline**
```
Agent 1 (Ingestion) → Agent 2 (Risk) → Agent 3 (Narrative) →
Agent 4 (Compliance) → Agent 5 (Audit) → Agent 6 (Human Review)
```
Output: Regulator-ready SAR document + immutable audit trail in Neo4j.

---

## 🧱 Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.11 |
| API | FastAPI 0.115.4 + uvicorn |
| AI Pipeline | LangGraph 0.2.45 + LangChain 0.3.7 |
| LLM | Minimax API (MiniMax-Text-01) |
| Data Models | Pydantic v2 (2.9.2) |
| Graph DB | Neo4j 5.14 Enterprise |
| Relational DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Vector Store | Weaviate 1.24 |
| Streaming | Apache Kafka 3.6 (mocked by simulator) |
| ML | XGBoost + scikit-learn + SHAP |
| Frontend | Streamlit + pyvis |
| Containers | Docker Compose |

---

## 🚀 Quick Start (New Team Member)

### Prerequisites
- Docker & Docker Compose installed
- Python 3.11 installed
- Git configured

### 1. Clone and set up environment

```bash
git clone https://github.com/<your-org>/Sar-platform.git
cd Sar-platform

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env.local
# Edit .env.local and fill in your MINIMAX_API_KEY (get from Ricky)
```

### 3. Start all infrastructure services

```bash
chmod +x infra/start_all.sh
./infra/start_all.sh
```

### 4. Verify services are running

```bash
./infra/check_services.sh
```

### 5. Run the backend

```bash
uvicorn main:app --reload --port 8000
```

### 6. Run the frontend (new terminal)

```bash
streamlit run ui/app.py
```

### 7. Verify everything works

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

---

## 🌐 Service Ports

| Service | URL | Credentials |
|---|---|---|
| FastAPI Backend | http://localhost:8000 | — |
| FastAPI Docs | http://localhost:8000/docs | — |
| Streamlit UI | http://localhost:8501 | — |
| Neo4j Browser | http://localhost:7474 | neo4j / sarplatform123 |
| Neo4j Bolt | bolt://localhost:7687 | — |
| PostgreSQL | localhost:5432 | saruser / sarpass123 / sardb |
| Redis | localhost:6379 | — |
| Kafka | localhost:9092 | — |
| Weaviate | http://localhost:8080 | — |

---

## 📁 Project Structure

```
Sar-platform/
├── main.py                          # FastAPI app + all endpoints
├── agents/
│   ├── shared/schemas.py            # All Pydantic models (source of truth)
│   ├── pipeline.py                  # LangGraph StateGraph wiring
│   ├── agent1_ingestion/node.py     # Agent 1 — Data ingestion & PII masking
│   ├── agent2_risk/node.py          # Agent 2 — Risk scoring (XGBoost + SHAP)
│   ├── agent2_risk/typologies.py    # 4 AML typology definitions
│   ├── agent3_narrative/node.py     # Agent 3 — SAR narrative (Minimax LLM)
│   ├── agent3_narrative/prompts.py  # All LLM prompts
│   ├── agent4_compliance/node.py    # Agent 4 — Compliance checks
│   ├── agent4_compliance/rules.py   # 8 compliance rule functions
│   ├── agent5_audit/node.py         # Agent 5 — Immutable audit trail
│   └── agent6_review/node.py        # Agent 6 — Human approval handler
├── prediction_engine/
│   ├── model.py                     # XGBoost scorer + SHAP explainer
│   └── simulator.py                 # 3 demo scenario generators
├── graph/neo4j/
│   ├── init_schema.py               # Schema init + GraphWriter class
│   ├── graph_api.py                 # Visualization data functions
│   └── cypher_queries/              # All .cypher files
├── ui/
│   ├── app.py                       # Streamlit app (5 pages)
│   ├── api_client.py                # All FastAPI calls from UI
│   └── mock_data.py                 # Mock data for offline dev
├── infra/
│   ├── start_all.sh                 # One command to start everything
│   └── check_services.sh            # Health check all services
├── tests/
│   ├── unit/                        # Unit tests per module
│   └── integration/test_full_pipeline.py
├── docs/
│   ├── demo_script.md               # Word-for-word demo script
│   └── pitch_deck_content.md        # Slide content
├── docker-compose.yml
├── requirements.txt
├── .env.example                     # ← copy to .env.local and fill in
├── MASTER_CONTEXT.md                # Full project context (read first!)
├── AGENTS.md                        # Team workflow rules
├── CONTRIBUTING.md                  # Branch rules and PR process
└── TASKS.md                         # Sprint task assignments
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/submit-transaction` | Score risk, create SAR case |
| `GET` | `/cases` | List all cases |
| `GET` | `/case/{id}` | Get single case |
| `POST` | `/case/{id}/run-pipeline` | Run full 6-agent pipeline |
| `GET` | `/case/{id}/pipeline-status` | Check agent completion |
| `POST` | `/case/{id}/generate-narrative` | Trigger Agent 3 only |
| `POST` | `/case/{id}/approve` | Human approval → FILED |
| `POST` | `/case/{id}/dismiss` | Dismiss case |
| `GET` | `/case/{id}/graph` | Nodes + edges for Neo4j viz |
| `GET` | `/health` | Health check |

---

## 🧪 Running Tests

```bash
# Unit tests
pytest tests/ -v

# Type checking
python -m mypy agents/

# Integration test (requires all services running)
pytest tests/integration/test_full_pipeline.py -v
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Branch naming conventions
- Commit message format
- PR review process
- GitHub branch protection rules

---

## 🏗 Architecture Overview

```
┌─────────────┐    POST /submit-transaction
│  Streamlit  │ ──────────────────────────▶ ┌─────────────┐
│     UI      │                              │   FastAPI   │
│  (port 8501)│ ◀─────────────────────────  │  (port 8000)│
└─────────────┘    SARCase JSON response     └──────┬──────┘
                                                    │
                                        ┌───────────▼──────────┐
                                        │  Prediction Engine    │
                                        │  XGBoost → RED/AMBER  │
                                        └───────────┬──────────┘
                                                    │ if RED
                                        ┌───────────▼──────────┐
                                        │   LangGraph Pipeline  │
                                        │  Agent1→2→3→4→5       │
                                        └───────────┬──────────┘
                                                    │
                                        ┌───────────▼──────────┐
                                        │       Neo4j           │
                                        │  Immutable Audit Trail│
                                        └──────────────────────┘
```

---

## 📋 Team & Module Ownership

See [TASKS.md](TASKS.md) for complete sprint assignments.

| Module | Owner |
|---|---|
| `main.py`, `agents/agent1_ingestion/`, `agents/agent2_risk/`, `prediction_engine/` | **Ricky** (Lead) |
| `agents/agent3_narrative/`, `agents/agent4_compliance/`, `graph/neo4j/` | **Nisarg** |
| `agents/agent5_audit/`, `agents/agent6_review/`, `ui/` | **Anshul** |
| `infra/`, `docker-compose.yml`, `tests/integration/` | **Ashwin** |
| `agents/shared/schemas.py`, `requirements.txt` | **Shared** (coordinate before editing) |

---

## ⚠️ Important Rules

1. **Never commit `.env.local`** — it contains secrets
2. **Never push directly to `main`** — always use PRs
3. **Never force push** any branch
4. **Never edit another person's module** without asking
5. **Shared files** (`schemas.py`) require team agreement before editing
6. **Tag reviewers** on every PR before merging

---

## 📅 Demo Flow (Hackathon)

The demo has **6 screens** for judges:

1. **Submit Transaction** — Structuring Demo preset → RED result
2. **Risk Analysis** — Risk score 0.9+, SHAP bars, typology match
3. **Neo4j Graph** — Colorful account/transaction graph
4. **SAR Narrative** — Streaming token-by-token generation
5. **Audit Trail** — Timeline with immutable SHA256 hash
6. **Human Approval** — st.balloons() confirming FILED status

> 📌 Total demo time: 4 minutes. Practice 3 times before submission.

---

## 🔑 Getting Your API Key

Contact **Ricky** (team lead) directly for:
- `MINIMAX_API_KEY`
- Any AWS credentials needed

Do **not** share keys in Slack, WhatsApp, or commit them to git.
