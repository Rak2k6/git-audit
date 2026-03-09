"""
council_service.py
------------------
The 3-Agent AI Council that audits a gig contract.

Pipeline:
  1. Auditor  → Extract & categorise clauses from raw contract text
  2. Debate   → Generate balanced Advocate / Skeptic arguments
  3. Judge    → Score, verdict, and negotiation suggestions

All three agents are stateless: they receive their inputs as prompt text
and return structured JSON payloads.
"""

from __future__ import annotations

import json
from typing import Any

from backend.llm_client import FAST_MODEL, LARGE_MODEL, call_llm

# ── Category definitions shared across agents ────────────────────────────────
CATEGORIES = ["payment", "termination", "non_compete", "ip", "dispute", "compensation"]


# ════════════════════════════════════════════════════════════════════════════
# AGENT 1 — AUDITOR
# ════════════════════════════════════════════════════════════════════════════

AUDITOR_SYSTEM = """You are a senior labor-law NLP expert specialising in gig economy contracts.

Your job:
- Read the raw contract text provided by the user.
- Identify EVERY clause that falls into one of the following categories:
    payment, termination, non_compete, ip, dispute, compensation
- For each detected clause, extract:
    - category       : one of the six above
    - risk_level     : "low" | "medium" | "high" | "critical"
    - excerpt        : a SHORT verbatim quote (≤ 30 words) from the contract
    - raw_text       : the full clause text you found

Return a JSON object with exactly this shape:
{
  "clauses": [
    {
      "category":   "payment",
      "risk_level": "critical",
      "excerpt":    "...",
      "raw_text":   "..."
    }
  ]
}

If a category has no problematic clauses, omit it from the list.
Assess risk strictly: only mark "critical" for extreme wage theft, total IP grab,
or illegal terms.
"""


def run_auditor(contract_text: str) -> dict[str, Any]:
    """Agent 1 — extract and categorise clauses."""
    result = call_llm(
        system_prompt=AUDITOR_SYSTEM,
        user_prompt=f"CONTRACT TEXT:\n\n{contract_text}",
        model=LARGE_MODEL,
        temperature=0.1,   # near-deterministic extraction
    )
    # Guarantee a safe shape even on empty/malformed LLM output
    if "clauses" not in result or not isinstance(result["clauses"], list):
        result = {"clauses": []}
    return result


# ════════════════════════════════════════════════════════════════════════════
# AGENT 2 — DEBATE
# ════════════════════════════════════════════════════════════════════════════

DEBATE_SYSTEM = """You are a legal debate moderator.

You will receive a list of contract clauses extracted by an auditor.

For EACH clause simulate two perspectives:
  - ADVOCATE  : argues the clause is acceptable / standard practice
  - SKEPTIC   : argues the clause is exploitative / one-sided

Rules:
  - Base arguments ONLY on the provided clauses — do not invent facts.
  - Keep each argument to 1–2 sentences.
  - Be balanced: the Advocate should have at least one reasonable point.

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


def run_debate(auditor_output: dict[str, Any]) -> dict[str, Any]:
    """Agent 2 — debate each clause."""
    clauses = auditor_output.get("clauses", [])
    if not clauses:
        return {"debates": []}

    clauses_json = json.dumps(clauses, indent=2)

    result = call_llm(
        system_prompt=DEBATE_SYSTEM,
        user_prompt=f"EXTRACTED CLAUSES:\n\n{clauses_json}",
        model=FAST_MODEL,     # speed-optimised; debate is lower-stakes
        temperature=0.3,
    )

    if "debates" not in result or not isinstance(result["debates"], list):
        result = {"debates": []}
    return result


# ════════════════════════════════════════════════════════════════════════════
# AGENT 3 — JUDGE
# ════════════════════════════════════════════════════════════════════════════

JUDGE_SYSTEM = f"""You are a senior labor-law judge with deep expertise in gig economy contracts.

You will receive:
  1. The clauses extracted by an Auditor.
  2. A debate log (Advocate vs. Skeptic arguments) for each clause.

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

  D. For each extracted clause produce a RISKY CLAUSE object:
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


def run_judge(
    auditor_output: dict[str, Any],
    debate_output: dict[str, Any],
) -> dict[str, Any]:
    """Agent 3 — score, verdict, and suggestions."""
    clauses = auditor_output.get("clauses", [])
    debates = debate_output.get("debates", [])

    user_prompt = (
        f"AUDITOR CLAUSES:\n{json.dumps(clauses, indent=2)}\n\n"
        f"DEBATE LOG:\n{json.dumps(debates, indent=2)}"
    )

    result = call_llm(
        system_prompt=JUDGE_SYSTEM,
        user_prompt=user_prompt,
        model=LARGE_MODEL,
        temperature=0.2,
    )

    # ── Safe fallback if judge output is malformed ────────────────────────────
    if "overall_score" not in result:
        result = _build_fallback_judgment(clauses)

    # Clamp score to [10, 100]
    result["overall_score"] = max(10, min(100, int(result.get("overall_score", 50))))

    # Ensure all six category keys exist
    cat_scores = result.setdefault("category_scores", {})
    for cat in CATEGORIES:
        cat_scores.setdefault(cat, 85)
        cat_scores[cat] = max(0, min(100, int(cat_scores[cat])))

    # Ensure verdict is valid
    valid_verdicts = {"approved", "needs_renegotiation", "unfair"}
    if result.get("verdict") not in valid_verdicts:
        score = result["overall_score"]
        result["verdict"] = (
            "approved" if score >= 70
            else "needs_renegotiation" if score >= 40
            else "unfair"
        )

    result.setdefault("risky_clauses", [])
    return result


# ════════════════════════════════════════════════════════════════════════════
# FALLBACK HELPER
# ════════════════════════════════════════════════════════════════════════════

def _build_fallback_judgment(clauses: list[dict]) -> dict[str, Any]:
    """
    Pure-Python fallback scoring used when the Judge LLM returns malformed JSON.
    Mirrors the simple formula described in the Judge system prompt.
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
            "explanation": f"This clause ({c.get('excerpt', '')[:60]}…) poses a {c.get('risk_level','medium')} risk to the worker.",
            "suggestion":  "Negotiate to remove or limit the scope of this clause before signing.",
        }
        for c in clauses
    ]

    verdict = (
        "approved" if score >= 70
        else "needs_renegotiation" if score >= 40
        else "unfair"
    )

    return {
        "overall_score":   score,
        "category_scores": cat_scores,
        "verdict":         verdict,
        "risky_clauses":   risky_clauses,
    }


# ════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

def run_council(contract_text: str) -> dict[str, Any]:
    """
    Execute the full 3-agent pipeline and return the final structured result.

    Steps:
      1. Auditor  — clause extraction
      2. Debate   — argument simulation
      3. Judge    — scoring + verdict
    """
    print("[council] Step 1/3 — Auditor")
    auditor_result = run_auditor(contract_text)
    print(f"[council] Auditor found {len(auditor_result.get('clauses', []))} clauses")

    print("[council] Step 2/3 — Debate")
    debate_result = run_debate(auditor_result)
    print(f"[council] Debate generated {len(debate_result.get('debates', []))} arguments")

    print("[council] Step 3/3 — Judge")
    final_result = run_judge(auditor_result, debate_result)
    print(f"[council] Judge verdict: {final_result.get('verdict')} | score: {final_result.get('overall_score')}")

    return final_result
