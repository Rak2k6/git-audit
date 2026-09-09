"""
services/pipeline.py
---------------------
Top-level async orchestrator for the GigAudit Map-Reduce analysis pipeline.

This module is the single entry point for contract analysis.  It wires
together all services and implements the adaptive routing logic:

  Short contract (≤ MAX_SINGLE_ANALYSIS tokens)
    └─ Single Auditor call → Merge wrapper → Debate → Judge

  Large contract (> MAX_SINGLE_ANALYSIS tokens)
    └─ Section-aware Chunking
       └─ Parallel Auditor calls (asyncio + Semaphore)
          └─ Exponential backoff retry per chunk
             └─ Semantic Merge + Dedup (Reduce stage)
                └─ Debate Agent
                   └─ Judge Agent

The function signature `run_council(contract_text)` is identical to the
original council_service.py so that the FastAPI route requires only a
minimal change (sync → async).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from services.auditor import run_auditor
from services.cache import get_cached_result, set_cached_result
from services.chunker import chunk_contract
from services.config import (
    ENABLE_PARALLEL,
    MAX_CHUNK_RETRIES,
    MAX_CONCURRENT_CHUNKS,
    MAX_SINGLE_ANALYSIS,
    MODEL_CONTEXT_WINDOW,
    PROMPT_OVERHEAD_TOKENS,
    RETRY_BASE_DELAY_SEC,
    SAFETY_MARGIN_TOKENS,
)
from services.debate import run_debate
from services.judge import run_judge
from services.merge import merge_findings
from services.metrics import log_pipeline_metrics
from services.models import (
    AuditorResult,
    Chunk,
    MergedAuditorResult,
    PipelineMetadata,
    RawClause,
)
from services.token_counter import count_tokens, estimate_cost, needs_chunking

logger = logging.getLogger(__name__)


# ── Retry wrapper ─────────────────────────────────────────────────────────────

def _run_auditor_with_retry(chunk: Chunk) -> AuditorResult:
    """
    Call run_auditor() on a single chunk with exponential backoff retry.

    Retry schedule (RETRY_BASE_DELAY_SEC=1.0):
      Attempt 0: immediate
      Attempt 1: sleep 1 s
      Attempt 2: sleep 2 s
      (MAX_CHUNK_RETRIES=2 means 3 total attempts)

    On exhaustion returns AuditorResult(chunk_failed=True) so that the
    pipeline can record the failure without crashing the whole request.

    Returns:
        (AuditorResult, retry_count: int)
    """
    last_exc: Exception | None = None

    for attempt in range(MAX_CHUNK_RETRIES + 1):
        try:
            result = run_auditor(chunk.text, chunk.index)
            if attempt > 0:
                logger.info(
                    "[pipeline] Chunk %d succeeded on attempt %d.",
                    chunk.index,
                    attempt + 1,
                )
            return result, attempt
        except Exception as exc:
            last_exc = exc
            if attempt < MAX_CHUNK_RETRIES:
                delay = RETRY_BASE_DELAY_SEC * (2 ** attempt)   # 1s, 2s, 4s …
                logger.warning(
                    "[pipeline] Chunk %d failed (attempt %d/%d): %s — "
                    "retrying in %.1fs.",
                    chunk.index,
                    attempt + 1,
                    MAX_CHUNK_RETRIES + 1,
                    exc,
                    delay,
                )
                time.sleep(delay)

    logger.error(
        "[pipeline] Chunk %d failed all %d attempt(s): %s — marking as failed.",
        chunk.index,
        MAX_CHUNK_RETRIES + 1,
        last_exc,
    )
    return AuditorResult(clauses=[], chunk_index=chunk.index, chunk_failed=True), MAX_CHUNK_RETRIES


# ── Parallel map stage ────────────────────────────────────────────────────────

async def _map_auditor_parallel(
    chunks: list[Chunk],
    meta: PipelineMetadata,
) -> list[AuditorResult]:
    """
    Run the Auditor agent on every chunk concurrently, bounded by a Semaphore.

    asyncio.Semaphore(MAX_CONCURRENT_CHUNKS) ensures we never exceed the Groq
    rate limit by launching all N chunk requests simultaneously.

    Uses asyncio.to_thread() to offload the synchronous Groq SDK call onto a
    thread-pool worker so it does not block the event loop.

    Updates PipelineMetadata in-place with per-chunk latencies and failure info.
    """
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CHUNKS)

    async def _auditor_task(chunk: Chunk) -> AuditorResult:
        async with semaphore:
            t0 = time.perf_counter()
            result, retries = await asyncio.to_thread(_run_auditor_with_retry, chunk)
            elapsed = time.perf_counter() - t0
            meta.auditor_latencies_sec.append(elapsed)
            meta.retry_count += retries
            if result.chunk_failed:
                meta.failed_chunks.append(chunk.index)
            logger.info(
                "[pipeline] Chunk %d processed in %.2fs (failed=%s).",
                chunk.index,
                elapsed,
                result.chunk_failed,
            )
            return result

    logger.info(
        "[pipeline] Map stage: %d chunk(s) | max_concurrent=%d.",
        len(chunks),
        MAX_CONCURRENT_CHUNKS,
    )
    tasks = [_auditor_task(c) for c in chunks]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


async def _map_auditor_sequential(
    chunks: list[Chunk],
    meta: PipelineMetadata,
) -> list[AuditorResult]:
    """
    Sequential (non-parallel) fallback for ENABLE_PARALLEL=False.
    Useful for debugging or environments where concurrency is prohibited.
    """
    results: list[AuditorResult] = []
    for chunk in chunks:
        t0 = time.perf_counter()
        result, retries = await asyncio.to_thread(_run_auditor_with_retry, chunk)
        elapsed = time.perf_counter() - t0
        meta.auditor_latencies_sec.append(elapsed)
        meta.retry_count += retries
        if result.chunk_failed:
            meta.failed_chunks.append(chunk.index)
        results.append(result)
    return results


# ── Wrap single-call auditor result in MergedAuditorResult ────────────────────

def _wrap_single_result(auditor_result: AuditorResult) -> MergedAuditorResult:
    """
    For the single-call (short contract) path, wrap the AuditorResult into a
    MergedAuditorResult so the rest of the pipeline uses a uniform interface.

    Each clause becomes a MergedFinding with:
      - single evidence entry
      - source_chunks = [0]
      - first_occurrence = 0
      - confidence from risk weight only (no cross-chunk signal)
    """
    from services.models import MergedFinding, RISK_ORDER

    _RISK_FACTOR = {"critical": 1.0, "high": 0.75, "medium": 0.50, "low": 0.25}

    findings = []
    for clause in auditor_result.clauses:
        risk_w = _RISK_FACTOR.get(clause.risk_level, 0.25)
        confidence = round(0.50 + 0.20 * risk_w, 3)   # base + risk_weight; no cross-chunk
        findings.append(
            MergedFinding(
                category=clause.category,
                risk_level=clause.risk_level,
                excerpt=clause.excerpt,
                evidence=[clause.raw_text],
                source_chunks=[0],
                first_occurrence=0,
                confidence=confidence,
            )
        )
    return MergedAuditorResult(findings=findings)


# ── Public entry point ────────────────────────────────────────────────────────

async def run_council(contract_text: str) -> dict[str, Any]:
    """
    Execute the full GigAudit analysis pipeline and return the final result.

    This is the only public function in this module and is called directly
    by the FastAPI route handler in main.py.

    Routing:
      - Short contract (≤ MAX_SINGLE_ANALYSIS tokens) → single Auditor call.
      - Long contract (> MAX_SINGLE_ANALYSIS tokens)  → chunked Map-Reduce.

    Returns:
        The final result dict with keys:
          overall_score, category_scores, verdict, risky_clauses
        — identical to the shape produced by the original council_service.py.
        The API response and frontend are fully backward compatible.
    """
    pipeline_start = time.perf_counter()

    # ── 1. Cache check ────────────────────────────────────────────────────────
    cached = get_cached_result(contract_text)
    if cached:
        logger.info("[pipeline] Cache hit — returning cached result.")
        total_tokens = count_tokens(contract_text)
        meta = PipelineMetadata(
            mode="single",
            original_tokens=total_tokens,
            cache_hit=True,
            total_time_sec=round(time.perf_counter() - pipeline_start, 3),
        )
        log_pipeline_metrics(meta)
        return cached

    # ── 2. Token count & routing decision ─────────────────────────────────────
    total_tokens = count_tokens(contract_text)
    use_chunked = needs_chunking(contract_text)

    meta = PipelineMetadata(
        mode="chunked" if use_chunked else "single",
        original_tokens=total_tokens,
        cache_hit=False,
    )

    # ── 3a. Single-call path (short contract) ─────────────────────────────────
    if not use_chunked:
        logger.info("[pipeline] Step 1/3 — Auditor (single call).")
        t0 = time.perf_counter()
        auditor_result = run_auditor(contract_text, chunk_index=0)
        meta.auditor_latencies_sec.append(time.perf_counter() - t0)
        meta.total_llm_calls += 1
        meta.num_chunks = 1
        meta.chunk_sizes = [total_tokens]
        merged = _wrap_single_result(auditor_result)

        logger.info(
            "[pipeline] Auditor found %d clause(s).",
            len(auditor_result.clauses),
        )

    # ── 3b. Chunked Map-Reduce path (large contract) ──────────────────────────
    else:
        # Chunk
        logger.info("[pipeline] Step 1/3 — Chunking contract.")
        chunks = chunk_contract(contract_text)
        meta.num_chunks = len(chunks)
        meta.chunk_sizes = [c.token_count for c in chunks]
        meta.avg_chunk_size_tokens = (
            sum(meta.chunk_sizes) / len(meta.chunk_sizes) if meta.chunk_sizes else 0.0
        )

        # Map stage — parallel or sequential
        logger.info("[pipeline] Step 2/3 — Map stage (Auditor × %d).", len(chunks))
        map_start = time.perf_counter()

        if ENABLE_PARALLEL:
            chunk_results = await _map_auditor_parallel(chunks, meta)
        else:
            chunk_results = await _map_auditor_sequential(chunks, meta)

        meta.map_time_sec = time.perf_counter() - map_start
        meta.total_llm_calls += len(chunks)

        logger.info(
            "[pipeline] Map stage complete: %.2fs | %d failed chunk(s).",
            meta.map_time_sec,
            len(meta.failed_chunks),
        )

        if meta.failed_chunks and len(meta.failed_chunks) == len(chunks):
            raise RuntimeError(
                "Contract analysis failed: every document section could not be analyzed."
            )

        # Reduce stage — semantic merge + dedup
        logger.info("[pipeline] Step 3/3 — Reduce stage (merge + dedup).")
        merge_start = time.perf_counter()
        merged = merge_findings(chunk_results)
        meta.merge_time_sec = time.perf_counter() - merge_start

        logger.info(
            "[pipeline] Merge complete: %.2fms | %d unique finding(s).",
            meta.merge_time_sec * 1000,
            len(merged.findings),
        )

    # ── 4. Debate Agent ───────────────────────────────────────────────────────
    logger.info("[pipeline] Debate Agent — %d finding(s).", len(merged.findings))
    t0 = time.perf_counter()
    debate_result = run_debate(merged)
    meta.debate_time_sec = time.perf_counter() - t0
    meta.total_llm_calls += 1

    # ── 5. Judge Agent ────────────────────────────────────────────────────────
    logger.info("[pipeline] Judge Agent.")
    t0 = time.perf_counter()
    final_result = run_judge(merged, debate_result)
    meta.judge_time_sec = time.perf_counter() - t0
    meta.total_llm_calls += 1

    # ── 6. Finalise metadata ──────────────────────────────────────────────────
    meta.total_time_sec = time.perf_counter() - pipeline_start
    if meta.chunk_sizes:
        meta.avg_chunk_size_tokens = sum(meta.chunk_sizes) / len(meta.chunk_sizes)
    meta.cost_estimate_usd = estimate_cost(total_tokens)

    # ── 7. Log metrics ────────────────────────────────────────────────────────
    log_pipeline_metrics(meta)

    # ── 8. Cache result ───────────────────────────────────────────────────────
    set_cached_result(contract_text, final_result)

    return final_result
