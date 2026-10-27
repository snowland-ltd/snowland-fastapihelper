"""Captcha (verification code) support.

Provides a pluggable cache system (memory built-in, redis optional) and the
``CaptchaService`` that issues and verifies codes with separate expiry and
retention windows.

Codes are bound to an identity from ``snowland_fastapihelper.auth``
(``User`` / ``VirtualUser`` or any ``AbstractBaseUser`` subclass); this module
deliberately does not define user classes itself.

The redis backend lives in ``snowland_fastapihelper.captcha.redis_cache`` and is
imported on demand, so redis is never required to use this module.
"""
from snowland_fastapihelper.captcha.backends import (
    CacheBackend,
    CacheRegistry,
    get_cache,
    register_cache,
)
from snowland_fastapihelper.captcha.config import CaptchaConfig
from snowland_fastapihelper.captcha.memory import MemoryCache
from snowland_fastapihelper.captcha.service import (
    CaptchaRecord,
    CaptchaService,
    VerifyStatus,
)

__all__ = [
    "CacheBackend",
    "CacheRegistry",
    "get_cache",
    "register_cache",
    "CaptchaConfig",
    "MemoryCache",
    "CaptchaRecord",
    "CaptchaService",
    "VerifyStatus",
]
