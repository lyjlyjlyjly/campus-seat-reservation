"""M2 路由：整教室申请与一级审批（M2-R01、M2-R02、M2-R03 部分）。

权限口径：提交申请需要 `room:apply`（teacher、org_leader），审批需要 `room:approve`
（approver、admin）。本轮不做二级审批、撤销与 M2→M1 座位占用，见 SPEC-002。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app.common.config import PROJECT_ROOT

from app.d.auth.dependencies import current_user, require_permission
from app.d.auth.errors import api_error
from app.d.auth.users import SessionUser
from app.m2 import applications
from app.m2.times import InvalidPeriod, parse_period

router = APIRouter()

_TEMPLATES = PROJECT_ROOT / "web" / "templates"

APPLY_PERMISSION = "room:apply"
APPROVE_PERMISSION = "room:approve"


class ApplicationCreate(BaseModel):
    room_id: int = Field(gt=0)
    start_at: str = Field(min_length=10, max_length=40)
    end_at: str = Field(min_length=10, max_length=40)
    purpose: str = Field(min_length=2, max_length=200)
    attendee_count: int = Field(ge=1, le=500)

    @field_validator("purpose", mode="before")
    @classmethod
    def strip_purpose(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class DecisionCreate(BaseModel):
    note: Optional[str] = Field(default=None, max_length=200)

    @field_validator("note", mode="before")
    @classmethod
    def strip_note(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


def _rejected(error: applications.ApplicationRejected) -> Exception:
    return api_error(error.status_code, error.message, error.code)


@router.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    """登录页公开可访问；页面本身不渲染任何用户数据。"""
    return FileResponse(_TEMPLATES / "m2-login.html")


@router.get("/apply", include_in_schema=False)
def apply_page() -> FileResponse:
    return FileResponse(_TEMPLATES / "m2-apply.html")


@router.get("/approve", include_in_schema=False)
def approve_page() -> FileResponse:
    return FileResponse(_TEMPLATES / "m2-approve.html")


@router.get("/rooms", tags=["M2 教室借用"])
def list_rooms(request: Request, _user: SessionUser = Depends(current_user)) -> dict:
    """登录后即可读取，供申请表单选择教室；写主数据仍归 G3。"""
    return {"items": applications.list_rooms(request.app.state.settings.database_path)}


@router.post("/applications", status_code=201, tags=["M2 教室借用"])
def create_application(
    payload: ApplicationCreate,
    request: Request,
    user: SessionUser = Depends(require_permission(APPLY_PERMISSION)),
) -> dict:
    try:
        start_at, end_at, hours = parse_period(payload.start_at, payload.end_at)
    except InvalidPeriod as error:
        raise api_error(422, str(error), "invalid_request") from error

    try:
        item = applications.create_application(
            request.app.state.settings.database_path,
            applicant_id=user.id,
            room_id=payload.room_id,
            start_at=start_at,
            end_at=end_at,
            purpose=payload.purpose,
            attendee_count=payload.attendee_count,
        )
    except applications.ApplicationRejected as error:
        raise _rejected(error) from error
    item["hours"] = hours
    return item


@router.get("/applications", tags=["M2 教室借用"])
def list_my_applications(
    request: Request,
    status: Optional[str] = Query(default=None, description="只看某个状态"),
    user: SessionUser = Depends(require_permission(APPLY_PERMISSION)),
) -> dict:
    if status is not None and status not in applications.STATUSES:
        raise api_error(422, "未知的申请状态", "invalid_request")
    statuses = (status,) if status else ()
    items = applications.list_applications(
        request.app.state.settings.database_path, applicant_id=user.id, statuses=statuses
    )
    return {"items": items, "total": len(items)}


@router.get("/applications/pending", tags=["M2 教室借用"])
def list_pending_applications(
    request: Request,
    _user: SessionUser = Depends(require_permission(APPROVE_PERMISSION)),
) -> dict:
    items = applications.list_applications(
        request.app.state.settings.database_path, statuses=(applications.STATUS_PENDING,)
    )
    return {"items": items, "total": len(items)}


@router.get("/applications/{application_id}", tags=["M2 教室借用"])
def get_application(
    application_id: int, request: Request, user: SessionUser = Depends(current_user)
) -> dict:
    item = applications.get_application(request.app.state.settings.database_path, application_id)
    if item is None:
        raise api_error(404, "申请不存在", "not_found")
    if item["applicant"]["id"] != user.id and not user.can(APPROVE_PERMISSION):
        raise api_error(403, "只能查看自己提交的申请", "forbidden")
    return item


@router.post("/applications/{application_id}/approve", tags=["M2 教室借用"])
def approve_application(
    application_id: int,
    payload: DecisionCreate,
    request: Request,
    user: SessionUser = Depends(require_permission(APPROVE_PERMISSION)),
) -> dict:
    return _decide(request, user, application_id, approved=True, note=payload.note)


@router.post("/applications/{application_id}/reject", tags=["M2 教室借用"])
def reject_application(
    application_id: int,
    payload: DecisionCreate,
    request: Request,
    user: SessionUser = Depends(require_permission(APPROVE_PERMISSION)),
) -> dict:
    if not payload.note:
        raise api_error(422, "驳回必须填写理由", "invalid_request")
    return _decide(request, user, application_id, approved=False, note=payload.note)


def _decide(
    request: Request, user: SessionUser, application_id: int, *, approved: bool, note: Optional[str]
) -> dict:
    try:
        return applications.decide_application(
            request.app.state.settings.database_path,
            application_id=application_id,
            approver_id=user.id,
            approved=approved,
            note=note,
        )
    except applications.ApplicationRejected as error:
        raise _rejected(error) from error
