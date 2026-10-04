"""Unified API response format.

All public endpoints consistently return the following structure (4 fixed
top-level fields):

    Success (non-list):
    {
        "successful": true,
        "code": 0,
        "message": "ok",
        "data": {...}
    }

    Success (list, data carries pagination metadata):
    {
        "successful": true,
        "code": 0,
        "message": "ok",
        "data": {
            "items": [...],
            "total": 100,
            "page": 1,
            "page_size": 20
        }
    }

    Failure (normalized by the exception handlers):
    {
        "successful": false,
        "code": <ErrorCode value>,
        "message": "<error description>",
        "data": null
    }

``code`` values come from the third-party package ``astartool.common.ErrorCode``.
"""
from typing import Any

from astartool.common import ErrorCode
from fastapi import Query

# Default page size
DEFAULT_PAGE_SIZE = 20
# Maximum rows per page, to avoid fetching too much at once
MAX_PAGE_SIZE = 200


def ok(data: Any = None, message: str = "ok") -> dict:
    """Build a success response."""
    return {
        "successful": True,
        "code": ErrorCode.ERROR_CODE_OPERATION_SUCCESS.value,
        "message": message,
        "data": data,
    }


def ok_list(items: list, total: int, page: int, page_size: int) -> dict:
    """Build a success response (list); data carries items and pagination metadata."""
    return {
        "successful": True,
        "code": ErrorCode.ERROR_CODE_OPERATION_SUCCESS.value,
        "message": "ok",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


def fail(code: int, message: str, data: Any = None) -> dict:
    """Build a failure response (business code usually raises an exception that the
    exception handlers normalize into this shape)."""
    return {
        "successful": False,
        "code": code,
        "message": message,
        "data": data,
    }


class Pagination:
    """Pagination params: page starts at 1; offset is for SQL usage."""

    def __init__(self, page: int, page_size: int):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination(
    page: int = Query(1, ge=1, description="Page number, starting at 1"),
    page_size: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Page size"
    ),
) -> Pagination:
    """FastAPI dependency: parse and validate pagination params."""
    return Pagination(page=page, page_size=page_size)


def http_status_to_code(status_code: int) -> int:
    """Map an HTTP status code to an ErrorCode value (for the exception handlers)."""
    mapping = {
        400: ErrorCode.ERROR_CODE_OPERATION_FAILED.value,
        401: ErrorCode.ERROR_CODE_TOKEN_ERROR.value,
        403: ErrorCode.ERROR_CODE_PERMISSION_ERROR.value,
        404: ErrorCode.ERROR_CODE_USER_NOT_FOUND.value,
        409: ErrorCode.ERROR_CODE_LOGINED_ERROR.value,
        423: ErrorCode.ERROR_CODE_ACCOUNT_LOCKED_ERROR.value,
        429: ErrorCode.ERROR_CODE_ACCOUNT_TRY_TIME_LIMITED_ERROR.value,
    }
    if status_code >= 500:
        return ErrorCode.ERROR_CODE_SERVER_ERROR.value
    return mapping.get(status_code, ErrorCode.ERROR_CODE_UNKNOWN.value)
