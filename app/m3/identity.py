"""唯一共享认证接入点；禁止从业务参数/自定义请求头认领身份。"""

from importlib import import_module

from fastapi import Request

from app.m3.errors import ReportError


def authenticated_reporter(request: Request) -> int:
    """参考 dd74749 的同步 current_user(request)，只提取服务端用户 ID。

    若 G2 后续改成其他 Depends 组合，只在这里适配。测试可以通过 FastAPI
    dependency_overrides 替换本函数，正常应用没有环境变量/演示身份后门。
    """
    try:
        module = import_module("app.d.auth.dependencies")
    except ModuleNotFoundError as error:
        if error.name not in {"app.d.auth", "app.d.auth.dependencies"}:
            raise
        raise ReportError(503, "auth_unavailable", "共享登录尚未接入，当前暂不可提交报修") from error
    user = module.current_user(request)
    if user is None:
        raise ReportError(401, "unauthenticated", "请先登录")
    if type(user.id) is not int or user.id <= 0:
        raise RuntimeError("共享认证返回了不符合契约的身份")
    return user.id
