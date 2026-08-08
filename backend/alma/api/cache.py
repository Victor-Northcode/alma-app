"""The process-wide calculation cache.

One instance, created lazily, shared by every request. A year of transits
costs about a second of CPU and is identical for the same birth on the same
day, so the difference between having this and not having it is the
difference between a page that opens and a page that spins.
"""

from __future__ import annotations

from functools import lru_cache

from ..calc.cache import MemoryCache


@lru_cache(maxsize=1)
def result_cache() -> MemoryCache:
    return MemoryCache(capacity=2048)
