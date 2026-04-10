"""
Agent 3 — Narrative Generation
LLM client with 3-tier fallback chain:
    1. Groq API (free — llama-3.1-8b-instant) — if GROQ_API_KEY is set
  2. OpenCode local proxy (MiniMax-Text-2.5) — fallback
  3. Template-based fallback — always works, no LLM needed
"""

from __future__ import annotations

import os
import openai
from agents.agent3_narrative.prompts import SYSTEM_PROMPT, build_user_prompt
from agents.agent3_narrative.fallback import generate_fallback_narrative
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agents.shared.schemas import SARCase

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_BASE_URL = "https://api.groq.com/openai/v1"
_GROQ_MODEL = "llama-3.1-8b-instant"

_OPENCODE_BASE_URL = "http://localhost:4000/v1"
_OPENCODE_MODEL = "minimax/MiniMax-Text-2.5"


async def _call_groq(state: "SARCase") -> str:
    """Call Groq API (free tier — llama-3.1-8b-instant)."""
    client = openai.AsyncOpenAI(base_url=_GROQ_BASE_URL, api_key=_GROQ_API_KEY)
    response = await client.chat.completions.create(
        model=_GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_prompt(state)},
        ],
        temperature=0.1,
        max_tokens=900,
        timeout=20,
    )
    return (response.choices[0].message.content or "").strip()


async def _call_opencode(state: "SARCase") -> str:
    """Call OpenCode local LLM proxy (MiniMax-Text-2.5)."""
    client = openai.AsyncOpenAI(base_url=_OPENCODE_BASE_URL, api_key="opencode-free")
    response = await client.chat.completions.create(
        model=_OPENCODE_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_user_prompt(state)},
        ],
        temperature=0.1,
        max_tokens=800,
        timeout=15,
    )
    return (response.choices[0].message.content or "").strip()


async def generate_narrative(state: "SARCase") -> str:
    """
    Generate a SAR narrative with 3-tier fallback:
      1. Groq (free cloud LLM) if GROQ_API_KEY is set
      2. OpenCode local proxy
      3. Template fallback — always succeeds
    Returns a string with section markers suitable for FIU-IND STR.
    """
    # Tier 1: Groq (free — add GROQ_API_KEY to .env.local)
    if _GROQ_API_KEY:
        try:
            result = await _call_groq(state)
            if len(result) >= 100:
                return result
        except Exception as e:
            print(f"[Agent3] Groq failed: {e} — trying OpenCode proxy")

    # Tier 2: OpenCode local proxy
    try:
        result = await _call_opencode(state)
        if len(result) >= 100:
            return result
    except Exception as e:
        print(f"[Agent3] OpenCode proxy failed: {e} — using template fallback")

    # Tier 3: Template fallback — guaranteed to work
    return generate_fallback_narrative(state)
