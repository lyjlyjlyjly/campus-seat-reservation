"""认证接口：登录、退出、当前身份。挂在 /m2 下，三组共用同一会话。"""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app.common.db import connect_database
from app.d.auth.errors import api_error
from app.d.auth.dependencies import current_user
from app.d.auth.password import verify_password
from app.d.auth.session import (
    COOKIE_NAME,
    SESSION_TTL_MINUTES,
    create_session,
    find_session_user,
    revoke_session,
)
from app.d.auth.users import SessionUser, find_credentials


router = APIRouter()

# 账号不存在时也做一次同等代价的派生校验，避免用响应时间枚举用户名。
_DUMMY_HASH = "pbkdf2_sha256$200000$" + "00" * 16 + "$" + "11" * 32


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def _identity(user: SessionUser) -> dict:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "roles": list(user.roles),
        "permissions": list(user.permissions),
    }


@router.post("/auth/login", tags=["认证"])
def login(payload: LoginRequest, request: Request, response: Response) -> dict:
    settings = request.app.state.settings
    with connect_database(settings.database_path) as connection:
        credentials = find_credentials(connection, payload.username)

    stored = credentials.password_hash if credentials is not None else _DUMMY_HASH
    matched = verify_password(payload.password, stored)
    if credentials is None or not matched or credentials.status != "ACTIVE":
        # 不区分“账号不存在”“口令错误”“账号停用”，也不创建会话。
        raise api_error(401, "用户名或口令错误")

    token, expires_at = create_session(settings.database_path, credentials.id)
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_TTL_MINUTES * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )
    user = find_session_user(settings.database_path, token)
    if user is None:  # 并发删除等极端情况，不返回半成品会话。
        raise api_error(401, "登录失败，请重试")

    payload_identity = _identity(user)
    payload_identity["expires_at"] = expires_at
    return payload_identity


@router.post("/auth/logout", tags=["认证"])
def logout(request: Request, response: Response) -> dict:
    settings = request.app.state.settings
    token = request.cookies.get(COOKIE_NAME, "")
    revoked = revoke_session(settings.database_path, token) if token else False
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"status": "logged_out", "revoked": revoked}


@router.get("/auth/me", tags=["认证"])
def me(user: SessionUser = Depends(current_user)) -> dict:
    return _identity(user)
