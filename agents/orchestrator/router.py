import logging
from agents.llm.config import (
    AGENT_PRIMARY_PROVIDER, AGENT_MODEL_SIZE,
    PROVIDER_CONFIGS, FALLBACK_CHAIN
)
from agents.orchestrator.budget_tracker import budget_tracker
from agents.orchestrator.health_cache import health_cache
from agents.shared.schemas import LLMRoutingDirective, ProviderName

def pick_provider(agent_name: str) -> LLMRoutingDirective | None:
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

        cfg = PROVIDER_CONFIGS.get(provider_name, {})
        if not cfg:
            continue
            
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
