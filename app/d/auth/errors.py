"""统一错误响应体：{"error": "<code>", "message": "<中文说明>"}。

契约见 docs/architecture.md；首页、健康检查与业务接口共用同一形状，
避免每个模块各自拼 detail。
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


DEFAULT_CODES = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "invalid_request",
    500: "internal_error",
}


def api_error(status_code: int, message: str, code: str = "") -> HTTPException:
    """构造带固定错误码的异常，交给 install_error_handlers 渲染。"""
    return HTTPException(
        status_code=status_code,
        detail={"code": code or DEFAULT_CODES.get(status_code, "error"), "message": message},
    )


def _render(status_code: int, detail) -> JSONResponse:
    if isinstance(detail, dict) and "message" in detail:
        code = str(detail.get("code") or DEFAULT_CODES.get(status_code, "error"))
        message = str(detail["message"])
    else:
        code = DEFAULT_CODES.get(status_code, "error")
        message = str(detail)
    return JSONResponse(status_code=status_code, content={"error": code, "message": message})


def install_error_handlers(application: FastAPI) -> None:
    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(_request: Request, error: StarletteHTTPException):
        return _render(error.status_code, error.detail)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(_request: Request, error: RequestValidationError):
        # 只回报字段位置，不回显完整输入，避免把口令写进响应或日志。
        first = error.errors()[0] if error.errors() else {}
        location = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        message = f"请求参数不合法：{location or 'body'}"
        return _render(422, {"code": "invalid_request", "message": message})
