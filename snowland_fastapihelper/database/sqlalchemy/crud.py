"""Generic async CRUD helper based on SQLAlchemy async sessions.

Use together with the Base / Mixin in
``snowland_fastapihelper.database.sqlalchemy.models``. Automatically detects and
applies ``SoftDeleteMixin``: ``list`` / ``get_by_uuid`` filter out logically
deleted rows by default (``include_deleted=True`` forces inclusion).
"""
from typing import Any, Generic, List, Optional, Sequence, Tuple, Type, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from snowland_fastapihelper.database.base import CRUDProtocol
from snowland_fastapihelper.database.sqlalchemy.models import Base, SoftDeleteMixin

ModelType = TypeVar("ModelType", bound=Base)


class CRUD(CRUDProtocol, Generic[ModelType]):
    """Generic async CRUD for a single model type.

    Example::

        crud = CRUD(User, session)
        user = await crud.create(name="alice")
        rows, total = await crud.list(page=1, page_size=20, merchant_id=mid)
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    def _alive_filter(self, stmt: Any) -> Any:
        if issubclass(self.model, SoftDeleteMixin):
            stmt = stmt.where(self.model.is_deleted == False)  # noqa: E712
        return stmt

    async def create(self, **kwargs: Any) -> ModelType:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_by_uuid(
        self, uuid: str, *, include_deleted: bool = False
    ) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.uuid == uuid)
        if not include_deleted:
            stmt = self._alive_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
        **filters: Any,
    ) -> Tuple[Sequence[ModelType], int]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        for key, value in filters.items():
            if not hasattr(self.model, key):
                raise AttributeError(
                    f"{self.model.__name__} has no field {key!r}; cannot use as filter"
                )
            column = getattr(self.model, key)
            stmt = stmt.where(column == value)
            count_stmt = count_stmt.where(column == value)
        if not include_deleted:
            stmt = self._alive_filter(stmt)
            count_stmt = self._alive_filter(count_stmt)

        total = (await self.session.execute(count_stmt)).scalar_one()
        offset = (max(page, 1) - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        rows = (await self.session.execute(stmt)).scalars().all()
        return rows, int(total)

    async def update(self, uuid: str, **kwargs: Any) -> Optional[ModelType]:
        obj = await self.get_by_uuid(uuid)
        if obj is None:
            return None
        for key, value in kwargs.items():
            if not hasattr(self.model, key):
                raise AttributeError(
                    f"{self.model.__name__} has no field {key!r}; cannot update"
                )
            setattr(obj, key, value)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, uuid: str) -> bool:
        if not issubclass(self.model, SoftDeleteMixin):
            raise TypeError(
                f"{self.model.__name__} does not inherit SoftDeleteMixin; "
                f"soft delete unsupported"
            )
        obj = await self.get_by_uuid(uuid)
        if obj is None:
            return False
        obj.is_deleted = True
        await self.session.commit()
        return True

    async def delete(self, uuid: str) -> bool:
        obj = await self.get_by_uuid(uuid, include_deleted=True)
        if obj is None:
            return False
        await self.session.delete(obj)
        await self.session.commit()
        return True
