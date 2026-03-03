"""
llm_client.py
-------------
Thin wrapper around the Groq SDK.
All agents in the council use this module to call LLMs.
"""

import json
import os
import re
from typing import Any

from groq import Groq

# ── Model aliases used across the codebase ──────────────────────────────────
LARGE_MODEL = "llama-3.3-70b-versatile"   # Auditor & Judge
FAST_MODEL  = "llama-3.1-8b-instant"       # Debate


def _get_client() -> Groq:
    """Return a Groq client.  API key is read from the environment."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY environment variable is not set. "
            "Export it before starting the server."
        )
    return Groq(api_key=api_key)


def call_llm(
    system_prompt: str,
    user_prompt: str,
    model: str = LARGE_MODEL,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """
    Call the Groq API and return a parsed JSON dict.

    The function:
    1. Asks the model for a JSON-only response (via system prompt guidance).
    2. Tries to parse it directly.
    3. Falls back to a regex extraction of the first {...} block if the
       model wraps JSON in markdown code fences.
    4. Returns an empty dict on any unexpected parse failure instead of raising.
    """
    client = _get_client()

    # Append strict JSON instruction to every system prompt
    full_system = (
        system_prompt.rstrip()
        + "\n\nIMPORTANT: Respond with ONLY valid JSON. "
          "Do not include markdown, code fences, or any text outside the JSON object."
    )

    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": full_system},
                {"role": "user",   "content": user_prompt},
            ],
        )
    except Exception as exc:
        print(f"[llm_client] Groq API error: {exc}")
        return {}

    raw = response.choices[0].message.content or ""

    # ── Attempt 1: direct parse ──────────────────────────────────────────────
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # ── Attempt 2: extract first {...} block (handles markdown fences) ────────
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # ── Fallback: log and return empty dict ──────────────────────────────────
    print(f"[llm_client] Failed to parse JSON from model output:\n{raw[:500]}")
    return {}
