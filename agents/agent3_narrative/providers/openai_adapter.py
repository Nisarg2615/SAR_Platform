import openai, os
from agents.agent3_narrative.llm_config import LLM_CONFIG

async def call_openai(system_prompt: str, user_prompt: str) -> str:
    cfg = LLM_CONFIG["providers"]["openai"]
    key = os.getenv(cfg["api_key_env"], "")
    if not key:
        raise ValueError("OPENAI_API_KEY not set")
    client = openai.AsyncOpenAI(base_url=cfg["base_url"], api_key=key)
    resp = await client.chat.completions.create(
        model=cfg["model"],
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=LLM_CONFIG["temperature"],
        max_tokens=LLM_CONFIG["max_tokens"],
        timeout=20,
    )
    return resp.choices[0].message.content or ""
