"""ORM-agnostic database abstraction layer interface definitions.

Defines the unified CRUD protocol ``CRUDProtocol`` and the contract every backend
must follow. Concrete ORMs (SQLAlchemy, Tortoise, Piccolo, Peewee, ...) implement
this protocol in their own subpackages and register with the
``BackendRegistry`` of ``snowland_fastapihelper.database``; business code then
obtains an ORM-agnostic CRUD helper via the unified ``get_crud(model, session)``.

This file does not depend on any ORM and can be imported standalone (core
features require no sqlalchemy installation).
"""
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Sequence, Tuple, TypeVar

ModelType = TypeVar("ModelType")


class CRUDProtocol(ABC, Generic[ModelType]):
    """Unified CRUD interface: every ORM backend must implement these signatures.

    Signature conventions (consistent with the pagination convention in ``response``):

    * ``list`` returns a ``(items, total)`` tuple, where ``items`` is the page's data
      sequence and ``total`` is the matched row count.
    * ``get_by_uuid`` / ``list`` filter out soft-deleted rows by default
      (``include_deleted=True`` forces inclusion).
    * ``soft_delete`` performs a logical delete, ``delete`` a physical delete.
    """

    @abstractmethod
    async def create(self, **kwargs: Any) -> ModelType: ...

    @abstractmethod
    async def get_by_uuid(
        self, uuid: str, *, include_deleted: bool = False
    ) -> Optional[ModelType]: ...

    @abstractmethod
    async def list(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
        **filters: Any,
    ) -> Tuple[Sequence[ModelType], int]: ...

    @abstractmethod
    async def update(self, uuid: str, **kwargs: Any) -> Optional[ModelType]: ...

    @abstractmethod
    async def soft_delete(self, uuid: str) -> bool: ...

    @abstractmethod
    async def delete(self, uuid: str) -> bool: ...
