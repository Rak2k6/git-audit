"""
services/models.py
------------------
Pydantic models for the GigAudit Map-Reduce pipeline.

Using typed models instead of raw dicts:
  - eliminates KeyError / TypeError bugs at runtime
  - makes the data-flow self-documenting
  - enables IDE auto-complete and mypy type checking
  - produces clear validation errors when an LLM returns unexpected shapes
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


# ── Risk level ordering (used for severity comparisons) ──────────────────────
RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def highest_risk(a: str, b: str) -> str:
    """Return whichever risk level is more severe."""
    return a if RISK_ORDER.get(a, 0) >= RISK_ORDER.get(b, 0) else b


# ── Chunker ───────────────────────────────────────────────────────────────────

class Chunk(BaseModel):
    """A single slice of the contract text produced by the chunker."""

    index: int = Field(..., description="Zero-based position in the chunk sequence.")
    text: str = Field(..., description="The actual contract text for this chunk.")
    token_count: int = Field(..., description="Estimated token count for this chunk.")
    method: Literal["section", "fallback"] = Field(
        ...,
        description=(
            "'section' when structural markers were detected; "
            "'fallback' when splitting by token count."
        ),
    )


# ── Auditor ───────────────────────────────────────────────────────────────────

class RawClause(BaseModel):
    """
    A single clause extracted by the Auditor agent from one chunk.
    Mirrors the JSON shape the LLM is instructed to return, with an added
    chunk_index field injected after parsing.
    """

    category: str = Field(..., description="One of: payment, termination, non_compete, ip, dispute, compensation.")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(
        ..., description="Risk severity assigned by the Auditor."
    )
    excerpt: str = Field(..., description="Short verbatim quote (≤ 30 words) from the contract.")
    raw_text: str = Field(..., description="Full clause text found by the Auditor.")
    chunk_index: int = Field(
        default=0, description="Index of the chunk this clause was extracted from."
    )


class AuditorResult(BaseModel):
    """Output from a single Auditor agent call (one chunk or the full contract)."""

    clauses: list[RawClause] = Field(default_factory=list)
    chunk_index: int = Field(default=0)
    chunk_failed: bool = Field(
        default=False,
        description="True when this chunk failed all retries and was skipped.",
    )


# ── Merge / Reduce ────────────────────────────────────────────────────────────

class MergedFinding(BaseModel):
    """
    A deduplicated finding produced by the merge stage.
    Represents one logical clause that may have been detected in multiple chunks.
    """

    category: str
    risk_level: Literal["low", "medium", "high", "critical"]
    excerpt: str = Field(..., description="Representative excerpt (from the highest-risk occurrence).")
    evidence: list[str] = Field(
        default_factory=list,
        description="raw_text from each supporting chunk occurrence.",
    )
    source_chunks: list[int] = Field(
        default_factory=list,
        description="Indices of chunks that contained this clause.",
    )
    first_occurrence: int = Field(
        ...,
        description="Lowest source chunk index — used to sort findings in document order.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Aggregated confidence score (0–1). "
            "Weighted by cross-chunk agreement, risk severity, and embedding consistency."
        ),
    )

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class MergedAuditorResult(BaseModel):
    """Output from the Reduce stage — the merged + deduplicated set of findings."""

    findings: list[MergedFinding] = Field(default_factory=list)

    def to_auditor_dict(self) -> dict:
        """
        Convert to the legacy {'clauses': [...]} dict shape expected by
        run_debate() and run_judge(), preserving backward compatibility.
        """
        return {
            "clauses": [
                {
                    "category":    f.category,
                    "risk_level":  f.risk_level,
                    "excerpt":     f.excerpt,
                    "raw_text":    " | ".join(f.evidence),
                    "confidence":  f.confidence,
                    "source_chunks": f.source_chunks,
                }
                for f in self.findings
            ]
        }

    def to_debate_dict(self) -> dict:
        """
        Richer representation passed to the Debate agent.
        Includes evidence and source_chunks so the agent can cite specific
        contract sections rather than hallucinating.
        """
        return {
            "clauses": [
                {
                    "category":     f.category,
                    "risk_level":   f.risk_level,
                    "excerpt":      f.excerpt,
                    "evidence":     f.evidence,
                    "source_chunks": f.source_chunks,
                    "confidence":   f.confidence,
                }
                for f in self.findings
            ]
        }


# ── Pipeline metadata (internal — never sent to frontend) ────────────────────

class PipelineMetadata(BaseModel):
    """
    Internal observability record for a single /analyze request.
    Emitted to the logger at INFO level; not included in the API response.
    """

    mode: Literal["single", "chunked"]
    original_tokens: int
    num_chunks: int = 0
    chunk_sizes: list[int] = Field(default_factory=list)
    map_time_sec: float = 0.0
    merge_time_sec: float = 0.0
    debate_time_sec: float = 0.0
    judge_time_sec: float = 0.0
    total_time_sec: float = 0.0
    total_llm_calls: int = 0
    failed_chunks: list[int] = Field(default_factory=list)
    retry_count: int = 0
    cache_hit: bool = False
    auditor_latencies_sec: list[float] = Field(default_factory=list)
    avg_chunk_size_tokens: float = 0.0
    cost_estimate_usd: float = 0.0
