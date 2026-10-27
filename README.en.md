# snowland-fastapihelper

A FastAPI development helper library providing out-of-the-box **unified response
format, pagination dependency, business exceptions & exception handlers, app
factory**, plus **SQLAlchemy 2.0 model base classes / mixins** and a **generic
async CRUD helper**.

> Version: v0.2.0

## Features

- **Unified response**: every endpoint returns a fixed 4-field body
  (`successful` / `code` / `message` / `data`); success `code=0`, failures are
  normalized by exception handlers.
- **Pagination dependency**: `pagination` as a FastAPI `Depends`, validating
  page/page_size, with pagination metadata (`items` / `total` / `page` /
  `page_size`) embedded in list responses.
- **Exception system**: `BizError` plus handlers for HTTP errors, validation
  errors and a fallback, all normalized into the unified body.
- **App factory**: `create_app()` wires up the handlers in one line.
- **SQLAlchemy models**: `Base`, cross-dialect `GUID` type, and reusable mixins
  `UuidMixin` / `TimestampMixin` / `TenantMixin` / `MerchantMixin` /
  `SoftDeleteMixin`.
- **Generic CRUD**: async `CRUD` helper aware of soft-delete, covering
  create/read/update/delete and paginated listing.
- **Identity & users (auth)**: Django-auth-style abstract base `AbstractBaseUser`,
  user models `AbstractUser` / `User`, an account-less `VirtualUser`, and a
  swappable user model via `get_user_model()` / `set_user_model()`.
- **Captcha**: ORM-agnostic verification-code service with a built-in memory cache
  or optional Redis cache; distinguishes **expiry** and **retention** windows so
  "expired" can be told apart from "never generated".

## Install

```bash
pip install snowland-fastapihelper
# Core features (unified response / exceptions / app factory) only need
# fastapi / starlette / astartool.
```

SQLAlchemy is an **optional dependency**, required only when using
`database.sqlalchemy` (models / CRUD):

```bash
# Option A: install the package with the extra
pip install "snowland-fastapihelper[sqlalchemy]"

# Option B: install only the SQLAlchemy-related deps
pip install -r requirements-sqlalchemy.txt
```

> `astartool` is hosted on an internal index; configure your pip source
> accordingly. `fastapi` / `starlette` are on PyPI.

## Quick start

```python
from fastapi import FastAPI
from snowland_fastapihelper import create_app, ok, ok_list, pagination, Pagination

app = create_app(title="Demo")


@app.get("/ping")
def ping():
    return ok({"hello": "world"})


@app.get("/items")
def items(page: Pagination = pagination()):
    items = [{"id": i} for i in range(page.offset, page.offset + page.page_size)]
    return ok_list(items, total=1000, page=page.page, page_size=page.page_size)
```

### Business exception

```python
from snowland_fastapihelper import BizError

@app.get("/user/{uid}")
def get_user(uid: str):
    if uid != "1":
        raise BizError(code=9, message="user not found")
    return ok({"uid": uid})
```

### Model & CRUD (ORM-agnostic interface)

The `database` module is an **ORM-agnostic abstraction**: it defines the unified
`CRUDProtocol` and a backend registry; concrete ORMs implement it in their own
subpackages and self-register. Business code always uses the single entry point
`get_crud(model, session)` and never depends on which ORM is in use.

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession
from snowland_fastapihelper import (
    Base, UuidMixin, TimestampMixin, SoftDeleteMixin, get_crud,
)


class User(Base, UuidMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)  # physical PK (see note)
    name: Mapped[str] = mapped_column(nullable=False, comment="user name")


async def create_user(session: AsyncSession, name: str):
    return await get_crud(User, session).create(name=name)
```

> **Note on physical primary key**: `Base` / `UuidMixin` expose a business `uuid`
> but do not declare a database primary key. Declare your own `id` autoincrement
> primary key (or the equivalent for your ORM), otherwise mapping fails.

### Adding another ORM

To support an ORM other than SQLAlchemy (Tortoise / Piccolo / Peewee, ...):

1. Implement `CRUDProtocol` under `snowland_fastapihelper/database/<your_orm>/`.
2. Self-register with that ORM's session type (effective on import):

   ```python
   from snowland_fastapihelper.database import register_backend
   register_backend("tortoise", TortoiseSession, lambda m, s: TortoiseCRUD(m, s))
   ```

Business code keeps calling `get_crud(model, session)` unchanged; dispatch is
automatic by session type (or explicit `backend="tortoise"`).

### Identity & users (auth)

Modelled after `django.contrib.auth`, identity classes live in
`snowland_fastapihelper.auth`; other features (e.g. captcha) depend only on its
abstraction and never define user classes themselves.

```python
from snowland_fastapihelper.auth import User, VirtualUser, get_user_model, set_user_model

# Real user: uuid points to users.uuid; tenant_id / merchant_id scope the data.
user = User(uuid="u-1", merchant_id="m-1")
print(user.identity_key)  # "user:u-1"

# Account-less identity: e.g. a phone number before registration.
v = VirtualUser(identity_type="phone", identity_value="+8613800000000")

# Swappable user model: register a custom AbstractUser subclass; get_user_model()
# then returns it.
set_user_model(User)
```

### Captcha

An ORM-agnostic verification-code service; the cache is either an in-process
memory backend (built-in) or Redis (optional `redis` dependency). It separates two
time windows: **expiry** (the code is valid and verifiable within it) and
**retention** (how long the record is kept, >= expiry, so "expired" can be told
apart from "never generated").

```python
from snowland_fastapihelper.auth import VirtualUser
from snowland_fastapihelper.captcha import CaptchaService, CaptchaConfig, VerifyStatus

service = CaptchaService(config=CaptchaConfig(expire_seconds=300, retain_seconds=900))
principal = VirtualUser(identity_type="phone", identity_value="+8613800000000")

code = await service.generate(principal)         # issue and deliver (SMS / email)
status = await service.verify(principal, code)    # SUCCESS / MISMATCH / EXPIRED / NOT_FOUND
# EXPIRED    code exists but is past its validity; NOT_FOUND never generated or purged
```

For Redis: import `snowland_fastapihelper.captcha.redis_cache`, then
`CaptchaService(cache=get_cache("redis"))` (requires `pip install redis`).

## Response convention

Regardless of HTTP status, the business layer always returns **HTTP 200** and
expresses success/failure via `successful` and `code` inside the body. `code`
values come from `astartool.common.ErrorCode`.

## Tests

```bash
python -m unittest discover -s tests
```

## Changelog

### v0.2.0
- Added the `auth` package: identity abstraction `AbstractBaseUser`, user models
  `AbstractUser` / `User`, account-less `VirtualUser`, and a swappable user model
  via `get_user_model()` / `set_user_model()` (modelled after `django.contrib.auth`).
- Added the `captcha` package: an ORM-agnostic verification-code service with a
  built-in memory cache or optional Redis cache, distinguishing code **expiry**
  from **retention** so "expired" differs from "never generated".
- Captcha codes are now generated with `astartool.random.random_digit_string`
  (SystemRandom-backed, cryptographically secure) instead of the pseudo-random
  `random` module.
- `MemoryCache` gained a background sweeper thread that proactively evicts expired
  entries, so codes that are generated but never verified no longer leak memory.
- Version is now single-sourced from ``snowland_fastapihelper.__version__``
  (``pyproject.toml`` uses ``dynamic``).

### v0.1.0
- Unified response format, pagination dependency, business exceptions & handlers,
  and the app factory.
- SQLAlchemy 2.0 based, ORM-agnostic database abstraction (model base classes /
  mixins, generic async CRUD).

## Project layout

```
snowland_fastapihelper/
├── __init__.py            # public API exports
├── response.py            # unified response / pagination dependency
├── exceptions.py          # business exceptions & handlers
├── app.py                 # create_app factory
├── auth/                  # identity & users (django.contrib.auth style)
│   ├── base_user.py       # AbstractBaseUser base class
│   └── models.py          # AbstractUser / User / VirtualUser
├── captcha/               # captcha service (ORM-agnostic)
│   ├── backends.py        # CacheBackend interface & registry
│   ├── memory.py          # in-process memory cache (built-in)
│   ├── redis_cache.py     # Redis cache (optional dependency)
│   ├── config.py          # expiry / retention settings
│   └── service.py         # CaptchaService
└── database/
    ├── base.py            # ORM-agnostic CRUDProtocol
    ├── backends.py        # backend registry & get_crud
    └── sqlalchemy/
        ├── models.py     # Base / GUID / mixins
        └── crud.py       # generic async CRUD helper
```

## License

BSD 3-Clause, see [LICENSE](./LICENSE).
