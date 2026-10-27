# Release Notes — v0.2.0

**Release date:** 2026-10-27

## Highlights

- Two new feature packages: **identity & users** (`auth`) and **verification codes**
  (`captcha`).
- Verification codes now use a **cryptographically secure** random source
  (`SystemRandom`) instead of the predictable `random` module.
- The in-process memory cache now **proactively reclaims expired entries** via a
  background sweeper — closing the memory-leak path for codes that are generated
  but never verified.
- The package **version is single-sourced** from `snowland_fastapihelper.__version__`.

## New Features

### Identity & users — `snowland_fastapihelper.auth`

Modelled after `django.contrib.auth`. All identity primitives live here so other
features (e.g. captcha) depend only on the contract, not on user classes.

- `AbstractBaseUser` — minimal identity contract (`identity_key`).
- `AbstractUser` / `User` — real user accounts (`uuid` → `users.uuid`, optional
  `tenant_id` / `merchant_id` for data isolation).
- `VirtualUser` — account-less identity (e.g. a phone number before registration).
- `get_user_model()` / `set_user_model()` — swap the active user model.

### Captcha — `snowland_fastapihelper.captcha`

An ORM-agnostic verification-code service.

- Two time windows: **expiry** (validity) vs **retention** (record kept, ≥ expiry),
  so "expired" can be told apart from "never generated".
- `CaptchaService.generate` / `verify` / `invalidate` / `remaining_seconds`.
- `VerifyStatus`: `SUCCESS` / `MISMATCH` / `EXPIRED` / `NOT_FOUND`.
- Backends: built-in `MemoryCache`, or optional `RedisCache` (`redis` extra) shared
  across workers.

## Improvements

- **Secure code generation** — switched from the pseudo-random `random` module to
  `astartool.random.random_digit_string` (SystemRandom-backed), so codes cannot be
  predicted or replayed.
- **MemoryCache sweeper** — a daemon thread periodically evicts expired entries.
  Previously expiry was lazy-only (on access), which could leak memory for codes
  that were generated but never queried.

## Packaging

- The version is now read from `snowland_fastapihelper.__version__`
  (`pyproject.toml` uses `dynamic = ["version"]`). The publish workflow builds with
  `--no-isolation` and pre-installs runtime deps (`fastapi`, `starlette`, `astartool`)
  so the version can be resolved.
- `redis` remains an **optional dependency** (extra) for the Redis captcha backend.

## Upgrade Notes

- No breaking changes to the v0.1.x surface (`response`, `exceptions`, `app` factory,
  `database`). `auth` / `captcha` are additive subpackages.
- If you run **multiple workers / processes**, use the Redis backend for the captcha
  cache so codes are shared; `MemoryCache` is per-process.
- Redis keys carry a server-side TTL (`retain_seconds`), so Redis reclaims expired
  codes on its own — no sweeper needed there.

## API Reference

See [`api_v0_2_0.md`](api_v0_2_0.md).
