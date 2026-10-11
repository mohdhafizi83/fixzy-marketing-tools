"""Tiny in-memory fixed-window rate limiter (stdlib only, no new deps).

Two primitives so callers choose what counts as a "hit":
  * webhooks: every request records a hit (flood protection)
  * admin auth: only FAILED logins record a hit (a browser re-sends Basic
    auth on every page load; counting successes would lock out the admin)

Buckets live in process memory: correct for the single-process deployment
this app targets (Flask dev/gunicorn workers each get their own window,
which is fine for brute-force/flood friction). Not a distributed limiter.
"""
import threading
import time

_lock = threading.Lock()
# key -> list of monotonic timestamps of recorded hits
_buckets: dict[str, list[float]] = {}
_MAX_KEYS = 10_000  # memory guard: prune stale keys if IPs churn


def _prune(key: str, window_s: float, now: float) -> list[float]:
    hits = [t for t in _buckets.get(key, []) if now - t < window_s]
    _buckets[key] = hits
    return hits


def is_blocked(key: str, limit: int, window_s: float = 60.0) -> bool:
    """True if this key already has >= limit hits inside the window."""
    now = time.monotonic()
    with _lock:
        return len(_prune(key, window_s, now)) >= limit


def record(key: str, window_s: float = 60.0) -> None:
    """Record one hit for this key."""
    now = time.monotonic()
    with _lock:
        if len(_buckets) > _MAX_KEYS:
            for k in [k for k, v in _buckets.items()
                      if not any(now - t < window_s for t in v)]:
                del _buckets[k]
        _prune(key, window_s, now).append(now)


def reset() -> None:
    """Clear all buckets (tests)."""
    with _lock:
        _buckets.clear()
