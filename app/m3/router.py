"""M3 房间报修；由现有 app.main 挂载到 /m3。"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.common.config import PROJECT_ROOT
from app.m3.errors import M3Route
from app.m3.identity import authenticated_reporter
from app.m3.models import ReportCreate
from app.m3 import service


router = APIRouter(route_class=M3Route)


@router.get("/report", include_in_schema=False, response_class=HTMLResponse)
def report_page(request: Request) -> HTMLResponse:
    # 只有服务端固定布尔值替换，不渲染用户输入；无模板框架依赖。
    login_available = any(getattr(route, "path", None) == "/m2/login" for route in request.app.routes)
    page = (PROJECT_ROOT / "web/templates/m3/report.html").read_text(encoding="utf-8")
    return HTMLResponse(page.replace("{{LOGIN_AVAILABLE}}", "true" if login_available else "false"))


@router.get("/rooms")
def rooms(request: Request, reporter_id: int = Depends(authenticated_reporter)) -> dict:
    return {"items": service.list_rooms(request.app.state.settings.database_path, reporter_id)}


@router.post("/work-orders", status_code=201)
def create_work_order(
    payload: ReportCreate, request: Request, reporter_id: int = Depends(authenticated_reporter),
) -> dict:
    return service.create_report(request.app.state.settings.database_path, reporter_id, payload)
