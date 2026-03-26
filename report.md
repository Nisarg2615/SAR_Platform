# SAR Platform — Master Project Report

## 1. Project Overview
The Suspicious Activity Report (SAR) Platform is an intelligent, high-throughput Anti-Money Laundering (AML) orchestration system. Its primary goal is to automate the ingestion, risk assessment, narrative generation, compliance checking, and immutable auditing of banking transactions required to file legal Suspicious Transaction Reports (STRs) to financial intelligence units like FIU-IND or FinCEN.

The system is powered by a FastAPI backend, a Next.js (App Router) user interface, and a **LangGraph State Machine** populated by 6 distinct AI "Agents".

---

## 2. The Multi-API Orchestrator
To achieve massive scale without burning through paid API tokens, the platform relies on a custom-built **Multi-API Orchestrator**. 

### How it works:
Instead of hardcoding a single LLM to all tasks, the Orchestrator sits at the very top of the LangGraph pipeline as `orchestrator_node`. Before any transaction begins processing, the Orchestrator evaluates:
1. **API Keys Available**: Reads `.env.local` to determine which free-tier models (Groq, Gemini, Mistral, Cerebras) are active.
2. **Budget Tracking**: Uses an in-memory `BudgetTracker` to tally RPM (Requests Per Minute) and RPD (Requests Per Day) to ensure we never hit a 429 Rate Limit.
3. **Health Cache**: Remembers if an API provider failed recently. If Gemini timeouts, it marks Gemini "unhealthy" for 60 seconds.
4. **Dynamic Routing**: Dispatches a `LLMRoutingDirective` to the 6 downstream agents, specifically assigning a model to a task. If a primary model fails mid-flight, the `agents.llm.client` automatically walks down the `fallback_chain`.

**Providers Used:**
* **Groq** (`llama-3.3-70b-versatile` / `llama3-8b-8192`): Lighting fast reasoning for Risk and Compliance.
* **Google Gemini** (`gemini-2.5-flash`): Heavy narrative generation requiring 1M+ token context windows.
* **Mistral** (`mistral-small-latest`): Immutable Audit summarization.
* **Cerebras** (`llama-3.3-70b`): End-of-line Human Review recommendations and universal fallback due to its massive 14.4k RPD free limit.

---

## 3. The 6-Agent AI Pipeline
The state machine passes a `SARCase` payload sequentially through the following nodes:

* **Agent 1 (Ingestion):** Normalizes the raw transaction. PII redaction rules are applied (dynamically disabled for actual investigators to ensure transparency).
* **Agent 2 (Risk Assessment):** Queries a trained **XGBoost Machine Learning model** to generate a risk probability (0.0 to 1.0) and uses `SHAP` values to understand feature importance. Evaluates transaction velocity and calculates the `RiskTier` (Green/Amber/Red).
* **Agent 3 (Narrative Generation):** Translates structured transaction data into a formal, multi-paragraph legal filing adhering to FIU-IND schema. Driven by deep LLM instruction parsing.
* **Agent 4 (Compliance Engine):** Executes 8 deterministic AML rules (like FinCEN format validation and BSA CTR limits). An LLM evaluates the edge cases to append a compliance summary.
* **Agent 5 (Audit Trail):** Serializes the entire state object, applies a SHA256 cryptographic hash to ensure the case cannot be tampered with, and stores the timeline into a **Neo4j Graph Database**.
* **Agent 6 (Manual Review):** A human-in-the-loop endpoint. The analyst reviews the flagged case in the UI and signs off. An LLM formulates the final analytical sign-off statement.

*(Note: If Agent 2 flags a transaction as **GREEN** (low risk), the pipeline utilizes a fast-path bypass to skip Agent 3 entirely, accelerating the workflow and disabling SAR Report PDF tools in the UI).*

---

## 4. Datasets and ML Features
The platform trains and evaluates cases against two prominent datasets:
1. `Bank_Transaction_Fraud_Detection.csv` (1.5M rows)
2. `suspicious-activity-reports-sar.csv` (Fine-tuned SAR events)

### ML Feature Engineering:
The XGBoost model in Agent 2 targets transactional anomalies using features such as:
* `amount_usd`: Raw and logarithmic transformations.
* `transaction_type_encoded`: Wire transfers versus Cash deposits versus ACH.
* `geography_risk_index`: High-risk cross-border flags.
* `velocity_24h` / `volume_30d`: Aggregated time-series signals pulled from the `TransactionHistoryStore`. 

The system relies on SHAP (SHapley Additive exPlanations) to turn the "black box" ML output into legally admissible evidence, explicitly stating *why* an AI flagged a transaction (e.g., *"This transaction was flagged because the $9,500 cash deposit amount is indicative of structuring"*).
