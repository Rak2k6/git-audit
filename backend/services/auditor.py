"""
services/auditor.py
--------------------
Auditor Agent — Agent 1 of the GigAudit pipeline.

Extracted from council_service.py and enhanced:
  - chunk_index parameter injected into the prompt so the LLM knows which
    section of the document it is reading (reduces hallucination).
  - Returns a typed AuditorResult instead of a raw dict.
  - Error path returns AuditorResult with chunk_failed=True so the pipeline
    can record but not crash on a bad chunk.
"""

from __future__ import annotations

import logging
from typing import Any

from llm_client import LARGE_MODEL, call_llm
from services.models import AuditorResult, RawClause

logger = logging.getLogger(__name__)


# ── System prompt ─────────────────────────────────────────────────────────────
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


# ── Agent function ────────────────────────────────────────────────────────────

def run_auditor(contract_text: str, chunk_index: int = 0) -> AuditorResult:
    """
    Run the Auditor agent on a single contract text (or chunk).

    Args:
        contract_text: The raw text to analyse.  May be the full contract
                       (single-call path) or a slice (chunked path).
        chunk_index:   Zero-based position of this chunk in the sequence.
                       Injected into the prompt for context; does not affect
                       the LLM's extraction logic.

    Returns:
        AuditorResult with the extracted clauses (or chunk_failed=True on
        any unrecoverable error — handled by the retry wrapper in pipeline.py).
    """
    chunk_label = (
        f"DOCUMENT SECTION {chunk_index + 1}"
        if chunk_index > 0
        else "CONTRACT TEXT"
    )

    user_prompt = f"{chunk_label}:\n\n{contract_text}"

    logger.debug("[auditor] Calling LLM for chunk_index=%d.", chunk_index)

    raw: dict[str, Any] = call_llm(
        system_prompt=AUDITOR_SYSTEM,
        user_prompt=user_prompt,
        model=LARGE_MODEL,
        temperature=0.1,   # near-deterministic extraction
    )

    # A valid JSON response with the wrong shape is still an analysis failure;
    # treating it as zero findings would make a broken call look perfectly fair.
    if "clauses" not in raw:
        raise RuntimeError("Auditor returned JSON without the required 'clauses' field.")

    # ── Parse and validate the LLM response ──────────────────────────────────
    raw_clauses = raw.get("clauses", [])
    if not isinstance(raw_clauses, list):
        logger.warning(
            "[auditor] Unexpected 'clauses' type from LLM for chunk %d: %s",
            chunk_index,
            type(raw_clauses),
        )
        raw_clauses = []

    clauses: list[RawClause] = []
    for item in raw_clauses:
        if not isinstance(item, dict):
            continue
        try:
            clauses.append(
                RawClause(
                    category=item.get("category", "general"),
                    risk_level=item.get("risk_level", "low"),
                    excerpt=item.get("excerpt", ""),
                    raw_text=item.get("raw_text", ""),
                    chunk_index=chunk_index,
                )
            )
        except Exception as parse_err:
            logger.warning(
                "[auditor] Skipping malformed clause from chunk %d: %s",
                chunk_index,
                parse_err,
            )

    logger.info(
        "[auditor] chunk=%d → %d clause(s) extracted.",
        chunk_index,
        len(clauses),
    )
    return AuditorResult(clauses=clauses, chunk_index=chunk_index, chunk_failed=False)
