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
