from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.m3 import identity


@pytest.mark.parametrize("mode,status,code", [
    ("valid", 201, None), ("no-session", 401, "unauthenticated"),
    ("transitive-missing", 500, "internal_error"), ("broken", 500, "internal_error"),
])
def test_m3_r01_identity_adapter_uses_only_server_result(monkeypatch, report_app, report_client, mode, status, code):
    report_app.dependency_overrides.clear()

    def load(name):
        assert name == "app.d.auth.dependencies"
        if mode == "transitive-missing":
            raise ModuleNotFoundError("missing implementation dependency", name="app.d.auth.session")
        def current_user(request):
            assert isinstance(request, Request)
            if mode == "no-session":
                raise HTTPException(401, "private auth diagnostics")
            if mode == "broken":
                raise RuntimeError("private auth bug")
            return SimpleNamespace(id=1)  # 仅身份边界替身；业务授权仍查询真实临时库。
        return SimpleNamespace(current_user=current_user)
    monkeypatch.setattr(identity, "import_module", load)
    response = report_client.post("/m3/work-orders", json={"room_id": 10, "fault_type": "OTHER", "description": "损坏"}, headers={"X-User-Id": "2"})
    assert response.status_code == status
    if code:
        assert response.json()["error"] == code
        assert "private" not in response.text


def test_m3_errors_stay_local_with_future_shared_handler(report_app):
    async def shared_handler(request, error):
        return JSONResponse({"shared": True}, status_code=error.status_code)
    report_app.add_exception_handler(HTTPException, shared_handler)

    def unauthenticated():
        raise HTTPException(401, "login required")
    report_app.dependency_overrides[identity.authenticated_reporter] = unauthenticated

    @report_app.get("/shared-test")
    def shared_route():
        raise HTTPException(401)

    # 在应用启动、构建 middleware stack 之前安装未来的共享处理器。
    with TestClient(report_app) as client:
        assert client.get("/m3/rooms").json()["error"] == "unauthenticated"
        assert client.get("/shared-test").json() == {"shared": True}


def test_m3_page_and_assets_are_public_without_broken_login_link(report_client, report_app):
    response = report_client.get("/m3/report")
    assert response.status_code == 200
    assert "当前仅支持房间报修" in response.text
    assert 'data-login-available="false"' in response.text
    assert 'id="report-login" href="/m2/login" hidden' in response.text
    assert "maxlength=" not in response.text  # 原生 maxlength 按 UTF-16 计数，不适用于本契约。
    for asset in ["/assets/styles.css", "/assets/m3/report.css", "/assets/m3/report.js"]:
        assert report_client.get(asset).status_code == 200

    @report_app.get("/m2/login")
    def future_login():
        return {}
    assert 'data-login-available="true"' in report_client.get("/m3/report").text
