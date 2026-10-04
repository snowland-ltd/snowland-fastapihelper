import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class Base(DeclarativeBase):
    pass


class GUID(TypeDecorator):
    """UUID 业务字段类型：PostgreSQL 用原生 UUID，其余库回退到 CHAR(36) 字符串。

    数据库主键仍保留自增整数 id（内部使用、不对外暴露），uuid 仅作为对外
    暴露的业务标识，避免通过自增主键撞库。
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect: Any):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=False))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        return str(value)


def gen_uuid() -> str:
    """生成 UUID 字符串默认值（业务字段）。"""
    return str(uuid.uuid4())


class UuidMixin:
    """对外暴露的业务标识：数据库保留自增 id 主键，uuid 作为业务主键。"""

    uuid: Mapped[str] = mapped_column(
        GUID, unique=True, index=True, default=gen_uuid, nullable=False,
        comment="对外暴露的业务主键（UUID 字符串）；数据库物理主键仍为自增 id，避免通过自增主键撞库。",
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        comment="创建时间（UTC，带时区）。",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        comment="更新时间（UTC，带时区）；每次 UPDATE 自动刷新。",
    )


class TenantMixin:
    # 租户引用使用业务 uuid（指向 tenants.uuid），不暴露自增 id。
    tenant_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("tenants.uuid"), index=True,
        comment="租户 uuid（指向 tenants.uuid 的业务标识）；用于租户级数据隔离。",
    )


class MerchantMixin:
    """商户引用（指向 merchants.uuid 的业务标识），用于按商户隔离的数据。

    遵循全库约定（见迁移 0003 注释），不建 DB 级外键，仅作 GUID 索引列，
    关联语义由应用层保证（兼容 SQLite）。
    """

    merchant_id: Mapped[str] = mapped_column(
        GUID, index=True,
        comment="商户 uuid（指向 merchants.uuid 的业务标识）；用于商户级数据隔离。",
    )


class SoftDeleteMixin:
    """逻辑删除（假删）标记位：删除时为 ``is_deleted`` 赋 True，默认 False。

    所有业务删除操作只置位、不做物理删除，便于数据留存与审计。
    查询（list/read）自动过滤已删除记录；系统级/共享定义表不继承本 Mixin。
    """

    is_deleted: Mapped[bool] = mapped_column(
        default=False, nullable=False,
        comment="逻辑删除标记：True 表示已删除（假删），查询自动过滤；默认 False。",
    )
