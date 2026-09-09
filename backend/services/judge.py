"""
services/judge.py
------------------
Judge Agent — Agent 3 of the GigAudit pipeline.

Extracted from council_service.py with no changes to the core logic or the
output shape.  The Judge receives the merged auditor findings and the debate
log, then produces the final scores, verdict, and per-clause recommendations.

The _build_fallback_judgment() function is preserved verbatim and used when
the LLM returns malformed JSON.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from llm_client import LARGE_MODEL, call_llm
from services.models import MergedAuditorResult

logger = logging.getLogger(__name__)

# ── Category definitions shared across agents ─────────────────────────────────
CATEGORIES = ["payment", "termination", "non_compete", "ip", "dispute", "compensation"]


# ── System prompt ─────────────────────────────────────────────────────────────
JUDGE_SYSTEM = f"""You are a senior labor-law judge with deep expertise in gig economy contracts.

You will receive:
  1. The findings extracted and merged by an Auditor pipeline.
  2. A debate log (Advocate vs. Skeptic arguments) for each finding.

Your task:
  A. Calculate an OVERALL FAIRNESS SCORE (0–100):
       100 = perfectly fair, 0 = completely predatory
       Deduct points based on risk severity:
         critical → −22,  high → −14,  medium → −8,  low → −2
       Floor: 10

  B. Calculate a CATEGORY SCORE (0–100) for each of these six categories:
       {CATEGORIES}
     • Start each at 85 (optimistic default for categories with no issues).
     • For categories WITH clauses, score based on the worst clause:
         critical → 10–25,  high → 30–45,  medium → 50–65,  low → 70–84

  C. Determine a VERDICT:
       "approved"             → overall_score ≥ 70
       "needs_renegotiation"  → 40 ≤ overall_score < 70
       "unfair"               → overall_score < 40

  D. For each extracted finding produce a RISKY CLAUSE object:
       - category    : same as the auditor assigned
       - risk_level  : same as the auditor assigned
       - explanation : plain English, 2–3 sentences, why this harms the worker
       - suggestion  : concrete negotiation tactic, 1–2 sentences

Return a JSON object with EXACTLY this shape:
{{
  "overall_score": 42,
  "category_scores": {{
    "payment":      15,
    "termination":  35,
    "non_compete":  20,
    "ip":           12,
    "dispute":      18,
    "compensation": 75
  }},
  "verdict": "unfair",
  "risky_clauses": [
    {{
      "category":    "payment",
      "risk_level":  "critical",
      "explanation": "...",
      "suggestion":  "..."
    }}
  ]
}}
"""


# ── Agent function ────────────────────────────────────────────────────────────

def run_judge(
    merged: MergedAuditorResult,
    debate_output: dict[str, Any],
) -> dict[str, Any]:
    """
    Run the Judge agent on the merged findings and debate log.

    Args:
        merged:        MergedAuditorResult from the Reduce stage.
        debate_output: Output from run_debate().

    Returns:
        The final result dict with overall_score, category_scores, verdict,
        and risky_clauses — the same shape exposed by the /analyze API endpoint.
    """
    # Convert merged findings to the legacy dict shape for the LLM prompt
    auditor_dict = merged.to_auditor_dict()
    clauses = auditor_dict.get("clauses", [])
    debates = debate_output.get("debates", [])

    user_prompt = (
        f"AUDITOR FINDINGS:\n{json.dumps(clauses, indent=2)}\n\n"
        f"DEBATE LOG:\n{json.dumps(debates, indent=2)}"
    )

    logger.info(
        "[judge] Evaluating %d finding(s) with %d debate argument(s).",
        len(clauses),
        len(debates),
    )

    result: dict[str, Any] = call_llm(
        system_prompt=JUDGE_SYSTEM,
        user_prompt=user_prompt,
        model=LARGE_MODEL,
        temperature=0.2,
    )

    # ── Safe fallback if judge output is malformed ────────────────────────────
    if "overall_score" not in result:
        logger.warning("[judge] Malformed LLM output — using fallback judgment.")
        result = _build_fallback_judgment(clauses)

    # Clamp score to [10, 100]
    result["overall_score"] = max(10, min(100, int(result.get("overall_score", 50))))

    # Ensure all six category keys exist and are in range
    cat_scores = result.setdefault("category_scores", {})
    for cat in CATEGORIES:
        cat_scores.setdefault(cat, 85)
        cat_scores[cat] = max(0, min(100, int(cat_scores[cat])))

    # Ensure verdict is valid
    valid_verdicts = {"approved", "needs_renegotiation", "unfair"}
    if result.get("verdict") not in valid_verdicts:
        score = result["overall_score"]
        result["verdict"] = (
            "approved"            if score >= 70
            else "needs_renegotiation" if score >= 40
            else "unfair"
        )

    result.setdefault("risky_clauses", [])
    logger.info(
        "[judge] Verdict: %s | Score: %d",
        result.get("verdict"),
        result.get("overall_score"),
    )
    return result


# ── Fallback helper ───────────────────────────────────────────────────────────

def _build_fallback_judgment(clauses: list[dict]) -> dict[str, Any]:
    """
    Pure-Python fallback scoring used when the Judge LLM returns malformed JSON.
    Mirrors the simple formula described in the Judge system prompt.
    Preserved verbatim from the original council_service.py implementation.
    """
    risk_deductions = {"critical": 22, "high": 14, "medium": 8, "low": 2}
    score = 100
    for clause in clauses:
        score -= risk_deductions.get(clause.get("risk_level", "low"), 2)
    score = max(10, score)

    cat_scores: dict[str, int] = {cat: 85 for cat in CATEGORIES}
    for clause in clauses:
        cat = clause.get("category", "")
        rl  = clause.get("risk_level", "low")
        if cat in cat_scores:
            mapping = {"critical": 15, "high": 38, "medium": 55, "low": 75}
            cat_scores[cat] = min(cat_scores[cat], mapping.get(rl, 75))

    risky_clauses = [
        {
            "category":    c.get("category", "general"),
            "risk_level":  c.get("risk_level", "medium"),
            "explanation": (
                f"This clause ({c.get('excerpt', '')[:60]}…) poses a "
                f"{c.get('risk_level', 'medium')} risk to the worker."
            ),
            "suggestion":  "Negotiate to remove or limit the scope of this clause before signing.",
        }
        for c in clauses
    ]

    verdict = (
        "approved"            if score >= 70
        else "needs_renegotiation" if score >= 40
        else "unfair"
    )

    return {
        "overall_score":   score,
        "category_scores": cat_scores,
        "verdict":         verdict,
        "risky_clauses":   risky_clauses,
    }
