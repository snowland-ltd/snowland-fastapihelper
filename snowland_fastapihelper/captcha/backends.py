"""Cache backend abstraction and registry used to store captcha records.

Business code depends on the ``CacheBackend`` interface; the concrete
implementation (memory or redis) is selected by name via ``get_cache`` or
injected directly. The registry keeps one shared instance per name so stored
codes survive across calls.
"""
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

CacheFactory = Callable[[], "CacheBackend"]


class CacheBackend(ABC):
    """Minimal async key/value interface used to store captcha records."""

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int) -> None:
        """Store ``value`` under ``key`` for ``ttl`` seconds."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Return the value for ``key``, or None when missing or expired."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove ``key`` from the cache."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True when ``key`` is present and not expired."""


class CacheRegistry:
    """Name -> cache backend mapping, holding one shared instance per name."""

    def __init__(self) -> None:
        self._factories: Dict[str, CacheFactory] = {}
        self._instances: Dict[str, CacheBackend] = {}

    def register(self, name: str, factory: CacheFactory) -> None:
        """Register a backend factory; any cached instance is discarded."""
        self._factories[name] = factory
        self._instances.pop(name, None)

    def get(self, name: str) -> CacheBackend:
        """Return the shared backend instance registered under ``name``."""
        if name not in self._factories:
            raise KeyError(
                f"unregistered cache backend: {name!r}; "
                f"registered: {sorted(self._factories)}"
            )
        if name not in self._instances:
            self._instances[name] = self._factories[name]()
        return self._instances[name]


# The single global registry instance.
registry = CacheRegistry()


def register_cache(name: str, factory: CacheFactory) -> None:
    """Register a cache backend factory under ``name``."""
    registry.register(name, factory)


def get_cache(name: str = "memory") -> CacheBackend:
    """Return the shared cache backend registered under ``name``."""
    return registry.get(name)
