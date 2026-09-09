"""
services/token_counter.py
--------------------------
Accurate token counting with a fast word-count fallback.

Priority:
  1. tiktoken (exact, uses cl100k_base encoding — close to llama tokenizers)
  2. word_count × 1.3  (fast approximation when tiktoken is unavailable)

The module exposes three pure functions with no side effects, making them
safe to unit-test without any LLM credentials.
"""

from __future__ import annotations

import logging

from services.config import (
    COST_PER_1K_TOKENS_USD,
    MAX_SINGLE_ANALYSIS,
)

logger = logging.getLogger(__name__)

# ── Try to import tiktoken once at module load ────────────────────────────────
try:
    import tiktoken as _tiktoken

    _encoding = _tiktoken.get_encoding("cl100k_base")
    _TIKTOKEN_AVAILABLE = True
    logger.info("[token_counter] tiktoken loaded — using exact token counts.")
except ImportError:
    _TIKTOKEN_AVAILABLE = False
    logger.warning(
        "[token_counter] tiktoken not installed — using word × 1.3 approximation. "
        "Install with: pip install tiktoken"
    )


# ── Public API ────────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    """
    Return the approximate number of tokens in *text*.

    Uses tiktoken (cl100k_base) when available; falls back to
    ``ceil(word_count × 1.3)`` which is accurate to within ~5 % for
    typical English contract prose.
    """
    if not text:
        return 0

    if _TIKTOKEN_AVAILABLE:
        return len(_encoding.encode(text))

    # Fallback: split on whitespace and apply the 1.3 factor
    word_count = len(text.split())
    return int(word_count * 1.3) + 1  # +1 avoids zero on single-word input


def needs_chunking(text: str) -> bool:
    """
    Return *True* when the token count of *text* exceeds MAX_SINGLE_ANALYSIS.

    A result of True means the contract should enter the chunked Map-Reduce
    pipeline rather than a single Auditor call.
    """
    token_count = count_tokens(text)
    if token_count > MAX_SINGLE_ANALYSIS:
        logger.info(
            "[token_counter] Contract tokens=%d > threshold=%d → chunked path.",
            token_count,
            MAX_SINGLE_ANALYSIS,
        )
        return True
    logger.info(
        "[token_counter] Contract tokens=%d ≤ threshold=%d → single-call path.",
        token_count,
        MAX_SINGLE_ANALYSIS,
    )
    return False


def compute_chunk_size(
    context_window: int,
    prompt_overhead: int,
    safety_margin: int,
) -> int:
    """
    Compute the maximum safe token count for a single contract chunk.

    chunk_size = context_window - prompt_overhead - safety_margin

    This function is called at pipeline startup so that changing the model
    (and therefore its context_window) automatically adjusts chunk sizes
    without touching any other code.

    Args:
        context_window:  Maximum tokens the LLM accepts in a single call.
        prompt_overhead: Tokens consumed by the system prompt and JSON
                         scaffolding instructions.
        safety_margin:   Buffer to avoid hitting the hard limit.

    Returns:
        Safe chunk size in tokens (minimum: 512).
    """
    size = context_window - prompt_overhead - safety_margin
    if size < 512:
        logger.warning(
            "[token_counter] Computed chunk size %d is very small — "
            "check MODEL_CONTEXT_WINDOW / PROMPT_OVERHEAD_TOKENS / SAFETY_MARGIN_TOKENS.",
            size,
        )
        size = 512
    return size


def estimate_cost(total_tokens: int) -> float:
    """
    Return a rough USD cost estimate for *total_tokens* processed.

    Uses COST_PER_1K_TOKENS_USD from config.  This is for observability /
    logging purposes only and is not billing-accurate.
    """
    return round(total_tokens / 1000 * COST_PER_1K_TOKENS_USD, 6)
