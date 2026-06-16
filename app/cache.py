"""A tiny async-safe in-memory TTL cache.

Good enough for a single-process app: weather forecasts only change slowly, so
we cache normalized provider results for a while to stay friendly to the free
APIs and to make repeated lookups instant.
"""

import asyncio
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl: int) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl, value)


cache = TTLCache()
