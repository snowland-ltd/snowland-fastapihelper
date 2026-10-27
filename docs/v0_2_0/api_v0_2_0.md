# snowland-fastapihelper API Reference (v0.2.0)

This document describes every public API of `snowland_fastapihelper` with its
inputs, outputs and behavior. See the code for the authoritative definition.

> Chinese version: [api_v0_2_0.zh.md](api_v0_2_0.zh.md)

---

## 1. Unified Response — `snowland_fastapihelper.response`

All endpoints share a fixed 4-field envelope:

| Field        | Type    | Meaning                                            |
|--------------|---------|----------------------------------------------------|
| `successful` | bool    | `true` on success, `false` on failure              |
| `code`       | int     | `0` on success; an `astartool.common.ErrorCode` value otherwise |
| `message`    | str     | Human-readable message (`"ok"` on success)         |
| `data`       | any     | Payload, or `null` on failure                      |

`code` values come from `astartool.common.ErrorCode`.

### `ok(data=None, message="ok") -> dict`
Build a success (non-list) response.
- **Input**: `data` (any payload), `message` (str).
- **Output**: `{"successful": True, "code": 0, "message": message, "data": data}`.

### `ok_list(items, total, page, page_size) -> dict`
Build a success (list) response.
- **Input**: `items` (list), `total` (int, matched count), `page` (int), `page_size` (int).
- **Output**: `{"successful": True, "code": 0, "message": "ok", "data": {"items": items, "total": total, "page": page, "page_size": page_size}}`.

### `fail(code, message, data=None) -> dict`
Build a failure response.
- **Input**: `code` (int), `message` (str), `data` (any, default `None`).
- **Output**: `{"successful": False, "code": code, "message": message, "data": data}`.

### `class Pagination`
Holds parsed pagination params.
- **Constructor**: `Pagination(page: int, page_size: int)`.
- **Attributes**: `page` (int, 1-based), `page_size` (int), `offset` (int = `(page-1)*page_size`), `limit` (int, equals `page_size`).

### `pagination(page=Query(1,ge=1), page_size=Query(20,ge=1,le=200)) -> Pagination`
FastAPI dependency that parses and validates pagination query params.
- **Input**: query params `page` (>=1), `page_size` (1..200).
- **Output**: a `Pagination` instance.

### `http_status_to_code(status_code: int) -> int`
Map an HTTP status to an `ErrorCode` value (for exception handlers).
- **Input**: `status_code` (int).
- **Output**: int. Mapping: `400->1`, `401->3`, `403->10`, `404->9`, `409->5`, `423->6`, `429->8`, `>=500->99`, else `-1`.

### Constants
- `DEFAULT_PAGE_SIZE = 20`
- `MAX_PAGE_SIZE = 200`

---

## 2. Exceptions — `snowland_fastapihelper.exceptions`

### `class BizError(Exception)`
Business exception carrying an `ErrorCode` value and a message; converted to a
unified response by `biz_error_handler`.
- **Constructor**: `BizError(code: int = 1, message: str = "operation failed", data: Any = None)`.
- **Attributes**: `code`, `message`, `data`.

### Handlers (registered via `register_exception_handlers`)
- `biz_error_handler(request, exc: BizError)` → `JSONResponse(200, fail(code, message, data))`.
- `http_exception_handler(request, exc: StarletteHTTPException)` → maps status via `http_status_to_code`, returns `JSONResponse(200, fail(...))`.
- `validation_exception_handler(request, exc: RequestValidationError)` → `JSONResponse(200, fail(2, "request validation failed", exc.errors()))`.
- `unhandled_exception_handler(request, exc: Exception)` → `JSONResponse(200, fail(99, "internal server error", None))` (fallback; no stack trace leaked).

> Note: every handler returns **HTTP 200** with the unified body; success/failure
> is expressed via `successful`/`code`.

### `register_exception_handlers(app: FastAPI) -> None`
Register all the handlers above onto a FastAPI app.

---

## 3. App Factory — `snowland_fastapihelper.app`

### `create_app(*args, **kwargs) -> FastAPI`
Create a `FastAPI` app and wire up the unified exception handlers.
- **Input**: same as `FastAPI(...)`.
- **Output**: a `FastAPI` instance with exception handlers registered.

```python
from snowland_fastapihelper import create_app
app = create_app(title="My API")
```

---

## 4. Database Abstraction — `snowland_fastapihelper.database`

ORM-agnostic. Business code depends only on `get_crud(model, session)`; the
concrete ORM (SQLAlchemy here) is a self-registered backend.

### `class CRUDProtocol(ABC, Generic[ModelType])`
Unified CRUD interface every backend must implement.

| Method | Input | Output |
|--------|-------|--------|
| `create(**kwargs)` | field values | created model instance |
| `get_by_uuid(uuid, *, include_deleted=False)` | uuid str | instance or `None` |
| `list(*, page=1, page_size=20, include_deleted=False, **filters)` | pagination + equality filters | `(items: Sequence, total: int)` |
| `update(uuid, **kwargs)` | fields to set | updated instance or `None` |
| `soft_delete(uuid)` | uuid str | `True` if marked deleted, else `False` |
| `delete(uuid)` | uuid str | `True` if physically removed, else `False` |

Conventions:
- `list` returns `(items, total)` where `total` is the matched count.
- `get_by_uuid`/`list` filter out soft-deleted rows by default; `include_deleted=True` forces inclusion.
- `soft_delete` sets a logical-delete flag; `delete` removes the row physically.

### `get_crud(model, session, *, backend=None) -> CRUDProtocol`
Unified entry point. Dispatches to the backend matching `type(session)`
(default), or to the named backend when `backend=` is given.
- **Input**: `model` (model class), `session` (ORM session), `backend` (str, optional).
- **Output**: a `CRUDProtocol` instance.
- **Raises**: `TypeError` (no backend for session type), `KeyError` (unknown `backend=` name).

### `register_backend(name, session_type, factory) -> None`
Register a CRUD factory for an ORM backend. `factory` is `(model, session) -> CRUDProtocol`.
- Used by backends for self-registration (e.g. SQLAlchemy registers on import).

### `class BackendRegistry`
Holds the `session type -> factory` mapping and does dispatch. A global instance
`registry` is exposed; `get_crud`/`register_backend` operate on it.

---

## 5. SQLAlchemy Backend — `snowland_fastapihelper.database.sqlalchemy`

*(optional dependency: `sqlalchemy`)* — import this subpackage to auto-register
the backend; `get_crud` then dispatches `AsyncSession` to it.

### Models — `models.py`
- `class Base(DeclarativeBase)`: declarative base for all models.
- `class GUID(TypeDecorator)`: UUID field; native UUID on PostgreSQL, `CHAR(36)` elsewhere. `gen_uuid()` returns a UUID string default.
- `class UuidMixin`: adds `uuid` (unique, indexed business primary key).
- `class TimestampMixin`: adds `created_at`, `updated_at` (UTC, timezone-aware).
- `class TenantMixin`: adds `tenant_id` (GUID, FK to `tenants.uuid`, indexed).
- `class MerchantMixin`: adds `merchant_id` (GUID, indexed; no DB FK, app-enforced).
- `class SoftDeleteMixin`: adds `is_deleted` (bool, default `False`).

> Note: `Base`/`UuidMixin` expose a business `uuid` but do **not** declare a DB
> primary key. Declare your own `id` autoincrement PK on each model.

### CRUD — `crud.py`
- `class CRUD(CRUDProtocol, Generic[ModelType])`: async CRUD bound to a SQLAlchemy
  `AsyncSession`. Implements all `CRUDProtocol` methods; auto-applies
  `SoftDeleteMixin` filtering; raises `AttributeError` on unknown filter/update
  field, `TypeError` on `soft_delete` when the model lacks `SoftDeleteMixin`.

### Example
```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from snowland_fastapihelper import (
    Base, UuidMixin, TimestampMixin, SoftDeleteMixin, get_crud,
)

class User(Base, UuidMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)

async def create_user(session: AsyncSession, name: str):
    return await get_crud(User, session).create(name=name)
```

---

## 6. Top-level Exports — `snowland_fastapihelper`

Always available (no `sqlalchemy` needed):
`ok`, `ok_list`, `fail`, `Pagination`, `pagination`, `DEFAULT_PAGE_SIZE`,
`MAX_PAGE_SIZE`, `BizError`, `register_exception_handlers`, `create_app`,
`CRUDProtocol`, `get_crud`, `register_backend`.

Lazily available (imports `sqlalchemy` on first access):
`Base`, `CRUD`, `GUID`, `gen_uuid`, `UuidMixin`, `TimestampMixin`, `TenantMixin`,
`MerchantMixin`, `SoftDeleteMixin`.

The `auth` and `captcha` features live in the subpackages
`snowland_fastapihelper.auth` and `snowland_fastapihelper.captcha` (see §7, §8)
and are not re-exported at the top level.

---

## 7. Identity & Users — `snowland_fastapihelper.auth`

Modelled after `django.contrib.auth`: the package owns every identity-related
primitive (user classes, the account-less virtual user, and the swappable user
model) so other features (e.g. captcha) can depend on the contract without
defining user classes themselves. These are plain dataclasses with **no ORM
dependency**, reusable with any persistence layer.

### `class AbstractBaseUser(ABC)`
Minimal contract every identity must satisfy.
- **Abstract property**: `identity_key: str` — a stable, unique key identifying
  this identity; used as the namespace under which identity-bound data (captcha
  codes, tokens) is stored.

### `class AbstractUser(AbstractBaseUser)` (dataclass)
Reusable base for real user accounts.
- **Fields**: `uuid: str` (business PK, points to `users.uuid`),
  `username: Optional[str] = None`, `tenant_id: Optional[str] = None`
  (→ `tenants.uuid`, tenant isolation), `merchant_id: Optional[str] = None`
  (→ `merchants.uuid`, merchant isolation).
- **Property**: `identity_key` → `"user:{uuid}"`.
- **Validation**: `__post_init__` raises `ValueError` if `uuid` is empty.

### `class User(AbstractUser)`
Default concrete user model. Swap it with `set_user_model()`; `get_user_model()`
then returns your subclass.

### `class VirtualUser(AbstractBaseUser)` (dataclass)
An account-less identity for flows without a real account (e.g. a phone number
before registration).
- **Fields**: `identity_type: str` (e.g. `"phone"` / `"email"` / `"device"` /
  `"session"`), `identity_value: str` (e.g. `"+8613800000000"`),
  `tenant_id: Optional[str] = None`, `merchant_id: Optional[str] = None`.
- **Property**: `identity_key` → `"virtual:{type}:{value}"`.
- **Validation**: raises `ValueError` if `identity_type` or `identity_value` is empty.

### `get_user_model() -> Type[AbstractUser]`
Return the active user model (defaults to `User`; returns whatever was set via
`set_user_model`).

### `set_user_model(model: Type[AbstractUser]) -> None`
Swap the active user model. Raises `TypeError` if `model` is not an
`AbstractUser` subclass.

```python
from snowland_fastapihelper.auth import User, VirtualUser, get_user_model, set_user_model

user = User(uuid="u-1", merchant_id="m-1")
print(user.identity_key)            # "user:u-1"

virtual = VirtualUser(identity_type="phone", identity_value="+8613800000000")

set_user_model(User)                # or register a custom AbstractUser subclass
```

---

## 8. Captcha — `snowland_fastapihelper.captcha`

ORM-agnostic verification-code service. Two independent time windows control a
code's life:

* `expire_seconds` — validity window; verification succeeds only inside it.
* `retain_seconds` — how long the record is kept in the cache (must be >=
  `expire_seconds`). The gap after expiry is what lets the service tell "this code
  expired" apart from "no code was ever generated".

Codes are generated with `astartool.random.random_digit_string` (SystemRandom,
cryptographically secure), not the pseudo-random `random` module.

### `class CaptchaConfig` (dataclass)
Timing settings.
- **Fields**: `expire_seconds: int = 300`, `retain_seconds: int = 900`,
  `code_length: int = 6`.
- **Validation** (`ValueError`): `expire_seconds > 0`, `retain_seconds >=
  expire_seconds`, `code_length > 0`.

### `class VerifyStatus(Enum)`
- `SUCCESS = "success"` — record exists, still valid, code matches.
- `EXPIRED = "expired"` — record exists but past its validity window (still retained).
- `NOT_FOUND = "not_found"` — no record at all: never generated, or purged past retention.
- `MISMATCH = "mismatch"` — a valid record exists but the submitted code differs.

### `class CaptchaService`
Issue and verify codes for a principal.
- **Constructor**: `CaptchaService(cache: Optional[CacheBackend] = None,
  config: Optional[CaptchaConfig] = None, key_prefix: str = "captcha:")`.
  - `cache`: backend to store records; defaults to `get_cache("memory")`.
  - `config`: timing; defaults to `CaptchaConfig()`.
  - `key_prefix`: namespace prefix for every cache key.
- **`async generate(principal, *, code: Optional[str] = None, length: Optional[int] = None) -> str`**:
  issue a new code, replacing any existing one. `code` uses an exact code
  (useful in tests); `length` overrides `config.code_length`. Returns the issued
  code so the caller can deliver it (SMS / email / ...).
- **`async verify(principal, code: str, *, consume: bool = True) -> VerifyStatus`**:
  verify. `consume=True` (default) deletes the record on success, making the code
  single-use.
- **`async invalidate(principal) -> None`**: discard any code currently issued.
- **`async remaining_seconds(principal) -> Optional[int]`**: seconds left before
  the code expires; `None` when there is no record, `0` when it already expired
  but is still retained.

### Cache backends — `backends.py`
- **`class CacheBackend(ABC)`**: async interface `set(key, value, ttl)`,
  `get(key) -> Optional[str]`, `delete(key)`, `exists(key) -> bool`.
- **`get_cache(name: str = "memory") -> CacheBackend`**: return the shared backend
  instance registered under `name`.
- **`register_cache(name, factory) -> None`**: register a backend factory (used for
  self-registration).
- **`class CacheRegistry`**: name → instance mapping; a global `registry` is
  exposed.

### `class MemoryCache(CacheBackend)` — `memory.py`
Built-in, in-process cache (no external dependency); the default backend.
- **Constructor**: `MemoryCache(sweep_interval: float = 60.0)`. A daemon sweeper
  thread purges expired entries every `sweep_interval` seconds (`<= 0` disables the
  sweeper, leaving lazy expiration only).
- Expiry is both lazy (on `get`/`exists`) and proactive (background sweep), so
  codes that are generated but never queried do not leak memory.

### `class RedisCache(CacheBackend)` — `redis_cache.py` *(optional: `redis`)*
Shared across processes and workers. `set` stores the value with `ex=ttl`, so
Redis reclaims expired entries server-side (active expiration) — no sweeper needed.
Importing this module registers the `"redis"` backend (reads the `REDIS_URL` env
var, default `redis://localhost:6379/0`).

```python
from snowland_fastapihelper.auth import VirtualUser
from snowland_fastapihelper.captcha import CaptchaService, CaptchaConfig, VerifyStatus

service = CaptchaService(config=CaptchaConfig(expire_seconds=300, retain_seconds=900))
principal = VirtualUser(identity_type="phone", identity_value="+8613800000000")

code = await service.generate(principal)       # issue & deliver
status = await service.verify(principal, code)  # SUCCESS / MISMATCH / EXPIRED / NOT_FOUND
```
