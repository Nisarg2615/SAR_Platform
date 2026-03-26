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

def orchestrator_node(state: SARCase) -> SARCase:
    try:
        directives = {}
        provider_health = {}

        for agent_name in AGENTS_NEEDING_LLM:
            directive = pick_provider(agent_name)
            if directive:
                directives[agent_name] = directive
                provider_health[directive.provider.value] = True

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
                          ", ".join(f"{k}→{v.provider.value}:{v.model}"
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
