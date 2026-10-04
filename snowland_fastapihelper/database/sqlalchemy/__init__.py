"""SQLAlchemy backend implementation (optional dependency; requires sqlalchemy).

Importing this subpackage auto-registers the backend with
``snowland_fastapihelper.database``, after which ``get_crud(model, session)``
dispatches to this implementation based on the AsyncSession type.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from snowland_fastapihelper.database.backends import register_backend
from snowland_fastapihelper.database.sqlalchemy.crud import CRUD
from snowland_fastapihelper.database.sqlalchemy.models import (
    Base,
    GUID,
    MerchantMixin,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
    UuidMixin,
    gen_uuid,
)

# Self-register: session type is sqlalchemy's AsyncSession
register_backend(
    "sqlalchemy", AsyncSession, lambda model, session: CRUD(model, session)
)

__all__ = [
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
