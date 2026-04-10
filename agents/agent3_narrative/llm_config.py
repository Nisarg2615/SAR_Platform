import os

LLM_CONFIG = {
    "primary": os.getenv("LLM_PRIMARY_PROVIDER", "groq"),
    "fallback_chain": ["groq", "openai", "anthropic", "gemini"],
    "temperature": 0.1,
    "max_tokens": 900,
    "providers": {
        "groq": {
            "model": "llama-3.1-8b-instant",
            "base_url": "https://api.groq.com/openai/v1",
            "api_key_env": "GROQ_API_KEY"
        },
        "openai": {
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key_env": "OPENAI_API_KEY"
        },
        "anthropic": {
            "model": "claude-3-haiku-20240307",
            "base_url": None,
            "api_key_env": "ANTHROPIC_API_KEY"
        },
        "gemini": {
            "model": "gemini-1.5-flash",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            "api_key_env": "GEMINI_API_KEY"
        }
    }
}
