# Multi-API Orchestrator — Implementation Plan
# SAR Platform · Agent-to-Provider Routing Architecture
# For AI agent execution: one subtask at a time
# Generated: March 26 2026

---

## WHAT THIS PLAN BUILDS

A Master Orchestrator Agent that sits at the top of the LangGraph pipeline.
It controls which free API provider + model each of the 6 downstream agents uses.
It manages token budgets, tracks provider health, enforces a fallback chain,
and logs every routing decision into the immutable audit trail.

No agent changes its own LLM call. Agents only call the unified LLM client
(agents/llm/client.py). The orchestrator sets the routing config in SARCase state
before each agent runs. This is fully modular — one file per provider adapter.

---

## FREE API PROVIDERS — SELECTED AND ASSIGNED

All providers below are 100% free (no credit card for basic tier). All expose
an OpenAI-compatible endpoint so all adapters use the same interface.

| Provider    | Model(s)                        | Free Limit           | Assigned Agent(s)      |
|-------------|--------------------------------|----------------------|------------------------|
| Groq        | llama-3.3-70b-versatile        | 30 RPM, 1K RPD       | Agent 2 (primary)      |
| Groq        | llama3-8b-8192 (existing)      | 14.4K RPD (8B)       | Agent 4 (primary)      |
| Google Gemini | gemini-2.5-flash             | 15 RPM, 1K RPD       | Agent 3 (primary)      |
| Mistral     | mistral-small-latest           | 1 req/s, 1B tok/mo   | Agent 5 (primary)      |
| Cerebras    | llama-3.3-70b                  | 30 RPM, 14.4K RPD    | Universal fallback 2nd |

Fallback chain (orchestrator enforces):
  Primary → Groq → Cerebras → Mistral → template fallback (no LLM)

---

## FILE MAP — ALL NEW FILES THIS PLAN CREATES

```
agents/orchestrator/
    __init__.py
    node.py             ← Master Orchestrator Agent (LangGraph node)
    router.py           ← routing logic: which provider per agent
    budget_tracker.py   ← token budget + rate limit state per session
    health_cache.py     ← in-memory provider health (last N calls)

agents/llm/
    __init__.py
    client.py           ← unified async LLM caller (used by all agents)
    config.py           ← all provider configs in one dict
    providers/
        __init__.py
        groq.py
        gemini.py
        mistral.py
        cerebras.py

agents/shared/schemas.py    ← ADD: LLMRoutingDirective, OrchestratorDecision fields
```

---

## SUBTASK O-1 — Add LLMRoutingDirective to schemas.py

**File:** `agents/shared/schemas.py`
**Owner:** All team agrees before editing

**What to add:**

```python
class ProviderName(str, Enum):
    GROQ       = "groq"
    GEMINI     = "gemini"
    MISTRAL    = "mistral"
    CEREBRAS   = "cerebras"
    FALLBACK   = "template_fallback"

class LLMRoutingDirective(BaseModel):
    agent_name: str                        # e.g. "agent3_narrative"
    provider: ProviderName
    model: str                             # e.g. "gemini-2.5-flash"
    max_tokens: int = 900
    temperature: float = 0.1
    reason: str = ""                       # why this provider was chosen
    fallback_chain: list[ProviderName] = []

class OrchestratorDecision(BaseModel):
    decided_at: str                        # ISO timestamp
    directives: dict[str, LLMRoutingDirective]  # keyed by agent_name
    total_budget_tokens: int = 10000
    tokens_used: int = 0
    provider_health: dict[str, bool] = {}  # provider_name → is_healthy
```

**Also add to SARCase:**
```python
orchestrator_decision: Optional[OrchestratorDecision] = None
```

**DONE CHECK:** `python -c "from agents.shared.schemas import LLMRoutingDirective, OrchestratorDecision; print('OK')"` — no errors.

---

## SUBTASK O-2 — Create Provider Config

**File to create:** `agents/llm/config.py`

```python
import os

PROVIDER_CONFIGS = {
    "groq": {
        "base_url":    "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "models": {
            "large": "llama-3.3-70b-versatile",
            "small": "llama3-8b-8192",
        },
        "rpm_limit": 30,
        "rpd_limit": 1000,   # 14400 for 8B model
    },
    "gemini": {
        "base_url":    "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "models": {
            "large": "gemini-2.5-flash",
        },
        "rpm_limit": 15,
        "rpd_limit": 1000,
    },
    "mistral": {
        "base_url":    "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "models": {
            "large": "mistral-small-latest",
            "small": "open-mistral-7b",
        },
        "rpm_limit": 60,
        "rpd_limit": 500,
    },        "rpm_limit": 20,
        "rpd_limit": 50,
    },
    "cerebras": {
        "base_url":    "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "models": {
            "large": "llama-3.3-70b",
            "small": "llama3.1-8b",
        },
        "rpm_limit": 30,
        "rpd_limit": 14400,  # highest free RPD of all providers
    },
}

# Global fallback chain — orchestrator tries these in order on primary failure
FALLBACK_CHAIN = ["groq", "cerebras", "mistral"]

# Per-agent primary provider assignment
AGENT_PRIMARY_PROVIDER = {
    "agent1_ingestion":  None,          # No LLM needed
    "agent2_risk":       "groq",        # Fast, 70B for risk signals
    "agent3_narrative":  "gemini",      # Best reasoning, 1M context
    "agent4_compliance": "groq",        # Structured JSON, 8B is enough
    "agent5_audit":      "mistral",     # Huge monthly token budget
    "agent6_review":     "cerebras",  # DeepSeek R1 free, reasoning model
}

# Per-agent model size preference
AGENT_MODEL_SIZE = {
    "agent2_risk":       "large",
    "agent3_narrative":  "large",
    "agent4_compliance": "small",
    "agent5_audit":      "large",
    "agent6_review":     "large",
}
```

**Add to .env.local (document, never commit keys):**
```
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=AIza...
MISTRAL_API_KEY=...
CEREBRAS_API_KEY=csk-...
```

**DONE CHECK:** `python -c "from agents.llm.config import PROVIDER_CONFIGS, AGENT_PRIMARY_PROVIDER; print(list(PROVIDER_CONFIGS.keys()))"` prints all 5 providers.

---

## SUBTASK O-3 — Create Provider Adapters (5 files)

**Directory:** `agents/llm/providers/`
**All adapters share the same function signature:**
```python
async def call(system_prompt: str, user_prompt: str,
               model: str, max_tokens: int, temperature: float) -> str
```

### O-3a: `agents/llm/providers/groq.py`
```python
import os, openai
from agents.llm.config import PROVIDER_CONFIGS

cfg = PROVIDER_CONFIGS["groq"]

async def call(system_prompt, user_prompt, model, max_tokens=900, temperature=0.1) -> str:
    client = openai.AsyncOpenAI(
        base_url=cfg["base_url"],
        api_key=os.getenv(cfg["api_key_env"]) or (_ for _ in ()).throw(ValueError("GROQ_API_KEY not set"))
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system_prompt},
                  {"role":"user",  "content":user_prompt}],
        temperature=temperature, max_tokens=max_tokens,
    )
    return resp.choices[0].message.content
```

### O-3b: `agents/llm/providers/gemini.py`
Same structure as groq.py. Uses:
- `base_url`: `https://generativelanguage.googleapis.com/v1beta/openai/`
- `api_key_env`: `GEMINI_API_KEY`
- Uses `openai.AsyncOpenAI` (Gemini exposes OpenAI-compatible endpoint)

### O-3c: `agents/llm/providers/mistral.py`
Same structure. Uses:
- `base_url`: `https://api.mistral.ai/v1`
- `api_key_env`: `MISTRAL_API_KEY`

### O-3d: `agents/llm/providers/cerebras.py`
Same structure as groq.py. Uses:
- `base_url`: `https://api.cerebras.ai/v1`
- `api_key_env`: `CEREBRAS_API_KEY`

**DONE CHECK for all 5:** `python -c "from agents.llm.providers import groq, gemini, mistral, cerebras; print('all adapters OK')"` — no import errors.

---

## SUBTASK O-4 — Create the Unified LLM Client

**File:** `agents/llm/client.py`

This is the ONLY file any agent should ever call for LLM inference.
No agent imports a provider directly.

```python
import logging, os
from agents.llm.config import PROVIDER_CONFIGS, FALLBACK_CHAIN
from agents.llm.providers import groq, gemini, mistral, cerebras
from agents.agent3_narrative.fallback import generate_fallback_narrative

ADAPTER_MAP = {
    "groq":       groq,
    "gemini":     gemini,
    "mistral":    mistral,
    
    "cerebras":   cerebras,
}

async def llm_call(
    system_prompt: str,
    user_prompt:   str,
    provider:      str,           # from LLMRoutingDirective
    model:         str,           # from LLMRoutingDirective
    max_tokens:    int   = 900,
    temperature:   float = 0.1,
    fallback_chain: list[str] = None,
) -> tuple[str, str]:
    """
    Returns (content, provider_used).
    Tries primary provider first, then each in fallback_chain.
    Never raises — always returns a string.
    """
    if fallback_chain is None:
        fallback_chain = FALLBACK_CHAIN

    providers_to_try = [provider] + [p for p in fallback_chain if p != provider]

    for p_name in providers_to_try:
        adapter = ADAPTER_MAP.get(p_name)
        if adapter is None:
            continue
        # Check if API key is set — skip silently if not
        cfg = PROVIDER_CONFIGS.get(p_name, {})
        api_key = os.getenv(cfg.get("api_key_env", ""), "")
        if not api_key:
            logging.warning(f"[LLM] Skipping {p_name}: no API key configured")
            continue
        try:
            result = await adapter.call(
                system_prompt, user_prompt, model, max_tokens, temperature
            )
            if result and len(result.strip()) > 30:
                logging.info(f"[LLM] Success: provider={p_name} model={model}")
                return result, p_name
        except Exception as e:
            logging.warning(f"[LLM] {p_name} failed: {e}")
            continue

    logging.error("[LLM] All providers failed — returning empty string for fallback")
    return "", "template_fallback"
```

**Key design rules:**
- Returns a tuple `(content, provider_used)` so agents can log which provider was actually used.
- Checks for API key existence before calling — silently skips unconfigured providers.
- Never raises. If all fail, returns `("", "template_fallback")`.

**DONE CHECK:** `python -c "from agents.llm.client import llm_call; import asyncio; asyncio.run(llm_call('sys','user','groq','llama3-8b-8192'))"` — either returns a real response or `("", "template_fallback")`. Does NOT raise an exception either way.

---

## SUBTASK O-5 — Create the Budget Tracker

**File:** `agents/orchestrator/budget_tracker.py`

Tracks token usage per provider per session. Prevents agents from blowing a
provider's daily limit mid-batch when running 160 transactions.

```python
from dataclasses import dataclass, field
from agents.llm.config import PROVIDER_CONFIGS

@dataclass
class ProviderBudget:
    rpm_used:  int = 0    # requests this minute
    rpd_used:  int = 0    # requests today
    rpm_limit: int = 30
    rpd_limit: int = 1000

    def can_use(self) -> bool:
        return self.rpm_used < self.rpm_limit and self.rpd_used < self.rpd_limit

    def record_use(self):
        self.rpm_used += 1
        self.rpd_used += 1

class BudgetTracker:
    def __init__(self):
        self._budgets: dict[str, ProviderBudget] = {
            name: ProviderBudget(
                rpm_limit=cfg["rpm_limit"],
                rpd_limit=cfg["rpd_limit"]
            )
            for name, cfg in PROVIDER_CONFIGS.items()
        }

    def can_use(self, provider: str) -> bool:
        return self._budgets.get(provider, ProviderBudget()).can_use()

    def record_use(self, provider: str):
        if provider in self._budgets:
            self._budgets[provider].record_use()

    def get_status(self) -> dict:
        return {
            name: {"rpm_used": b.rpm_used, "rpd_used": b.rpd_used,
                   "can_use": b.can_use()}
            for name, b in self._budgets.items()
        }

# Module-level singleton — shared across the whole process
budget_tracker = BudgetTracker()
```

**DONE CHECK:** `python -c "from agents.orchestrator.budget_tracker import budget_tracker; budget_tracker.record_use('groq'); print(budget_tracker.get_status()['groq'])"` shows `rpm_used=1`.

---

## SUBTASK O-6 — Create the Provider Health Cache

**File:** `agents/orchestrator/health_cache.py`

Tracks the last N call results per provider. If a provider fails 2 consecutive
times, it's marked unhealthy and skipped for the next 60 seconds.

```python
import time
from collections import deque

class ProviderHealth:
    def __init__(self, window: int = 5, failure_threshold: int = 2, cooldown_s: int = 60):
        self._results: deque = deque(maxlen=window)    # True=success, False=fail
        self._fail_threshold = failure_threshold
        self._cooldown_s = cooldown_s
        self._unhealthy_until: float = 0.0

    def record(self, success: bool):
        self._results.append(success)
        recent_failures = sum(1 for r in list(self._results)[-self._fail_threshold:] if not r)
        if recent_failures >= self._fail_threshold:
            self._unhealthy_until = time.time() + self._cooldown_s

    def is_healthy(self) -> bool:
        return time.time() >= self._unhealthy_until

class HealthCache:
    def __init__(self):
        self._providers: dict[str, ProviderHealth] = {}

    def _get(self, provider: str) -> ProviderHealth:
        if provider not in self._providers:
            self._providers[provider] = ProviderHealth()
        return self._providers[provider]

    def record_success(self, provider: str):
        self._get(provider).record(True)

    def record_failure(self, provider: str):
        self._get(provider).record(False)

    def is_healthy(self, provider: str) -> bool:
        return self._get(provider).is_healthy()

health_cache = HealthCache()
```

**DONE CHECK:** Import works. Simulate 2 failures on "gemini" — `health_cache.is_healthy("gemini")` returns False for 60s.

---

## SUBTASK O-7 — Create the Router Logic

**File:** `agents/orchestrator/router.py`

Given an agent name and current state (budget + health), returns the best
available `LLMRoutingDirective`.

```python
import logging
from agents.llm.config import (
    AGENT_PRIMARY_PROVIDER, AGENT_MODEL_SIZE,
    PROVIDER_CONFIGS, FALLBACK_CHAIN
)
from agents.orchestrator.budget_tracker import budget_tracker
from agents.orchestrator.health_cache import health_cache
from agents.shared.schemas import LLMRoutingDirective, ProviderName

def pick_provider(agent_name: str) -> LLMRoutingDirective:
    """
    Returns the best available LLMRoutingDirective for this agent.
    Priority: primary → fallback chain (skip unhealthy / over-budget).
    """
    primary = AGENT_PRIMARY_PROVIDER.get(agent_name)
    if primary is None:
        return None  # Agent 1 needs no LLM

    size = AGENT_MODEL_SIZE.get(agent_name, "small")
    chain = [primary] + [p for p in FALLBACK_CHAIN if p != primary]

    for provider_name in chain:
        if not health_cache.is_healthy(provider_name):
            logging.info(f"[Router] Skipping {provider_name} — unhealthy")
            continue
        if not budget_tracker.can_use(provider_name):
            logging.info(f"[Router] Skipping {provider_name} — budget exhausted")
            continue

        cfg = PROVIDER_CONFIGS[provider_name]
        model = cfg["models"].get(size) or cfg["models"].get("small") or list(cfg["models"].values())[0]

        reason = "primary" if provider_name == primary else f"fallback (primary={primary} unavailable)"

        return LLMRoutingDirective(
            agent_name=agent_name,
            provider=ProviderName(provider_name),
            model=model,
            max_tokens=900,
            temperature=0.1,
            reason=reason,
            fallback_chain=[ProviderName(p) for p in chain if p != provider_name],
        )

    # All providers failed — return template fallback directive
    logging.error(f"[Router] No provider available for {agent_name} — using template fallback")
    return LLMRoutingDirective(
        agent_name=agent_name,
        provider=ProviderName.FALLBACK,
        model="none",
        reason="all providers exhausted or unhealthy",
    )
```

**DONE CHECK:** `python -c "from agents.orchestrator.router import pick_provider; print(pick_provider('agent3_narrative'))"` prints a directive with `provider='gemini'` (assuming key is set) or a fallback if not.

---

## SUBTASK O-8 — Create the Master Orchestrator Agent Node

**File:** `agents/orchestrator/node.py`

This is the new LangGraph node inserted at the very start of the pipeline,
before Agent 1. It sets `state.orchestrator_decision` and from that point
every downstream agent reads its routing directive from state.

```python
import logging
from datetime import datetime
from agents.shared.schemas import SARCase, OrchestratorDecision
from agents.orchestrator.router import pick_provider
from agents.orchestrator.budget_tracker import budget_tracker

AGENTS_NEEDING_LLM = [
    "agent2_risk",
    "agent3_narrative",
    "agent4_compliance",
    "agent5_audit",
    "agent6_review",
]

async def orchestrator_node(state: SARCase) -> SARCase:
    try:
        directives = {}
        provider_health = {}

        for agent_name in AGENTS_NEEDING_LLM:
            directive = pick_provider(agent_name)
            if directive:
                directives[agent_name] = directive
                provider_health[directive.provider] = True

        state.orchestrator_decision = OrchestratorDecision(
            decided_at=datetime.now().isoformat(),
            directives=directives,
            total_budget_tokens=10000,
            tokens_used=0,
            provider_health=provider_health,
        )

        state.audit_trail.append({
            "agent":      "Orchestrator",
            "action":     f"Routing plan created for {len(directives)} agents. "
                          f"Assignments: " +
                          ", ".join(f"{k}→{v.provider}:{v.model}"
                                    for k, v in directives.items()),
            "confidence": 1.0,
            "timestamp":  datetime.now().isoformat(),
        })

        logging.info(f"[Orchestrator] Routing plan: {directives}")
        return state

    except Exception as e:
        state.error_log.append({
            "agent":     "Orchestrator",
            "error":     str(e),
            "timestamp": datetime.now().isoformat(),
        })
        return state   # NEVER crash — agents will use their own defaults
```

**DONE CHECK:** Inject orchestrator_node into the pipeline (Task O-9 below) and run one test case. Confirm `state.audit_trail[0]["agent"] == "Orchestrator"` and all directives are present.

---

## SUBTASK O-9 — Wire Orchestrator into LangGraph Pipeline

**File:** `agents/pipeline.py`
**Owner:** Ricky — coordinate before editing

**Current graph (simplified):**
```
START → agent1_ingest → validate_gate_1 → agent2_assess_risk → ...
```

**New graph:**
```
START → orchestrator_node → agent1_ingest → validate_gate_1 → agent2_assess_risk → ...
```

**Instructions:**
1. Import `orchestrator_node` from `agents.orchestrator.node`.
2. Add `graph.add_node("orchestrator", orchestrator_node)` before all other nodes.
3. Change the first edge: `graph.add_edge(START, "orchestrator")`.
4. Add: `graph.add_edge("orchestrator", "agent1_ingest")`.
5. All existing edges remain unchanged.

**DONE CHECK:** `curl -X POST http://localhost:8000/submit-transaction -d '{"transaction_id":"TXN-TEST",...}'`
Response JSON must include `orchestrator_decision` field with `directives` populated.

---

## SUBTASK O-10 — Migrate Agents to Use Unified LLM Client

Each agent that currently calls its own LLM (Agents 2, 3, 4, 5, 6) must be
updated to call `agents.llm.client.llm_call` instead of its private client.

### O-10a: Update Agent 3 (Narrative) — Nisarg

**File:** `agents/agent3_narrative/node.py`

Replace:
```python
from agents.agent3_narrative.minimax_client import generate_narrative
narrative_text = await generate_narrative(state)
```

With:
```python
from agents.llm.client import llm_call
from agents.agent3_narrative.prompts import SYSTEM_PROMPT, build_user_prompt
from agents.agent3_narrative.fallback import generate_fallback_narrative

directive = state.orchestrator_decision.directives.get("agent3_narrative")
provider  = directive.provider if directive else "groq"
model     = directive.model    if directive else "llama3-8b-8192"
fallback_chain = [p.value for p in directive.fallback_chain] if directive else []

narrative_text, provider_used = await llm_call(
    system_prompt=SYSTEM_PROMPT,
    user_prompt=build_user_prompt(state),
    provider=provider,
    model=model,
    fallback_chain=fallback_chain,
)
if not narrative_text:
    narrative_text = generate_fallback_narrative(state)
    provider_used  = "template_fallback"
```

Then record `provider_used` in the audit_trail entry for Agent 3.

### O-10b: Update Agent 2 (Risk) — Ricky

**File:** `agents/agent2_risk/node.py`

Same pattern as Agent 3. Agent 2 uses LLM only for explaining risk signals
in natural language (the SHAP explanation text). If Agent 2 currently has
no LLM call, this subtask can be skipped — add the LLM call only if needed
for the signal explanation feature.

### O-10c: Update Agent 4 (Compliance) — Nisarg

**File:** `agents/agent4_compliance/node.py`

Same pattern. Directive is `state.orchestrator_decision.directives["agent4_compliance"]`.
Agent 4 uses `llm_call` to get structured JSON compliance flags. If the call
returns empty string, use the existing rule-based fallback.

### O-10d: Update Agent 5 (Audit) — Nisarg

**File:** `agents/agent5_audit/node.py`

Same pattern. Directive is `state.orchestrator_decision.directives["agent5_audit"]`.
Agent 5 uses LLM to write the human-readable audit summary paragraph.

### O-10e: Update Agent 6 (Review) — Anshul

**File:** `agents/agent6_review/node.py`

Same pattern. Directive is `state.orchestrator_decision.directives["agent6_review"]`.
Agent 6 uses LLM for the final approval recommendation text.

**DONE CHECK for all O-10 subtasks:**
For each updated agent, run the full pipeline on a test RED transaction and confirm:
- The audit_trail entry for that agent includes a `provider_used` field.
- The pipeline completes without errors even if you temporarily remove a provider's key.

---

## SUBTASK O-11 — Record Provider Outcomes Back to Health Cache

**File:** `agents/llm/client.py` (extend the existing `llm_call` function)

After each `adapter.call()` attempt, record the result to `health_cache`:

```python
from agents.orchestrator.health_cache import health_cache
from agents.orchestrator.budget_tracker import budget_tracker

# Inside the for loop, after the try block:
try:
    result = await adapter.call(...)
    if result and len(result.strip()) > 30:
        health_cache.record_success(p_name)
        budget_tracker.record_use(p_name)
        return result, p_name
    else:
        health_cache.record_failure(p_name)
except Exception as e:
    health_cache.record_failure(p_name)
    budget_tracker.record_use(p_name)   # count even failed calls against budget
    logging.warning(f"[LLM] {p_name} failed: {e}")
    continue
```

**DONE CHECK:** Deliberately make Gemini fail (wrong key) and run 3 transactions.
Confirm that after the 2nd consecutive failure, `health_cache.is_healthy("gemini")` returns False
and Agent 3 automatically routes to the Groq fallback on the 3rd transaction.

---

## SUBTASK O-12 — Add Orchestrator Status to /health Endpoint

**File:** `main.py`
**Owner:** Ricky

Extend `GET /health` to return:
```json
{
  "status": "ok",
  "orchestrator": {
    "providers_configured": {
      "groq":       true,
      "gemini":     true,
      "mistral":    false,
      "openrouter": false,
      "cerebras":   false
    },
    "provider_health": {
      "groq":       true,
      "gemini":     false,
      "mistral":    true,
      "openrouter": true,
      "cerebras":   true
    },
    "budget_status": {
      "groq":    { "rpm_used": 3, "rpd_used": 12, "can_use": true },
      "gemini":  { "rpm_used": 0, "rpd_used": 0,  "can_use": true }
    },
    "agent_routing": {
      "agent2_risk":       "groq:llama-3.3-70b-versatile",
      "agent3_narrative":  "gemini:gemini-2.5-flash",
      "agent4_compliance": "groq:llama3-8b-8192",
      "agent5_audit":      "mistral:mistral-small-latest",
      "agent6_review":     "cerebras:llama-3.3-70b"
    }
  }
}
```

Import `health_cache` from `agents.orchestrator.health_cache`
and `budget_tracker` from `agents.orchestrator.budget_tracker`.
`providers_configured` is True if the env var for that provider is non-empty.
Never expose the actual key values.

**DONE CHECK:** `curl http://localhost:8000/health` returns the extended JSON.

---

## SUBTASK O-13 — Add Provider Info to UI (SAR Review Page)

**File:** `ui/app.py`
**Owner:** Anshul

In the audit trail section of the SAR Review page, after the existing
agent decision timeline, add a small "LLM Routing" info card:

1. Call `GET /health` and extract `orchestrator.agent_routing`.
2. Display a compact table:
   - Columns: Agent | Provider | Model | Status
   - Color code status: green for configured + healthy, amber for fallback, red for unavailable.
3. Show below the audit trail, collapsed in an `st.expander("🔀 LLM Provider Routing")`.

**DONE CHECK:** Open SAR Review for a completed case. Expand "LLM Provider Routing".
Confirm each agent shows its assigned provider and the health status is accurate.

---

## FINAL EXECUTION ORDER

Run subtasks in this exact order. Do not skip ahead.

```
[ ] O-1   schemas.py: add LLMRoutingDirective + OrchestratorDecision + sar field
[ ] O-2   agents/llm/config.py: all 5 provider configs + agent assignments
[ ] O-3a  agents/llm/providers/groq.py
[ ] O-3b  agents/llm/providers/gemini.py
[ ] O-3c  agents/llm/providers/mistral.py
[ ] O-3d  agents/llm/providers/
[ ] O-3d  agents/llm/providers/cerebras.py
[ ] O-4   agents/llm/client.py: unified llm_call()
[ ] O-5   agents/orchestrator/budget_tracker.py
[ ] O-6   agents/orchestrator/health_cache.py
[ ] O-7   agents/orchestrator/router.py
[ ] O-8   agents/orchestrator/node.py: orchestrator LangGraph node
[ ] O-9   agents/pipeline.py: wire orchestrator as first node
[ ] O-10a agents/agent3_narrative/node.py: migrate to llm_call
[ ] O-10b agents/agent2_risk/node.py: migrate if LLM is used
[ ] O-10c agents/agent4_compliance/node.py: migrate to llm_call
[ ] O-10d agents/agent5_audit/node.py: migrate to llm_call
[ ] O-10e agents/agent6_review/node.py: migrate to llm_call
[ ] O-11  agents/llm/client.py: add health_cache + budget_tracker recording
[ ] O-12  main.py: extend /health with orchestrator status
[ ] O-13  ui/app.py: add LLM Provider Routing expander

INTEGRATION TEST:
[ ] Run full pipeline on 5 test transactions
[ ] Confirm audit_trail[0].agent == "Orchestrator" for every case
[ ] Confirm each agent's audit entry has provider_used field
[ ] Remove GEMINI_API_KEY from .env.local — confirm Agent 3 routes to Groq
[ ] Remove GROQ_API_KEY — confirm template fallback activates, pipeline still completes
[ ] curl /health — confirm orchestrator section is present and accurate
```

---

## IMPORTANT RULES FOR THE AI AGENT IMPLEMENTING THIS

1. Do exactly ONE subtask per session. Commit after every subtask.
2. Commit format: `feat(orchestratorO-N): description`
3. Never touch a file owned by another person without checking the owner list.
4. schemas.py edits require all 4 team members to agree first.
5. Never hardcode API keys. Read exclusively from env vars via `os.getenv()`.
6. Never let any single agent failure crash the pipeline. Every LLM call is wrapped in try/except.
7. The fallback template in `agents/agent3_narrative/fallback.py` is the last resort.
   It must always produce a valid SARNarrative — it exists precisely for when all LLMs are down.
8. The `llm_call()` return value is always `(str, str)`. Never returns `None`. Never raises.
9. The orchestrator does NOT call any LLM itself. It only decides routing. It is pure Python logic.
10. After O-9 (pipeline wiring), run `pytest tests/integration/test_full_pipeline.py` before continuing.

---

*End of Plan — SAR Platform Multi-API Orchestrator*
*March 26 2026*
