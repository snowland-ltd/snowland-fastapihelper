# snowland-fastapihelper API Reference (v0.1.0)

This document describes every public API of `snowland-fastapihelper` with its
inputs, outputs and behavior. See the code for the authoritative definition.

> Chinese version: [api.zh.md](api_v0_1_0.zh.md)

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
