"""
services/metrics.py
--------------------
Structured observability logging for the GigAudit pipeline.

Emits a single JSON-serialisable log record per request containing all
key performance and cost metrics.  Nothing here touches the API response —
the frontend never sees this data.

Usage (from pipeline.py):
    from services.metrics import log_pipeline_metrics
    log_pipeline_metrics(metadata)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from services.models import PipelineMetadata

logger = logging.getLogger("gigaudit.metrics")


def log_pipeline_metrics(meta: PipelineMetadata) -> None:
    """
    Emit a structured INFO log record for the completed pipeline run.

    The record is JSON-serialisable so it can be ingested by log aggregators
    (Datadog, CloudWatch, Loki, etc.) without additional parsing.

    Metrics emitted:
      - mode               : "single" or "chunked"
      - original_tokens    : token count of the raw contract
      - num_chunks         : number of chunks produced (0 for single-call path)
      - chunk_sizes        : token count per chunk
      - avg_chunk_size     : mean chunk token count
      - map_time_sec       : total parallel auditor stage duration
      - merge_time_sec     : semantic merge + dedup duration
      - debate_time_sec    : debate agent duration
      - judge_time_sec     : judge agent duration
      - total_time_sec     : end-to-end request duration
      - total_llm_calls    : number of Groq API calls made
      - failed_chunks      : chunk indices that failed all retries
      - retry_count        : total retry attempts across all chunks
      - cache_hit          : whether the result was served from Redis
      - auditor_latencies  : per-chunk auditor call duration list
      - cost_estimate_usd  : rough USD cost for this request
    """
    record: dict[str, Any] = {
        "event":              "pipeline_complete",
        "mode":               meta.mode,
        "original_tokens":    meta.original_tokens,
        "num_chunks":         meta.num_chunks,
        "chunk_sizes":        meta.chunk_sizes,
        "avg_chunk_size":     round(meta.avg_chunk_size_tokens, 1),
        "map_time_sec":       round(meta.map_time_sec, 3),
        "merge_time_sec":     round(meta.merge_time_sec, 3),
        "debate_time_sec":    round(meta.debate_time_sec, 3),
        "judge_time_sec":     round(meta.judge_time_sec, 3),
        "total_time_sec":     round(meta.total_time_sec, 3),
        "total_llm_calls":    meta.total_llm_calls,
        "failed_chunks":      meta.failed_chunks,
        "retry_count":        meta.retry_count,
        "cache_hit":          meta.cache_hit,
        "auditor_latencies":  [round(l, 3) for l in meta.auditor_latencies_sec],
        "cost_estimate_usd":  meta.cost_estimate_usd,
    }

    logger.info("METRICS | %s", json.dumps(record))

    # Also log a human-friendly summary to the root logger for easy reading
    # in development (uvicorn --reload terminal output).
    _log_summary(meta)


def _log_summary(meta: PipelineMetadata) -> None:
    """Print a concise human-readable summary to the root logger."""
    mode_label = "SINGLE" if meta.mode == "single" else f"CHUNKED ({meta.num_chunks} chunks)"
    failed_label = (
        f"  ⚠ failed_chunks={meta.failed_chunks}"
        if meta.failed_chunks
        else ""
    )
    root_logger = logging.getLogger(__name__)
    root_logger.info(
        "[metrics] %s | tokens=%d | time=%.2fs | llm_calls=%d | "
        "cost=$%.4f | cache=%s%s",
        mode_label,
        meta.original_tokens,
        meta.total_time_sec,
        meta.total_llm_calls,
        meta.cost_estimate_usd,
        "HIT" if meta.cache_hit else "MISS",
        failed_label,
    )
