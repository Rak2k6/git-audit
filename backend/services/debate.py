"""
services/debate.py
-------------------
Debate Agent — Agent 2 of the GigAudit pipeline.

Extracted from council_service.py and enhanced to receive:
  - evidence[]       : raw_text from each supporting chunk occurrence
  - source_chunks[]  : chunk indices that contained the finding

The Debate agent can now cite specific contract sections ("Supported by
chunks 4 and 5") rather than generating unsupported arguments, which
significantly reduces hallucination in the Advocate/Skeptic debate.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from llm_client import FAST_MODEL, call_llm
from services.models import MergedAuditorResult

logger = logging.getLogger(__name__)


# ── System prompt ─────────────────────────────────────────────────────────────
DEBATE_SYSTEM = """You are a legal debate moderator.

You will receive a list of contract clauses (findings) extracted and merged
by an auditor pipeline. Each finding includes:
  - category      : the type of clause
  - risk_level    : the assessed risk severity
  - excerpt       : a short verbatim quote
  - evidence      : full clause texts from each chunk where this was found
  - source_chunks : which document sections this clause appeared in
  - confidence    : auditor confidence score (0-1)

For EACH finding simulate two perspectives:
  - ADVOCATE  : argues the clause is acceptable / standard practice.
                Reference the evidence and source_chunks in your argument.
  - SKEPTIC   : argues the clause is exploitative / one-sided.
                Reference the evidence and source_chunks in your argument.

Rules:
  - Base arguments ONLY on the provided evidence — do not invent facts.
  - Keep each argument to 1–2 sentences.
  - Be balanced: the Advocate should have at least one reasonable point.
  - When a finding has multiple evidence entries, acknowledge that the clause
    appears in multiple sections of the document.

Return a JSON object with this exact shape:
{
  "debates": [
    {
      "category":  "payment",
      "excerpt":   "...",
      "advocate":  "Advocate argument here.",
      "skeptic":   "Skeptic argument here."
    }
  ]
}
"""


# ── Agent function ────────────────────────────────────────────────────────────

def run_debate(merged: MergedAuditorResult) -> dict[str, Any]:
    """
    Run the Debate agent on the merged and deduplicated findings.

    Receives a MergedAuditorResult (from the Reduce stage) instead of a
    raw auditor dict.  The richer to_debate_dict() representation is passed
    to the LLM so it can cite evidence and source chunk references.

    Returns:
        {'debates': [...]}  — same shape as the original council_service.py
        implementation, preserving backward compatibility with run_judge().
    """
    findings = merged.findings
    if not findings:
        logger.info("[debate] No findings to debate — returning empty debates list.")
        return {"debates": []}

    # Use the evidence-enriched representation for the LLM prompt
    debate_input = merged.to_debate_dict()
    clauses_json = json.dumps(debate_input["clauses"], indent=2)

    logger.info("[debate] Debating %d merged finding(s).", len(findings))

    result: dict[str, Any] = call_llm(
        system_prompt=DEBATE_SYSTEM,
        user_prompt=f"EXTRACTED FINDINGS:\n\n{clauses_json}",
        model=FAST_MODEL,      # speed-optimised; debate is lower-stakes
        temperature=0.3,
    )

    if "debates" not in result or not isinstance(result["debates"], list):
        logger.warning("[debate] LLM returned unexpected shape — using empty debates.")
        result = {"debates": []}

    logger.info("[debate] Generated %d debate argument(s).", len(result["debates"]))
    return result
