"""ORM 无关的数据库抽象层接口定义。

定义统一的 CRUD 协议 ``CRUDProtocol`` 与各后端需遵守的契约。具体 ORM
（SQLAlchemy、Tortoise、Piccolo、Peewee 等）在各自子包中实现本协议，并向
``snowland_fastapihelper.database`` 的 ``BackendRegistry`` 注册后，上层业务即可
通过统一的 ``get_crud(model, session)`` 获取与底层 ORM 无关的 CRUD 助手。

本文件不依赖任何 ORM，可独立导入（核心功能无需安装 sqlalchemy）。
"""
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, Sequence, Tuple, TypeVar

ModelType = TypeVar("ModelType")


class CRUDProtocol(ABC, Generic[ModelType]):
    """统一 CRUD 接口：任何 ORM 后端都需实现这些方法签名。

    签名约定（与 ``response`` 的分页约定保持一致）：

    * ``list`` 返回 ``(items, total)`` 二元组，``items`` 为当页数据序列，
      ``total`` 为符合条件的总条数。
    * ``get_by_uuid`` / ``list`` 默认过滤软删除记录（``include_deleted=True`` 强制包含）。
    * ``soft_delete`` 执行逻辑删除，``delete`` 执行物理删除。
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
