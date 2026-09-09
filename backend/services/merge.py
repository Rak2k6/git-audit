"""
services/merge.py
------------------
Reduce stage: Merge and deduplicate Auditor findings across all chunks.

Two deduplication strategies (controlled by ENABLE_SEMANTIC_DEDUP in config):

  1. Semantic deduplication (default, ENABLE_SEMANTIC_DEDUP=True)
     - Encode all clause excerpts using sentence-transformers (all-MiniLM-L6-v2).
     - Build pairwise cosine similarity matrix.
     - Group clauses whose similarity exceeds SIMILARITY_THRESHOLD (0.85).
     - Handles paraphrases: "terminate with 30 days notice" ≈
       "end the agreement after thirty days written notice".

  2. Normalised-string deduplication (fallback, ENABLE_SEMANTIC_DEDUP=False)
     - Group by (category, normalised_excerpt) using exact string matching.
     - Cheaper, no model download, but misses paraphrases.

Both strategies produce the same MergedAuditorResult output, so the rest of
the pipeline is oblivious to which strategy was used.

Merge rules (applied after grouping):
  - Keep the HIGHEST risk_level across the group.
  - Collect all raw_text values into evidence[].
  - Union source_chunks[].
  - Set first_occurrence = min(chunk_index) → preserves document order.
  - Compute a confidence score from four components.

Confidence formula (clamped to [0.0, 1.0]):
  base            = 0.50   always
  cross_chunk     = 0.20 × (supporting_chunks / total_chunks)
  risk_weight     = 0.20 × risk_factor  (critical=1.0, high=0.75, medium=0.5, low=0.25)
  consistency     = 0.10 × (1 - intra_group_similarity_std)  ← only for semantic mode
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any

from services.config import (
    EMBEDDING_MODEL,
    ENABLE_SEMANTIC_DEDUP,
    SIMILARITY_THRESHOLD,
)
from services.models import (
    AuditorResult,
    MergedAuditorResult,
    MergedFinding,
    RawClause,
    highest_risk,
    RISK_ORDER,
)

logger = logging.getLogger(__name__)

# ── Risk weight mapping for confidence scoring ────────────────────────────────
_RISK_FACTOR: dict[str, float] = {
    "critical": 1.0,
    "high":     0.75,
    "medium":   0.50,
    "low":      0.25,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_excerpt(text: str) -> str:
    """
    Lowercase, strip punctuation, collapse whitespace.
    Used as the grouping key for string-based deduplication.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compute_confidence(
    group: list[RawClause],
    total_chunks: int,
    intra_similarity_std: float = 0.0,
) -> float:
    """
    Compute a composite confidence score for a merged finding group.

    Args:
        group:               All RawClause objects merged into this finding.
        total_chunks:        Total number of chunks in the pipeline run.
        intra_similarity_std: Std-dev of pairwise cosine similarities within
                              the group (0 when string-based dedup is used).

    Returns:
        Float in [0.0, 1.0].
    """
    # Base confidence
    confidence = 0.50

    # Cross-chunk agreement: rewarded when multiple chunks agree
    if total_chunks > 0:
        supporting_chunks = len({c.chunk_index for c in group})
        confidence += 0.20 * (supporting_chunks / total_chunks)

    # Risk weight: critical clauses get a boosted confidence
    worst_risk = max(group, key=lambda c: RISK_ORDER.get(c.risk_level, 0)).risk_level
    confidence += 0.20 * _RISK_FACTOR.get(worst_risk, 0.25)

    # Embedding consistency bonus (0.10 max; penalised by high std-dev)
    consistency = max(0.0, 1.0 - intra_similarity_std)
    confidence += 0.10 * consistency

    return max(0.0, min(1.0, confidence))


def _build_finding_from_group(
    group: list[RawClause],
    total_chunks: int,
    intra_similarity_std: float = 0.0,
) -> MergedFinding:
    """
    Collapse a group of duplicate/similar clauses into a single MergedFinding.
    """
    # Highest risk_level in the group
    best_clause = max(group, key=lambda c: RISK_ORDER.get(c.risk_level, 0))

    # De-duplicate evidence texts
    seen_texts: set[str] = set()
    evidence: list[str] = []
    for clause in sorted(group, key=lambda c: c.chunk_index):
        if clause.raw_text not in seen_texts:
            evidence.append(clause.raw_text)
            seen_texts.add(clause.raw_text)

    source_chunks = sorted({c.chunk_index for c in group})
    first_occurrence = min(c.chunk_index for c in group)

    confidence = _compute_confidence(group, total_chunks, intra_similarity_std)

    return MergedFinding(
        category=best_clause.category,
        risk_level=best_clause.risk_level,
        excerpt=best_clause.excerpt,
        evidence=evidence,
        source_chunks=source_chunks,
        first_occurrence=first_occurrence,
        confidence=round(confidence, 3),
    )


# ── Strategy 1: Semantic deduplication ───────────────────────────────────────

def _semantic_merge(
    clauses: list[RawClause],
    total_chunks: int,
) -> list[MergedFinding]:
    """
    Group clauses by semantic similarity of their excerpts.

    Uses sentence-transformers to embed excerpts, then runs a simple
    greedy union-find clustering on cosine similarities above
    SIMILARITY_THRESHOLD.
    """
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.warning(
            "[merge] sentence-transformers or numpy not installed — "
            "falling back to string-based deduplication. "
            "Install with: pip install sentence-transformers numpy"
        )
        return _string_merge(clauses, total_chunks)

    if not clauses:
        return []

    logger.info(
        "[merge] Encoding %d clause excerpt(s) with %s.",
        len(clauses),
        EMBEDDING_MODEL,
    )

    model = SentenceTransformer(EMBEDDING_MODEL)
    excerpts = [c.excerpt for c in clauses]
    embeddings: np.ndarray = model.encode(excerpts, convert_to_numpy=True)

    # Normalise rows to unit length for cosine similarity via dot product
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1e-9, norms)   # avoid division by zero
    unit_emb = embeddings / norms

    # Cosine similarity matrix (n × n)
    sim_matrix: np.ndarray = unit_emb @ unit_emb.T

    # ── Greedy union-find clustering ──────────────────────────────────────────
    n = len(clauses)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: int, y: int) -> None:
        parent[find(x)] = find(y)

    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i, j] >= SIMILARITY_THRESHOLD:
                union(i, j)

    # Group indices by cluster root
    groups: dict[int, list[int]] = defaultdict(list)
    for idx in range(n):
        groups[find(idx)].append(idx)

    # Build MergedFinding for each cluster
    findings: list[MergedFinding] = []
    for cluster_indices in groups.values():
        group_clauses = [clauses[i] for i in cluster_indices]

        # Compute intra-cluster similarity std for confidence bonus
        if len(cluster_indices) > 1:
            cluster_sims = [
                float(sim_matrix[i, j])
                for idx_i, i in enumerate(cluster_indices)
                for j in cluster_indices[idx_i + 1:]
            ]
            intra_std = float(np.std(cluster_sims)) if cluster_sims else 0.0
        else:
            intra_std = 0.0

        findings.append(
            _build_finding_from_group(group_clauses, total_chunks, intra_std)
        )

    logger.info(
        "[merge] Semantic dedup: %d clause(s) → %d unique finding(s).",
        len(clauses),
        len(findings),
    )
    return findings


# ── Strategy 2: String-based deduplication ────────────────────────────────────

def _string_merge(
    clauses: list[RawClause],
    total_chunks: int,
) -> list[MergedFinding]:
    """
    Group clauses by (category, normalised_excerpt) string matching.

    Cheaper than semantic merge but cannot detect paraphrases.  Used when
    ENABLE_SEMANTIC_DEDUP=False or when sentence-transformers is unavailable.
    """
    groups: dict[tuple[str, str], list[RawClause]] = defaultdict(list)
    for clause in clauses:
        key = (clause.category, _normalise_excerpt(clause.excerpt))
        groups[key].append(clause)

    findings = [
        _build_finding_from_group(group_clauses, total_chunks)
        for group_clauses in groups.values()
    ]

    logger.info(
        "[merge] String dedup: %d clause(s) → %d unique finding(s).",
        len(clauses),
        len(findings),
    )
    return findings


# ── Public API ────────────────────────────────────────────────────────────────

def merge_findings(chunk_results: list[AuditorResult]) -> MergedAuditorResult:
    """
    Merge and deduplicate clause findings from all Auditor chunk results.

    This is the Reduce stage of the Map-Reduce pipeline.

    Steps:
      1. Flatten all RawClause objects from every AuditorResult.
      2. Deduplicate using semantic (default) or string-based grouping.
      3. Sort merged findings by first_occurrence → preserves document order.
      4. Return a MergedAuditorResult.

    Args:
        chunk_results: List of AuditorResult objects, one per chunk.
                       Results with chunk_failed=True contribute no clauses
                       but are still counted in total_chunks for confidence
                       score normalisation.

    Returns:
        MergedAuditorResult with deduplicated, document-ordered findings.
    """
    total_chunks = len(chunk_results)

    # Flatten all clauses (skip failed chunks)
    all_clauses: list[RawClause] = []
    failed_count = 0
    for result in chunk_results:
        if result.chunk_failed:
            failed_count += 1
            continue
        all_clauses.extend(result.clauses)

    if failed_count:
        logger.warning(
            "[merge] %d / %d chunk(s) failed — their clauses are excluded from merge.",
            failed_count,
            total_chunks,
        )

    if not all_clauses:
        logger.info("[merge] No clauses to merge — returning empty result.")
        return MergedAuditorResult(findings=[])

    logger.info(
        "[merge] Merging %d total clause(s) from %d chunk(s) "
        "(semantic_dedup=%s, threshold=%.2f).",
        len(all_clauses),
        total_chunks - failed_count,
        ENABLE_SEMANTIC_DEDUP,
        SIMILARITY_THRESHOLD,
    )

    # Choose deduplication strategy
    if ENABLE_SEMANTIC_DEDUP:
        findings = _semantic_merge(all_clauses, total_chunks)
    else:
        findings = _string_merge(all_clauses, total_chunks)

    # Sort by first_occurrence to preserve document reading order
    findings.sort(key=lambda f: f.first_occurrence)

    return MergedAuditorResult(findings=findings)
