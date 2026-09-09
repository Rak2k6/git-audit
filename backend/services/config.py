"""
services/config.py
------------------
Single source of truth for every pipeline configuration constant.

All knobs are readable from environment variables so they can be overridden
in production without touching code.

Design principle: nothing in the pipeline is hardcoded — every numeric
threshold is derived from the constants declared here.
"""

from __future__ import annotations

import os

# ── Token budget ─────────────────────────────────────────────────────────────
# Contracts whose token count is below this threshold are analysed in a single
# LLM call (the existing fast path).  Contracts above this threshold enter the
# chunked Map-Reduce pipeline.
MAX_SINGLE_ANALYSIS: int = int(os.getenv("MAX_SINGLE_ANALYSIS", "6000"))

# ── Dynamic chunk size ────────────────────────────────────────────────────────
# Chunk size is NOT hardcoded.  It is computed from the model's context window
# minus the tokens consumed by system prompts and JSON scaffolding.
# Swap the model → adjust MODEL_CONTEXT_WINDOW → chunk size adapts automatically.
MODEL_CONTEXT_WINDOW: int   = int(os.getenv("MODEL_CONTEXT_WINDOW",   "8192"))
PROMPT_OVERHEAD_TOKENS: int = int(os.getenv("PROMPT_OVERHEAD_TOKENS", "1200"))
SAFETY_MARGIN_TOKENS: int   = int(os.getenv("SAFETY_MARGIN_TOKENS",   "500"))

# Derived at import time — available everywhere as config.CHUNK_SIZE
CHUNK_SIZE: int = MODEL_CONTEXT_WINDOW - PROMPT_OVERHEAD_TOKENS - SAFETY_MARGIN_TOKENS
# Default: 8192 - 1200 - 500 = 6492 tokens

# Number of tokens to overlap between consecutive chunks so that clauses
# crossing chunk boundaries are not silently dropped.
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

# ── Concurrency ───────────────────────────────────────────────────────────────
# Whether to run auditor agents in parallel using asyncio.gather().
ENABLE_PARALLEL: bool = os.getenv("ENABLE_PARALLEL", "true").lower() == "true"

# Maximum number of concurrent LLM calls during the Map stage.
# asyncio.Semaphore(MAX_CONCURRENT_CHUNKS) ensures we never blast the
# Groq API with more than this many simultaneous requests.
MAX_CONCURRENT_CHUNKS: int = int(os.getenv("MAX_CONCURRENT_CHUNKS", "5"))

# ── Retry / fault tolerance ───────────────────────────────────────────────────
# How many times to retry a failed auditor chunk call before giving up.
MAX_CHUNK_RETRIES: int = int(os.getenv("MAX_CHUNK_RETRIES", "2"))

# Base delay (seconds) for exponential backoff.
# Attempt 0 → 1 s, attempt 1 → 2 s, attempt 2 → 4 s …
RETRY_BASE_DELAY_SEC: float = float(os.getenv("RETRY_BASE_DELAY_SEC", "1.0"))

# ── Semantic deduplication ────────────────────────────────────────────────────
# When True, the merge stage uses sentence-transformer embeddings + cosine
# similarity to detect semantically equivalent clauses across chunks.
# When False, it falls back to normalised-string exact matching (cheaper,
# no model download required).
ENABLE_SEMANTIC_DEDUP: bool = (
    os.getenv("ENABLE_SEMANTIC_DEDUP", "true").lower() == "true"
)

# Cosine similarity threshold above which two clause excerpts are considered
# duplicates and are merged into one finding.
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.85"))

# Hugging Face model used for excerpt embeddings.  all-MiniLM-L6-v2 is fast,
# lightweight (~80 MB), and runs on CPU with no GPU required.
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# ── Caching ───────────────────────────────────────────────────────────────────
# Redis connection URL.  If Redis is unreachable, caching is silently skipped
# — the pipeline degrades gracefully with a warning log.
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

# Time-to-live for cached results (seconds).  Default: 1 hour.
CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))

# Cache key prefix — bump the version suffix when the output schema changes
# to avoid serving stale cached results after a schema update.
CACHE_KEY_PREFIX: str = "gigaudit:v1:"

# ── Cost estimation ───────────────────────────────────────────────────────────
# Approximate USD cost per 1 000 tokens for the Groq-hosted llama-3.3-70b.
# Used only for log-level cost estimates — not billing-accurate.
COST_PER_1K_TOKENS_USD: float = float(
    os.getenv("COST_PER_1K_TOKENS_USD", "0.00059")
)
