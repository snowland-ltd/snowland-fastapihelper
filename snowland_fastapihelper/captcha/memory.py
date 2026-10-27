"""In-process memory cache backend (no external dependency).

Suitable for single-process deployments and tests; the cache is NOT shared
between processes or workers.

Expired entries are reclaimed in two ways:

* *Lazily* -- the next ``get``/``exists`` that touches an expired key drops it.
* *Proactively* -- a daemon sweeper thread periodically scans and removes every
  entry whose TTL has elapsed, so codes that are generated but never queried
  (e.g. an abandoned verification flow) do not leak memory.
"""
import threading
import time
from typing import Dict, Optional, Tuple

from snowland_fastapihelper.captcha.backends import CacheBackend, register_cache


class MemoryCache(CacheBackend):
    """Process-local cache with lazy expiration and a background sweeper."""

    def __init__(self, sweep_interval: float = 60.0) -> None:
        """
        Args:
            sweep_interval: seconds between background sweeps that purge expired
                entries. Set to ``0`` (or a negative value) to disable the
                sweeper and rely on lazy expiration only.
        """
        self._data: Dict[str, Tuple[str, float]] = {}
        self._lock = threading.Lock()
        self._sweep_interval = sweep_interval
        self._sweeper: Optional[threading.Thread] = None

    async def set(self, key: str, value: str, ttl: int) -> None:
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._data[key] = (value, expires_at)
        # Start the reclamation thread lazily, on first write.
        self._ensure_sweeper()

    async def get(self, key: str) -> Optional[str]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.monotonic() >= expires_at:
                self._data.pop(key, None)
                return None
            return value

    async def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)

    async def exists(self, key: str) -> bool:
        return await self.get(key) is not None

    def clear(self) -> None:
        """Remove every entry (mainly useful in tests)."""
        with self._lock:
            self._data.clear()

    # --- background sweeper -------------------------------------------------
    def _ensure_sweeper(self) -> None:
        """Start the daemon sweeper thread once, if enabled and not running."""
        if self._sweep_interval <= 0:
            return
        with self._lock:
            if self._sweeper is not None:
                return
            # Reserve the slot so a concurrent caller does not spawn a second
            # thread before we finish starting this one.
            self._sweeper = _STARTING
        thread = threading.Thread(
            target=self._sweep_loop, name="MemoryCache-sweeper", daemon=True
        )
        thread.start()
        with self._lock:
            self._sweeper = thread

    def _sweep_loop(self) -> None:
        while True:
            time.sleep(self._sweep_interval)
            self._sweep_expired()

    def _sweep_expired(self) -> None:
        now = time.monotonic()
        with self._lock:
            expired = [k for k, (_, exp) in self._data.items() if now >= exp]
            for k in expired:
                self._data.pop(k, None)


# Sentinel used to reserve the sweeper slot before the thread object exists.
_STARTING = object()


# Built-in backend: available without installing redis.
register_cache("memory", MemoryCache)
