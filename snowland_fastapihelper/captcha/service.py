"""Captcha generation and verification.

Two independent time windows control the lifecycle of a captcha:

* ``expire_seconds`` - validity window. Verification succeeds only inside it;
  after it the code can no longer be used.
* ``retain_seconds`` - how long the record is kept in the cache (must be
  >= ``expire_seconds``). The extra time after expiry is what lets callers tell
  "this code expired" apart from "no code was ever generated for this principal".

Resulting verification outcomes:

* ``SUCCESS`` - a record exists, is still valid and the code matches.
* ``MISMATCH`` - a valid record exists but the submitted code differs.
* ``EXPIRED`` - a record exists but is past its validity window (still retained).
* ``NOT_FOUND`` - no record at all: never generated, or purged past retention.
"""
import json
import math
import time
from astartool.random import random_digit_string
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from snowland_fastapihelper.auth import AbstractBaseUser
from snowland_fastapihelper.captcha.backends import CacheBackend, get_cache
from snowland_fastapihelper.captcha.config import CaptchaConfig


class VerifyStatus(Enum):
    """Outcome of a captcha verification."""

    SUCCESS = "success"
    EXPIRED = "expired"
    NOT_FOUND = "not_found"
    MISMATCH = "mismatch"


@dataclass
class CaptchaRecord:
    """Stored representation of an issued captcha code.

    Attributes:
        code: the code value that was issued.
        created_at: unix timestamp (seconds) when the code was generated.
        expire_seconds: validity window captured at generation time, so a
            surviving record can still be judged even if config changes later.
    """

    code: str
    created_at: float
    expire_seconds: int

    def expires_at(self) -> float:
        """Unix timestamp after which the code can no longer be used."""
        return self.created_at + self.expire_seconds

    def to_json(self) -> str:
        return json.dumps(
            {
                "code": self.code,
                "created_at": self.created_at,
                "expire_seconds": self.expire_seconds,
            }
        )

    @classmethod
    def from_json(cls, raw: str) -> "CaptchaRecord":
        data = json.loads(raw)
        return cls(
            code=data["code"],
            created_at=data["created_at"],
            expire_seconds=data["expire_seconds"],
        )


class CaptchaService:
    """Issue and verify captcha codes for a principal."""

    def __init__(
        self,
        cache: Optional[CacheBackend] = None,
        config: Optional[CaptchaConfig] = None,
        key_prefix: str = "captcha:",
    ) -> None:
        """
        Args:
            cache: cache backend to store records in; defaults to ``get_cache("memory")``.
            config: timing settings; defaults to ``CaptchaConfig()``.
            key_prefix: namespace prefix for every cache key.
        """
        self._cache = cache if cache is not None else get_cache("memory")
        self._config = config if config is not None else CaptchaConfig()
        self._key_prefix = key_prefix

    @property
    def config(self) -> CaptchaConfig:
        """Timing settings currently in use."""
        return self._config

    def _key(self, principal: AbstractBaseUser) -> str:
        return f"{self._key_prefix}{principal.identity_key}"

    async def generate(
        self,
        principal: AbstractBaseUser,
        *,
        code: Optional[str] = None,
        length: Optional[int] = None,
    ) -> str:
        """Issue a new code for ``principal``, replacing any existing one.

        Codes are produced with ``astartool.random.random_digit_string``, a
        cryptographically secure source (SystemRandom), so they are not
        guessable.

        Args:
            principal: the identity the code is bound to.
            code: use this exact code instead of a generated one (useful in tests).
            length: override ``config.code_length`` for this code.

        Returns:
            The issued code, so the caller can deliver it (SMS / email / ...).
        """
        new_code = (
            code
            if code is not None
            else random_digit_string(length or self._config.code_length)
        )
        record = CaptchaRecord(
            code=new_code,
            created_at=time.time(),
            expire_seconds=self._config.expire_seconds,
        )
        # The cache entry lives for the retention window, not just the validity
        # window, so an expired code can still be reported as EXPIRED.
        await self._cache.set(
            self._key(principal), record.to_json(), self._config.retain_seconds
        )
        return new_code

    async def verify(
        self, principal: AbstractBaseUser, code: str, *, consume: bool = True
    ) -> VerifyStatus:
        """Verify ``code`` for ``principal``.

        Args:
            principal: the identity the code was issued for.
            code: the code submitted by the user.
            consume: when True (default) a successful check deletes the record,
                making the code single-use.

        Returns:
            A ``VerifyStatus`` distinguishing success, mismatch, expired and
            never-generated.
        """
        raw = await self._cache.get(self._key(principal))
        if raw is None:
            return VerifyStatus.NOT_FOUND

        record = CaptchaRecord.from_json(raw)
        if time.time() >= record.expires_at():
            return VerifyStatus.EXPIRED
        if record.code != code:
            return VerifyStatus.MISMATCH

        if consume:
            await self._cache.delete(self._key(principal))
        return VerifyStatus.SUCCESS

    async def invalidate(self, principal: AbstractBaseUser) -> None:
        """Discard any code currently issued for ``principal``."""
        await self._cache.delete(self._key(principal))

    async def remaining_seconds(self, principal: AbstractBaseUser) -> Optional[int]:
        """Seconds left before the current code expires.

        Returns None when there is no record, and 0 when it already expired but
        is still retained.
        """
        raw = await self._cache.get(self._key(principal))
        if raw is None:
            return None
        record = CaptchaRecord.from_json(raw)
        left = record.expires_at() - time.time()
        # Round up so a code that is still valid never reports 0 seconds left.
        return max(0, math.ceil(left))
