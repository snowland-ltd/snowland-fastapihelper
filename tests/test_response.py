"""Unit tests for the response module and exception handling (stdlib unittest)."""
import unittest

from astartool.common import ErrorCode

from snowland_fastapihelper.exceptions import BizError, http_status_to_code
from snowland_fastapihelper.response import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Pagination,
    fail,
    ok,
    ok_list,
    pagination,
)


class TestResponse(unittest.TestCase):
    def test_ok_shape(self):
        body = ok({"id": 1})
        self.assertTrue(body["successful"])
        self.assertEqual(body["code"], ErrorCode.ERROR_CODE_OPERATION_SUCCESS.value)
        self.assertEqual(body["message"], "ok")
        self.assertEqual(body["data"], {"id": 1})

    def test_ok_list_shape(self):
        body = ok_list([1, 2], total=2, page=1, page_size=20)
        self.assertTrue(body["successful"])
        data = body["data"]
        self.assertEqual(data["items"], [1, 2])
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 20)

    def test_fail_shape(self):
        body = fail(1, "boom")
        self.assertFalse(body["successful"])
        self.assertEqual(body["code"], 1)
        self.assertEqual(body["message"], "boom")
        self.assertIsNone(body["data"])

    def test_pagination_offset(self):
        p = Pagination(page=3, page_size=20)
        self.assertEqual(p.offset, 40)
        self.assertEqual(p.limit, 20)

    def test_pagination_dependency(self):
        p = pagination(page=2, page_size=10)
        self.assertIsInstance(p, Pagination)
        self.assertEqual(p.page, 2)

    def test_constants(self):
        self.assertEqual(DEFAULT_PAGE_SIZE, 20)
        self.assertEqual(MAX_PAGE_SIZE, 200)


class TestHttpStatusMapping(unittest.TestCase):
    def test_mapping(self):
        self.assertEqual(
            http_status_to_code(401), ErrorCode.ERROR_CODE_TOKEN_ERROR.value
        )
        self.assertEqual(
            http_status_to_code(403), ErrorCode.ERROR_CODE_PERMISSION_ERROR.value
        )
        self.assertEqual(
            http_status_to_code(404), ErrorCode.ERROR_CODE_USER_NOT_FOUND.value
        )
        self.assertEqual(http_status_to_code(500), ErrorCode.ERROR_CODE_SERVER_ERROR.value)


class TestBizError(unittest.TestCase):
    def test_defaults(self):
        exc = BizError()
        self.assertEqual(exc.code, ErrorCode.ERROR_CODE_OPERATION_FAILED.value)
        self.assertEqual(exc.message, "operation failed")

    def test_custom(self):
        exc = BizError(code=9, message="no user", data={"x": 1})
        self.assertEqual(exc.code, 9)
        self.assertEqual(exc.message, "no user")
        self.assertEqual(exc.data, {"x": 1})


if __name__ == "__main__":
    unittest.main()
