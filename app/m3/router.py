"""M3 房间报修；由现有 app.main 挂载到 /m3。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.common.config import PROJECT_ROOT
from app.m3.errors import M3Route, ReportError
from app.m3.identity import authenticated_reporter
from app.m3.models import AssignmentCreate, ReportCreate, parse_order_id
from app.m3 import service


router = APIRouter(route_class=M3Route)


def _page(request: Request, filename: str, order_id: str = "") -> HTMLResponse:
    # 仅替换服务端布尔值及已验证的 ASCII 数字 ID，不渲染任意用户文本。
    login_available = any(getattr(route, "path", None) == "/m2/login" for route in request.app.routes)
    page = (PROJECT_ROOT / "web/templates/m3" / filename).read_text(encoding="utf-8")
    return HTMLResponse(page.replace("{{LOGIN_AVAILABLE}}", "true" if login_available else "false")
                        .replace("{{ORDER_ID}}", order_id))


@router.get("/report", include_in_schema=False, response_class=HTMLResponse)
def report_page(request: Request) -> HTMLResponse:
    return _page(request, "report.html")


@router.get("/my-orders", include_in_schema=False, response_class=HTMLResponse)
def my_orders_page(request: Request) -> HTMLResponse:
    return _page(request, "my-orders.html")


@router.get("/dispatch", include_in_schema=False, response_class=HTMLResponse)
def dispatch_page(request: Request) -> HTMLResponse:
    return _page(request, "dispatch.html")


@router.get("/orders/{order_id}", include_in_schema=False, response_class=HTMLResponse)
def order_page(order_id: str, request: Request) -> HTMLResponse:
    parse_order_id(order_id)  # 模板只允许十进制数字，不填入任意路径内容或工单资料。
    return _page(request, "order-detail.html", order_id)


@router.get("/rooms")
def rooms(request: Request, reporter_id: int = Depends(authenticated_reporter)) -> dict:
    return {"items": service.list_rooms(request.app.state.settings.database_path, reporter_id)}


@router.post("/work-orders", status_code=201)
def create_work_order(
    payload: ReportCreate, request: Request, reporter_id: int = Depends(authenticated_reporter),
) -> dict:
    return service.create_report(request.app.state.settings.database_path, reporter_id, payload)


@router.get("/work-orders")
def my_orders(request: Request, reporter_id: int = Depends(authenticated_reporter)) -> dict:
    if request.query_params:
        raise ReportError(422, "invalid_request", "本人工单列表不接受查询参数，身份由服务端确定")
    return service.list_my_orders(request.app.state.settings.database_path, reporter_id)


@router.get("/work-orders/dispatch")
def dispatch_orders(request: Request, status: str = "REPORTED", reporter_id: int = Depends(authenticated_reporter)) -> dict:
    return service.dispatch_queue(request.app.state.settings.database_path, reporter_id, status)


@router.get("/repairers")
def repairers(request: Request, reporter_id: int = Depends(authenticated_reporter)) -> dict:
    return service.list_repairers(request.app.state.settings.database_path, reporter_id)


@router.post("/work-orders/{order_id}/assign")
def assign_work_order(
    order_id: str, payload: AssignmentCreate, request: Request,
    reporter_id: int = Depends(authenticated_reporter),
) -> dict:
    return service.assign_order(request.app.state.settings.database_path, reporter_id, order_id, payload)


# /work-orders 下的静态路径必须声明在此动态路径之前。
@router.get("/work-orders/{order_id}")
def order_detail(order_id: str, request: Request, reporter_id: int = Depends(authenticated_reporter)) -> dict:
    return service.read_order(request.app.state.settings.database_path, reporter_id, order_id)
