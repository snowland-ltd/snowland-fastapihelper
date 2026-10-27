"""snowland_fastapihelper - a FastAPI development helper library.

Provides the following out-of-the-box capabilities:

* Unified API response format and a pagination dependency (``response``)
* A business exception and FastAPI exception handlers that normalize failures
  into the unified response (``exceptions``)
* An app factory ``create_app`` that wires up the exception handlers in one call
  (``app``)
* A SQLAlchemy-based generic model base / mixins and async CRUD helper
  (``database.sqlalchemy``)

See README.md for typical usage.
"""
__version__ = "0.2.0"

from snowland_fastapihelper.response import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Pagination,
    fail,
    ok,
    ok_list,
    pagination,
)
from snowland_fastapihelper.exceptions import (
    BizError,
    register_exception_handlers,
)
from snowland_fastapihelper.app import create_app
from snowland_fastapihelper.database import (
    CRUDProtocol,
    get_crud,
    register_backend,
)

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Listed in ``__all__`` for ``import *`` completeness; bound at runtime via
    # ``__getattr__`` so the core API works without sqlalchemy installed.
    from snowland_fastapihelper.database.sqlalchemy import (
        Base,
        CRUD,
        GUID,
        gen_uuid,
        UuidMixin,
        TimestampMixin,
        TenantMixin,
        MerchantMixin,
        SoftDeleteMixin,
    )

__all__ = [
    "__version__",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "Pagination",
    "fail",
    "ok",
    "ok_list",
    "pagination",
    "BizError",
    "register_exception_handlers",
    "create_app",
    "CRUDProtocol",
    "get_crud",
    "register_backend",
    "Base",
    "CRUD",
    "GUID",
    "gen_uuid",
    "UuidMixin",
    "TimestampMixin",
    "TenantMixin",
    "MerchantMixin",
    "SoftDeleteMixin",
]

# SQLAlchemy-related symbols live in the optional ``database.sqlalchemy``
# subpackage and are imported lazily: using the core API (response / exceptions /
# app factory) does not require sqlalchemy; the import is only triggered when one
# of the names below is accessed (or via an explicit
# ``from snowland_fastapihelper.database.sqlalchemy import ...``), raising a clear
# ModuleNotFoundError if sqlalchemy is not installed.
_SQLALCHEMY_NAMES = frozenset(
    {
        "Base",
        "CRUD",
        "GUID",
        "gen_uuid",
        "UuidMixin",
        "TimestampMixin",
        "TenantMixin",
        "MerchantMixin",
        "SoftDeleteMixin",
    }
)


def __getattr__(name: str):
    if name in _SQLALCHEMY_NAMES:
        from snowland_fastapihelper.database.sqlalchemy import (
            Base,
            CRUD,
            GUID,
            gen_uuid,
            UuidMixin,
            TimestampMixin,
            TenantMixin,
            MerchantMixin,
            SoftDeleteMixin,
        )
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
