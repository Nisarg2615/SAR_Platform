import logging, os
from agents.llm.config import PROVIDER_CONFIGS, FALLBACK_CHAIN
from agents.llm.providers import groq, gemini, mistral, cerebras

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
    """
    from agents.orchestrator.health_cache import health_cache
    from agents.orchestrator.budget_tracker import budget_tracker

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
                health_cache.record_success(p_name)
                budget_tracker.record_use(p_name)
                logging.info(f"[LLM] Success: provider={p_name} model={model}")
                return result, p_name
            else:
                health_cache.record_failure(p_name)
        except Exception as e:
            health_cache.record_failure(p_name)
            budget_tracker.record_use(p_name)
            logging.warning(f"[LLM] {p_name} failed: {e}")
            continue

    logging.error("[LLM] All providers failed — returning empty string for fallback")
    return "", "template_fallback"
