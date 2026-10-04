"""database 抽象层单元测试（基于标准库 unittest，不依赖任何 ORM）。"""
import unittest
from typing import Any, Optional, Sequence, Tuple

from snowland_fastapihelper.database import (
    CRUDProtocol,
    get_crud,
    register_backend,
)


class _DummySession:
    pass


class DummyCRUD(CRUDProtocol):
    """仅用于验证注册表派发的桩实现。"""

    def __init__(self, model: Any, session: Any) -> None:
        self.model = model
        self.session = session

    async def create(self, **kwargs: Any) -> Any: ...

    async def get_by_uuid(self, uuid: str, *, include_deleted: bool = False) -> Optional[Any]:
        return None

    async def list(
        self, *, page: int = 1, page_size: int = 20, include_deleted: bool = False, **filters: Any
    ) -> Tuple[Sequence[Any], int]:
        return [], 0

    async def update(self, uuid: str, **kwargs: Any) -> Optional[Any]:
        return None

    async def soft_delete(self, uuid: str) -> bool:
        return False

    async def delete(self, uuid: str) -> bool:
        return False


class TestDatabaseAbstraction(unittest.TestCase):
    def test_protocol_is_abstract(self):
        with self.assertRaises(TypeError):
            CRUDProtocol()  # noqa: B018

    def test_register_and_dispatch_by_session(self):
        register_backend("dummy", _DummySession, lambda m, s: DummyCRUD(m, s))
        crud = get_crud(object(), _DummySession())
        self.assertIsInstance(crud, DummyCRUD)

    def test_dispatch_by_name(self):
        register_backend("dummy_named", _DummySession, lambda m, s: DummyCRUD(m, s))
        crud = get_crud(object(), _DummySession(), backend="dummy_named")
        self.assertIsInstance(crud, DummyCRUD)

    def test_unknown_session_raises(self):
        class Other:  # 未注册
            pass

        with self.assertRaises(TypeError):
            get_crud(object(), Other())

    def test_unknown_name_raises(self):
        with self.assertRaises(KeyError):
            get_crud(object(), _DummySession(), backend="__no_such_backend__")


if __name__ == "__main__":
    unittest.main()
