import os, openai
from agents.llm.config import PROVIDER_CONFIGS

cfg = PROVIDER_CONFIGS["mistral"]

async def call(system_prompt, user_prompt, model, max_tokens=900, temperature=0.1) -> str:
    client = openai.AsyncOpenAI(
        base_url=cfg["base_url"],
        api_key=os.getenv(cfg["api_key_env"]) or (_ for _ in ()).throw(ValueError("MISTRAL_API_KEY not set"))
    )
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system_prompt},
                  {"role":"user",  "content":user_prompt}],
        temperature=temperature, max_tokens=max_tokens,
    )
    return resp.choices[0].message.content
