"""Redis cache backend (optional dependency: redis).

Importing this module registers the ``"redis"`` backend. It requires the
``redis`` package (``pip install redis``) and is only imported on demand, so the
captcha module works without redis installed.
"""
import os
from typing import Optional

from redis.asyncio import Redis

from snowland_fastapihelper.captcha.backends import CacheBackend, register_cache

DEFAULT_REDIS_URL = "redis://localhost:6379/0"
REDIS_URL_ENV = "REDIS_URL"


class RedisCache(CacheBackend):
    """Redis-backed cache, shared across processes and workers.

    Attributes:
        url: redis connection URL, used when no client is supplied.
        client: an existing ``redis.asyncio.Redis`` client to reuse.
        key_prefix: optional namespace prefix added to every key.
    """

    def __init__(
        self,
        url: str = DEFAULT_REDIS_URL,
        client: Optional[Redis] = None,
        key_prefix: str = "",
    ) -> None:
        self._client = client or Redis.from_url(url, decode_responses=True)
        self._key_prefix = key_prefix

    def _key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self._client.set(self._key(key), value, ex=ttl)

    async def get(self, key: str) -> Optional[str]:
        return await self._client.get(self._key(key))

    async def delete(self, key: str) -> None:
        await self._client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(self._key(key)))

    async def aclose(self) -> None:
        """Close the underlying redis client."""
        # redis>=5 exposes aclose(); older versions only have close().
        close = getattr(self._client, "aclose", None) or self._client.close
        await close()


def _default_factory() -> RedisCache:
    return RedisCache(url=os.getenv(REDIS_URL_ENV, DEFAULT_REDIS_URL))


register_cache("redis", _default_factory)
