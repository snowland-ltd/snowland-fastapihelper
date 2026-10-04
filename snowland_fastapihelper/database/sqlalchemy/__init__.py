"""SQLAlchemy 后端实现（可选依赖，需安装 sqlalchemy）。

import 本子包时会自动向 ``snowland_fastapihelper.database`` 注册后端，
此后 ``get_crud(model, session)`` 即可按 AsyncSession 类型派发到本实现。
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

# 自注册：session 类型为 sqlalchemy 的 AsyncSession
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
