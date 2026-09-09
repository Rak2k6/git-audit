"""
services/cache.py
-----------------
Optional Redis-backed result cache for the GigAudit pipeline.

Design:
  - Cache key: SHA-256 of normalised contract text, prefixed with CACHE_KEY_PREFIX.
  - Value:     JSON-serialised final result dict.
  - TTL:       CACHE_TTL_SECONDS (default 1 hour).

Graceful degradation:
  - If Redis is not configured / unreachable, ALL cache operations are no-ops
    and a single WARNING is emitted at first connection attempt.
  - The pipeline continues without caching — no exceptions are propagated.

This means developers can work locally without running Redis.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from services.config import CACHE_KEY_PREFIX, CACHE_TTL_SECONDS, REDIS_URL

logger = logging.getLogger(__name__)

# ── Lazy Redis client — only attempted on first use ───────────────────────────
_redis_client = None
_redis_warned = False          # emit the "Redis unavailable" warning only once
_redis_available = False       # set to True on first successful connection


def _get_redis():
    """
    Return a connected Redis client, or None if Redis is unavailable.

    Imports and connects lazily so that environments without Redis do not
    raise ImportError or ConnectionError at module import time.
    """
    global _redis_client, _redis_warned, _redis_available

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    try:
        import redis as _redis_lib  # optional dependency

        client = _redis_lib.from_url(REDIS_URL, socket_connect_timeout=2)
        client.ping()  # confirm the connection is live
        _redis_client = client
        _redis_available = True
        logger.info("[cache] Redis connected at %s — caching enabled.", REDIS_URL)
        return _redis_client

    except ImportError:
        if not _redis_warned:
            logger.warning(
                "[cache] 'redis' package not installed — caching disabled. "
                "Install with: pip install redis"
            )
            _redis_warned = True
        _redis_client = None
        return None

    except Exception as exc:
        if not _redis_warned:
            logger.warning(
                "[cache] Redis unavailable at %s (%s) — caching disabled. "
                "The pipeline will run without caching.",
                REDIS_URL,
                exc,
            )
            _redis_warned = True
        _redis_client = None
        return None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_key(contract_text: str) -> str:
    """
    Derive a deterministic cache key from the contract text.

    Normalisation (strip + lower) ensures that contracts differing only in
    leading/trailing whitespace or case hit the same cache entry.
    """
    normalised = contract_text.strip().lower()
    digest = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return f"{CACHE_KEY_PREFIX}{digest}"


# ── Public API ────────────────────────────────────────────────────────────────

def get_cached_result(contract_text: str) -> dict[str, Any] | None:
    """
    Look up a previously computed result for *contract_text*.

    Returns the cached result dict, or None on cache miss / Redis unavailability.
    """
    client = _get_redis()
    if client is None:
        return None

    key = _make_key(contract_text)
    try:
        raw = client.get(key)
        if raw:
            logger.info("[cache] Cache HIT for key %s…", key[:24])
            return json.loads(raw)
        logger.debug("[cache] Cache MISS for key %s…", key[:24])
        return None
    except Exception as exc:
        logger.warning("[cache] GET failed: %s — proceeding without cache.", exc)
        return None


def set_cached_result(contract_text: str, result: dict[str, Any]) -> None:
    """
    Store *result* in Redis with TTL = CACHE_TTL_SECONDS.

    Silently skips if Redis is unavailable.
    """
    client = _get_redis()
    if client is None:
        return

    key = _make_key(contract_text)
    try:
        client.setex(key, CACHE_TTL_SECONDS, json.dumps(result))
        logger.info("[cache] Stored result under key %s… (TTL=%ds)", key[:24], CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("[cache] SET failed: %s — result will not be cached.", exc)
