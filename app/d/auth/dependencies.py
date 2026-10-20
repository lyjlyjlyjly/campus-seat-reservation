"""可复用的认证与授权依赖，供 M1/M2/M3 路由共用。"""

from fastapi import Depends, Request

from app.d.auth.errors import api_error
from app.d.auth.session import COOKIE_NAME, find_session_user
from app.d.auth.users import SessionUser


def current_user(request: Request) -> SessionUser:
    token = request.cookies.get(COOKIE_NAME, "")
    if not token:
        raise api_error(401, "请先登录")
    user = find_session_user(request.app.state.settings.database_path, token)
    if user is None:
        raise api_error(401, "会话已失效，请重新登录")
    return user


def require_permission(code: str):
    """返回“已登录且拥有指定权限”的依赖；401 与 403 严格区分。"""

    def dependency(user: SessionUser = Depends(current_user)) -> SessionUser:
        if not user.can(code):
            raise api_error(403, f"缺少权限：{code}")
        return user

    return dependency
