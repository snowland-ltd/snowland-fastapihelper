"""数据库抽象层（ORM 无关）统一入口。

设计目标：屏蔽底层 ORM 差异，业务层只依赖统一接口：:

    from snowland_fastapihelper.database import get_crud
    crud = get_crud(User, session)   # session 来自当前使用的 ORM

具体 ORM 在各自子包中实现 ``base.CRUDProtocol`` 并向注册表自注册：

* SQLAlchemy 后端：``snowland_fastapihelper.database.sqlalchemy``
  （import 该子包即自动注册，已安装 sqlalchemy 时可用）。

新增其他 ORM 支持（如 Tortoise / Piccolo）时，只需实现 ``CRUDProtocol``，
在对应子包里 ``register_backend(name, SessionType, factory)`` 即可，上层
``get_crud`` 调用方式保持不变。

本文件与其导入的 ``base`` / ``backends`` 均不依赖任何 ORM，可独立导入。
"""
from snowland_fastapihelper.database.backends import (
    BackendRegistry,
    get_crud,
    register_backend,
)
from snowland_fastapihelper.database.base import CRUDProtocol

__all__ = [
    "CRUDProtocol",
    "get_crud",
    "register_backend",
    "BackendRegistry",
]
