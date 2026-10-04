"""后端注册表：将 session 类型映射到对应 ORM 的 CRUD 工厂。

业务层只依赖 ``get_crud(model, session)`` 这一统一入口，无需关心底层 ORM。
新增 ORM 支持时，在对应子包中调用 ``register_backend`` 即可（SQLAlchemy 后端
已在 ``snowland_fastapihelper.database.sqlalchemy`` 中自注册）。

本文件不依赖任何 ORM，可独立导入。
"""
import inspect
from typing import Any, Callable, Dict, Tuple, Type

from snowland_fastapihelper.database.base import CRUDProtocol

# 工厂签名：(model, session) -> CRUDProtocol 实例
BackendFactory = Callable[[Any, Any], CRUDProtocol]


class BackendRegistry:
    """保存「session 类型 -> 后端 CRUD 工厂」的映射，并负责派发。"""

    def __init__(self) -> None:
        # session 类型 -> (后端名, 工厂)
        self._by_session: Dict[type, Tuple[str, BackendFactory]] = {}
        # 后端名 -> (session 类型, 工厂)
        self._by_name: Dict[str, Tuple[type, BackendFactory]] = {}

    def register(
        self, name: str, session_type: Type[Any], factory: BackendFactory
    ) -> None:
        """注册一个后端。``session_type`` 用于按 session 实例自动派发。"""
        self._by_session[session_type] = (name, factory)
        self._by_name[name] = (session_type, factory)

    def get_factory(self, session: Any, *, backend: str = None) -> BackendFactory:
        if backend is not None:
            if backend not in self._by_name:
                raise KeyError(
                    f"未注册的数据库后端：{backend!r}；已注册：{sorted(self._by_name)}"
                )
            return self._by_name[backend][1]

        session_type = type(session)
        if session_type in self._by_session:
            return self._by_session[session_type][1]
        # 兼容自定义 session 子类（如 AsyncSession 的子类）
        for cls in inspect.getmro(session_type):
            if cls in self._by_session:
                return self._by_session[cls][1]
        raise TypeError(
            f"无法为 session 类型 {session_type!r} 找到已注册的数据库后端；"
            f"请先 import 对应 ORM 子包（如 snowland_fastapihelper.database.sqlalchemy），"
            f"或显式传入 backend= 参数。"
        )

    def get_crud(
        self, model: Any, session: Any, *, backend: str = None
    ) -> CRUDProtocol:
        factory = self.get_factory(session, backend=backend)
        return factory(model, session)


# 全局唯一注册表实例
registry = BackendRegistry()


def register_backend(
    name: str, session_type: Type[Any], factory: BackendFactory
) -> None:
    """注册一个 ORM 后端的 CRUD 工厂（供各 ORM 子包自注册使用）。"""
    registry.register(name, session_type, factory)


def get_crud(model: Any, session: Any, *, backend: str = None) -> CRUDProtocol:
    """统一入口：根据 session 类型返回对应 ORM 后端的 CRUD 助手。

    优先按 ``type(session)`` 自动派发；也可用 ``backend=`` 显式指定已注册的后端名。
    """
    return registry.get_crud(model, session, backend=backend)
