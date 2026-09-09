"""
services/chunker.py
--------------------
Section-aware contract chunking with a token-based fallback.

Algorithm (in priority order):
  1. Section-aware split
     - Scan for structural markers: ARTICLE, SECTION, CLAUSE headings,
       numbered patterns (1., 1.1, 2.3.1), ALL-CAPS short headings.
     - Build sections between consecutive markers.
     - Sub-split oversized sections at sentence boundaries.
     - Merge undersized adjacent sections up to CHUNK_SIZE.
     - Apply CHUNK_OVERLAP by prepending the tail of the previous chunk.
     - Tag chunks: method="section"

  2. Fallback (fewer than 2 markers detected)
     - Split on sentence boundaries (".  " / ".\n") every CHUNK_SIZE tokens.
     - Apply CHUNK_OVERLAP the same way.
     - Tag chunks: method="fallback"

Returns:
    list[Chunk]  — typed Pydantic models, each with index, text, token_count,
                   and method.
"""

from __future__ import annotations

import logging
import re
from typing import Sequence

from services.config import (
    CHUNK_OVERLAP,
    PROMPT_OVERHEAD_TOKENS,
    SAFETY_MARGIN_TOKENS,
    MODEL_CONTEXT_WINDOW,
)
from services.models import Chunk
from services.token_counter import compute_chunk_size, count_tokens

logger = logging.getLogger(__name__)

# Compute CHUNK_SIZE dynamically from model context window
CHUNK_SIZE: int = compute_chunk_size(
    MODEL_CONTEXT_WINDOW, PROMPT_OVERHEAD_TOKENS, SAFETY_MARGIN_TOKENS
)

# ── Section marker patterns ───────────────────────────────────────────────────
# These regexes match common structural markers in legal / gig contracts.
# The patterns are tried in order; the first match wins for each line.

_SECTION_PATTERNS: list[re.Pattern] = [
    # Keyword headings: ARTICLE IV, SECTION 3, CLAUSE 2
    re.compile(r"^\s*(ARTICLE|SECTION|CLAUSE)\b.*", re.IGNORECASE | re.MULTILINE),
    # Decimal numbering: 1., 1.1, 2.3, 10.4.1  (at line start)
    re.compile(r"^\s*\d+(\.\d+)*\.?\s+\S", re.MULTILINE),
    # Lettered sub-clauses: (a), (b), (i), (ii)
    re.compile(r"^\s*\([a-z]{1,3}\)\s+\S", re.MULTILINE),
    # ALL-CAPS short lines (≤ 8 words) — e.g., "TERMINATION", "PAYMENT TERMS"
    re.compile(r"^\s*[A-Z][A-Z\s\-]{2,50}\s*$", re.MULTILINE),
]


def _find_section_boundaries(text: str) -> list[int]:
    """
    Return sorted character offsets for every detected section marker.

    Deduplicates overlapping matches and returns at least [0] so that even
    contracts with no structure get a single "section" starting at 0.
    """
    offsets: set[int] = {0}
    for pattern in _SECTION_PATTERNS:
        for match in pattern.finditer(text):
            offsets.add(match.start())
    return sorted(offsets)


def _split_at_sentence_boundaries(text: str, max_tokens: int) -> list[str]:
    """
    Split *text* into pieces where each piece is ≤ *max_tokens* tokens.
    Splits preferentially at sentence boundaries (". " or ".\n").
    """
    # Split into sentences (simple heuristic — good enough for contracts)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    pieces: list[str] = []
    current_sentences: list[str] = []
    current_tokens = 0

    for sentence in sentences:
        sentence_tokens = count_tokens(sentence)
        if current_tokens + sentence_tokens > max_tokens and current_sentences:
            pieces.append(" ".join(current_sentences))
            current_sentences = [sentence]
            current_tokens = sentence_tokens
        else:
            current_sentences.append(sentence)
            current_tokens += sentence_tokens

    if current_sentences:
        pieces.append(" ".join(current_sentences))

    return [p for p in pieces if p.strip()]


def _apply_overlap(chunks: list[str], overlap_tokens: int) -> list[str]:
    """
    Prepend the last *overlap_tokens* tokens from chunk[i-1] to chunk[i].

    This ensures that clauses spanning chunk boundaries are captured in at
    least one of the two adjacent chunks.
    """
    if len(chunks) <= 1 or overlap_tokens <= 0:
        return chunks

    result: list[str] = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_words = chunks[i - 1].split()
        # Approximate: overlap_tokens words (words ≈ tokens for English)
        overlap_words = prev_words[-overlap_tokens:] if len(prev_words) > overlap_tokens else prev_words
        overlap_text = " ".join(overlap_words)
        result.append(overlap_text + "\n\n" + chunks[i])

    return result


def _build_chunks_from_sections(text: str, boundaries: list[int]) -> list[str]:
    """
    Slice *text* at *boundaries* into raw section strings.

    Sections that exceed CHUNK_SIZE are sub-split at sentence boundaries.
    Adjacent sections smaller than CHUNK_SIZE / 4 are merged greedily.
    """
    # Extract raw section strings
    raw_sections: list[str] = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else len(text)
        section_text = text[start:end].strip()
        if not section_text:
            continue

        if count_tokens(section_text) > CHUNK_SIZE:
            # Sub-split oversized sections
            raw_sections.extend(_split_at_sentence_boundaries(section_text, CHUNK_SIZE))
        else:
            raw_sections.append(section_text)

    # Greedy merge of undersized sections
    merged: list[str] = []
    buffer = ""
    buffer_tokens = 0
    merge_threshold = CHUNK_SIZE // 4  # sections smaller than this get merged

    for section in raw_sections:
        section_tokens = count_tokens(section)
        if buffer_tokens + section_tokens <= CHUNK_SIZE:
            buffer = (buffer + "\n\n" + section).strip() if buffer else section
            buffer_tokens += section_tokens
        else:
            if buffer:
                merged.append(buffer)
            buffer = section
            buffer_tokens = section_tokens

    if buffer:
        merged.append(buffer)

    return merged


# ── Public API ────────────────────────────────────────────────────────────────

def chunk_contract(text: str) -> list[Chunk]:
    """
    Split *text* into a list of Chunk objects for parallel Auditor processing.

    Tries section-aware splitting first; falls back to sentence-boundary
    splitting if fewer than 2 structural markers are detected.

    Each chunk is tagged with:
      - index:       zero-based position in the sequence
      - text:        the actual contract text (with overlap prepended)
      - token_count: estimated tokens
      - method:      "section" | "fallback"

    Returns at least one chunk (the full text) even for very short inputs.
    """
    text = text.strip()
    if not text:
        return []

    # ── Attempt 1: section-aware ─────────────────────────────────────────────
    boundaries = _find_section_boundaries(text)
    method: str

    if len(boundaries) >= 2:
        logger.info(
            "[chunker] Detected %d section markers — using section-aware split.",
            len(boundaries),
        )
        raw_chunks = _build_chunks_from_sections(text, boundaries)
        method = "section"
    else:
        # ── Fallback: sentence-boundary split ────────────────────────────────
        logger.info(
            "[chunker] < 2 section markers detected — falling back to "
            "token-based sentence splitting."
        )
        raw_chunks = _split_at_sentence_boundaries(text, CHUNK_SIZE)
        method = "fallback"

    # Apply overlap between consecutive chunks
    overlapped = _apply_overlap(raw_chunks, CHUNK_OVERLAP)

    # Build typed Chunk models
    chunks: list[Chunk] = [
        Chunk(
            index=i,
            text=chunk_text,
            token_count=count_tokens(chunk_text),
            method=method,  # type: ignore[arg-type]
        )
        for i, chunk_text in enumerate(overlapped)
        if chunk_text.strip()
    ]

    logger.info(
        "[chunker] Produced %d chunks (method=%s, sizes=%s).",
        len(chunks),
        method,
        [c.token_count for c in chunks],
    )
    return chunks
