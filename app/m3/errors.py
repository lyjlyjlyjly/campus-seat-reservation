"""只作用于 M3 路由；不安装全局异常处理器。"""

import logging
import sqlite3

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from starlette.exceptions import HTTPException


logger = logging.getLogger(__name__)


class ReportError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "message": message})


def validation_message(error: RequestValidationError, *, assignment: bool = False) -> str:
    # 不输出原始输入/任意字段名/异常正文；只显示已知字段与预定原因。
    first = error.errors()[0]
    kind = first["type"]
    field = first["loc"][-1] if first["loc"] else None
    if assignment:
        if kind == "extra_forbidden":
            return "派单请求仅允许 assigned_to，不接受操作者、状态、时间或其他额外字段"
        if field == "assigned_to":
            return "assigned_to 必须是严格正整数，不能为布尔值、小数或数字字符串"
        return "派单请求须为 JSON 对象，并且仅包含 assigned_to 严格正整数"
    if kind == "extra_forbidden":
        return "请求仅允许 room_id、fault_type、description，不接受身份、状态或其他额外字段"
    if field == "room_id":
        return "room_id 必须是严格正整数，不能为布尔值、小数或数字字符串"
    if field == "fault_type":
        return "fault_type 必须是字符串，且为 ELECTRICAL、WATER、FURNITURE 或 OTHER"
    if field == "description":
        return "description 必须是字符串，去除首尾空白后为 1–1000 个 Unicode 字符，不含 U+0000 或无效 Unicode"
    return "请求须为 JSON 对象，并包含 room_id、fault_type、description"


class M3Route(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()
        assignment = self.path.endswith("/work-orders/{order_id}/assign")

        async def handle(request):
            try:
                return await original(request)
            except ReportError as error:
                return error_response(error.status_code, error.code, error.message)
            except RequestValidationError as error:
                return error_response(422, "invalid_request", validation_message(error, assignment=assignment))
            except HTTPException as error:
                # G2 的 HTTPException 在此局部适配，优先于共享的全局 handler。
                messages = {
                    401: ("unauthenticated", "请先登录，或重新登录已失效的会话"),
                    403: ("forbidden", "当前账号没有报修权限"),
                    503: ("dependency_unavailable", "共享服务暂不可用，请稍后再试"),
                }
                code, message = messages.get(error.status_code, ("request_failed", "请求未能完成"))
                return error_response(error.status_code, code, message)
            except sqlite3.Error as error:
                # Python 3.10 兼容：新版可用错误码，旧版只匹配明确的锁错误。
                code = getattr(error, "sqlite_errorcode", 0) & 0xFF
                if code in (5, 6) or str(error) in ("database is locked", "database table is locked"):
                    return error_response(503, "database_busy", "数据库暂时繁忙，本次未提交，请稍后再试")
                logger.exception("M3 数据库操作失败")
                return error_response(500, "internal_error", "报修服务发生内部错误，请联系管理员")
            except Exception:
                # 保留错误日志及 500；不把代码错误或传递依赖损坏伪装为 503。
                logger.exception("M3 请求处理失败")
                return error_response(500, "internal_error", "报修服务发生内部错误，请联系管理员")

        return handle
