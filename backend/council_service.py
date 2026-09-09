"""
council_service.py
------------------
Backward-compatible shim.

All pipeline logic has been refactored into the services/ package:

    services/config.py        ← pipeline configuration constants
    services/models.py        ← Pydantic typed models
    services/token_counter.py ← token counting + budget check
    services/chunker.py       ← section-aware + fallback chunking
    services/auditor.py       ← Auditor agent (Agent 1)
    services/merge.py         ← semantic merge + deduplication (Reduce stage)
    services/debate.py        ← Debate agent (Agent 2)
    services/judge.py         ← Judge agent (Agent 3)
    services/cache.py         ← optional Redis result cache
    services/metrics.py       ← structured observability logging
    services/pipeline.py      ← async orchestrator (run_council)

This file exists solely so that the FastAPI route in main.py can continue
to use `from council_service import run_council` without modification.
"""

from services.pipeline import run_council  # noqa: F401 — re-exported for main.py

__all__ = ["run_council"]
