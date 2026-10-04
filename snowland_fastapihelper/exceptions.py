"""Business exception and FastAPI exception handlers.

All outward-facing failure responses are normalized here into the format defined
by the ``response`` module:

    {
        "successful": false,
        "code": <int>,
        "message": "<error description>",
        "data": null
    }

Design note: regardless of the HTTP status, the business layer always returns
200, and success/failure is expressed via ``successful`` / ``code`` in the body,
so the frontend can handle everything uniformly (this is the premise of the
response format defined in ``response``).
"""
from typing import Any

from astartool.common import ErrorCode
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from snowland_fastapihelper.response import fail, http_status_to_code


class BizError(Exception):
    """Business exception: carries an ErrorCode value and a message, converted to a
    response by ``biz_error_handler``.

    Business code simply does ``raise BizError(...)`` without building the body.
    """

    def __init__(
        self,
        code: int = ErrorCode.ERROR_CODE_OPERATION_FAILED.value,
        message: str = "operation failed",
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
    return JSONResponse(status_code=200, content=fail(exc.code, exc.message, exc.data))


def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = http_status_to_code(exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(status_code=200, content=fail(code, detail, None))


def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content=fail(
            ErrorCode.ERROR_CODE_PARTNER_ERROR.value,
            "request validation failed",
            exc.errors(),
        ),
    )


def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Fallback: do not leak stack traces for unknown errors; return the unified body.
    return JSONResponse(
        status_code=200,
        content=fail(ErrorCode.ERROR_CODE_SERVER_ERROR.value, "internal server error", None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers of this module onto the FastAPI app."""
    app.add_exception_handler(BizError, biz_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
