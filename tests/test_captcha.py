"""Unit tests for the captcha module (stdlib unittest)."""
import asyncio
import threading
import unittest

from snowland_fastapihelper.auth import User, VirtualUser
from snowland_fastapihelper.captcha import (
    CaptchaConfig,
    CaptchaService,
    MemoryCache,
    VerifyStatus,
    get_cache,
)


class TestPrincipals(unittest.TestCase):
    def test_user_identity_key(self):
        user = User(uuid="u-1", merchant_id="m-1")
        self.assertEqual(user.identity_key, "user:u-1")

    def test_user_requires_uuid(self):
        with self.assertRaises(ValueError):
            User(uuid="")

    def test_virtual_user_identity_key(self):
        virtual = VirtualUser(identity_type="phone", identity_value="+86138")
        self.assertEqual(virtual.identity_key, "virtual:phone:+86138")

    def test_virtual_user_requires_identity(self):
        with self.assertRaises(ValueError):
            VirtualUser(identity_type="phone", identity_value="")

    def test_principals_do_not_collide(self):
        user = User(uuid="u-1")
        virtual = VirtualUser(identity_type="phone", identity_value="u-1")
        self.assertNotEqual(user.identity_key, virtual.identity_key)


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        config = CaptchaConfig()
        self.assertEqual(config.expire_seconds, 300)
        self.assertEqual(config.retain_seconds, 900)
        self.assertEqual(config.code_length, 6)

    def test_retain_must_cover_expire(self):
        with self.assertRaises(ValueError):
            CaptchaConfig(expire_seconds=10, retain_seconds=5)

    def test_expire_must_be_positive(self):
        with self.assertRaises(ValueError):
            CaptchaConfig(expire_seconds=0)


class TestMemoryCache(unittest.IsolatedAsyncioTestCase):
    async def test_set_get_delete(self):
        cache = MemoryCache()
        await cache.set("k", "v", 60)
        self.assertEqual(await cache.get("k"), "v")
        self.assertTrue(await cache.exists("k"))
        await cache.delete("k")
        self.assertIsNone(await cache.get("k"))

    async def test_ttl_expires_entry(self):
        cache = MemoryCache()
        await cache.set("k", "v", 1)
        self.assertEqual(await cache.get("k"), "v")
        await asyncio.sleep(1.05)
        self.assertIsNone(await cache.get("k"))
        self.assertFalse(await cache.exists("k"))


class TestMemoryCacheSweeper(unittest.IsolatedAsyncioTestCase):
    async def test_sweeper_reclaims_unqueried_entries(self):
        # A very short interval so the test stays fast.
        cache = MemoryCache(sweep_interval=0.05)
        # Never call get/exists on this key -- it must still be reclaimed.
        await cache.set("orphan", "v", 0.05)
        self.assertIsInstance(cache._sweeper, threading.Thread)
        self.assertTrue(cache._sweeper.daemon)
        await asyncio.sleep(0.3)
        self.assertIsNone(await cache.get("orphan"))
        with cache._lock:
            self.assertEqual(len(cache._data), 0)

    async def test_disabled_sweeper_keeps_unqueried_entry(self):
        cache = MemoryCache(sweep_interval=0)  # sweeper disabled
        self.assertIsNone(cache._sweeper)
        await cache.set("orphan", "v", 0.05)
        await asyncio.sleep(0.2)
        # No sweeper and never queried -> the entry lingers (lazy only).
        with cache._lock:
            self.assertEqual(len(cache._data), 1)


class TestCacheRegistry(unittest.TestCase):
    def test_memory_registered_by_default(self):
        self.assertIsInstance(get_cache("memory"), MemoryCache)

    def test_shared_instance(self):
        self.assertIs(get_cache("memory"), get_cache("memory"))

    def test_unknown_backend_raises(self):
        with self.assertRaises(KeyError):
            get_cache("__no_such_backend__")


class TestCaptchaService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.cache = MemoryCache()
        self.service = CaptchaService(
            cache=self.cache,
            config=CaptchaConfig(expire_seconds=1, retain_seconds=5),
        )
        self.principal = VirtualUser(identity_type="phone", identity_value="+8613800000000")

    async def test_generate_then_verify_success(self):
        code = await self.service.generate(self.principal)
        self.assertEqual(len(code), 6)
        self.assertEqual(
            await self.service.verify(self.principal, code), VerifyStatus.SUCCESS
        )

    async def test_custom_code_and_length(self):
        await self.service.generate(self.principal, code="1234")
        self.assertEqual(
            await self.service.verify(self.principal, "1234"), VerifyStatus.SUCCESS
        )
        long_code = await self.service.generate(self.principal, length=8)
        self.assertEqual(len(long_code), 8)

    async def test_wrong_code_is_mismatch(self):
        code = await self.service.generate(self.principal)
        self.assertEqual(
            await self.service.verify(self.principal, code + "0"), VerifyStatus.MISMATCH
        )

    async def test_not_found_when_never_generated(self):
        self.assertEqual(
            await self.service.verify(self.principal, "123456"), VerifyStatus.NOT_FOUND
        )

    async def test_expired_is_distinct_from_not_found(self):
        # Retention (5s) outlives expiry (1s), so once expired the service can
        # still report EXPIRED instead of NOT_FOUND.
        code = await self.service.generate(self.principal)
        await asyncio.sleep(1.05)
        self.assertEqual(
            await self.service.verify(self.principal, code), VerifyStatus.EXPIRED
        )

    async def test_consume_makes_code_single_use(self):
        code = await self.service.generate(self.principal)
        await self.service.verify(self.principal, code)
        self.assertEqual(
            await self.service.verify(self.principal, code), VerifyStatus.NOT_FOUND
        )

    async def test_keep_code_when_not_consumed(self):
        code = await self.service.generate(self.principal)
        await self.service.verify(self.principal, code, consume=False)
        self.assertEqual(
            await self.service.verify(self.principal, code), VerifyStatus.SUCCESS
        )

    async def test_invalidate(self):
        code = await self.service.generate(self.principal)
        await self.service.invalidate(self.principal)
        self.assertEqual(
            await self.service.verify(self.principal, code), VerifyStatus.NOT_FOUND
        )

    async def test_regenerate_replaces_previous_code(self):
        old = await self.service.generate(self.principal)
        new = await self.service.generate(self.principal)
        self.assertEqual(
            await self.service.verify(self.principal, old), VerifyStatus.MISMATCH
        )
        self.assertEqual(
            await self.service.verify(self.principal, new), VerifyStatus.SUCCESS
        )

    async def test_codes_are_isolated_per_principal(self):
        code = await self.service.generate(self.principal)
        other = VirtualUser(identity_type="phone", identity_value="+8613911111111")
        self.assertEqual(
            await self.service.verify(other, code), VerifyStatus.NOT_FOUND
        )

    async def test_remaining_seconds(self):
        await self.service.generate(self.principal)
        remaining = await self.service.remaining_seconds(self.principal)
        self.assertIsNotNone(remaining)
        self.assertGreater(remaining, 0)
        await self.service.invalidate(self.principal)
        self.assertIsNone(await self.service.remaining_seconds(self.principal))

    async def test_works_with_real_user(self):
        user = User(uuid="u-1", merchant_id="m-1")
        code = await self.service.generate(user)
        self.assertEqual(
            await self.service.verify(user, code), VerifyStatus.SUCCESS
        )


if __name__ == "__main__":
    unittest.main()
