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
        "rpd_limit": 1000,
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
    },
    "cerebras": {
        "base_url":    "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "models": {
            "large": "llama-3.3-70b",
            "small": "llama3.1-8b",
        },
        "rpm_limit": 30,
        "rpd_limit": 14400,
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
    "agent6_review":     "cerebras",    # Replaces OpenRouter as primary
}

# Per-agent model size preference
AGENT_MODEL_SIZE = {
    "agent2_risk":       "large",
    "agent3_narrative":  "large",
    "agent4_compliance": "small",
    "agent5_audit":      "large",
    "agent6_review":     "large",
}
