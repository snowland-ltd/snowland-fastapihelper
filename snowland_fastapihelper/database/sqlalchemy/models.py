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
    """UUID business field type: native UUID on PostgreSQL, CHAR(36) elsewhere.

    The database primary key remains an auto-increment integer id (internal, not
    exposed); uuid is only the externally exposed business identifier, to avoid
    enumeration via sequential primary keys.
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
    """Generate a UUID string default value (business field)."""
    return str(uuid.uuid4())


class UuidMixin:
    """Externally exposed business identifier: the DB keeps an auto-increment id PK,
    while uuid serves as the business primary key."""

    uuid: Mapped[str] = mapped_column(
        GUID, unique=True, index=True, default=gen_uuid, nullable=False,
        comment="Externally exposed business primary key (UUID string); the physical "
                "DB primary key remains an auto-increment id to avoid enumeration.",
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        comment="Creation time (UTC, timezone-aware).",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        comment="Update time (UTC, timezone-aware); refreshed on every UPDATE.",
    )


class TenantMixin:
    # Tenant reference uses the business uuid (points to tenants.uuid), not the
    # auto-increment id.
    tenant_id: Mapped[str] = mapped_column(
        GUID, ForeignKey("tenants.uuid"), index=True,
        comment="Tenant uuid (business identifier pointing to tenants.uuid); used for "
                "tenant-level data isolation.",
    )


class MerchantMixin:
    """Merchant reference (business identifier pointing to merchants.uuid) for
    merchant-scoped data.

    Per the repository-wide convention (see migration 0003 note), no DB-level
    foreign key is created; this is a GUID indexed column only, with the
    relationship semantics guaranteed at the application layer (SQLite-compatible).
    """

    merchant_id: Mapped[str] = mapped_column(
        GUID, index=True,
        comment="Merchant uuid (business identifier pointing to merchants.uuid); used "
                "for merchant-level data isolation.",
    )


class SoftDeleteMixin:
    """Soft-delete (logical delete) flag: set ``is_deleted`` to True on delete,
    defaulting to False.

    All business deletions only set the flag, never physically remove rows, so data
    is retained for audit. Reads (list/read) filter out deleted rows automatically;
    system-wide / shared definition tables do not inherit this mixin.
    """

    is_deleted: Mapped[bool] = mapped_column(
        default=False, nullable=False,
        comment="Soft-delete flag: True means deleted (logical), filtered out by "
                "queries by default; False otherwise.",
    )
