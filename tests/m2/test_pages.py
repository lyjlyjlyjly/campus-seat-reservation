"""G2 页面可访问性：登录、申请、审批三个页面与它们引用的静态资源。

不启动浏览器，只断言服务端交付的 HTML/JS/CSS，交互逻辑靠 API 测试覆盖。
"""

from fastapi.testclient import TestClient

PAGES = {
    "/m2/login": ('data-page="login"', "演示账号登录"),
    "/m2/apply": ('data-page="apply"', "整教室借用申请"),
    "/m2/approve": ('data-page="approve"', "教室借用审批台"),
}


def test_pages_are_served_without_login(seeded_client: TestClient):
    for path, (marker, title) in PAGES.items():
        response = seeded_client.get(path)
        assert response.status_code == 200, path
        assert response.headers["content-type"].startswith("text/html"), path
        body = response.text
        assert marker in body, path
        assert title in body, path
        assert "/assets/m2.js" in body and "/assets/m2.css" in body, path
        if path != "/m2/login":
            # 业务页只通过接口取数，服务端不渲染任何账号数据。
            assert "Teacher#2026" not in body


def test_static_assets_are_served(seeded_client: TestClient):
    for path in ("/assets/m2.js", "/assets/m2.css"):
        response = seeded_client.get(path)
        assert response.status_code == 200, path
        assert len(response.text) > 200, path


def test_login_page_lists_only_fictional_demo_accounts(seeded_client: TestClient):
    body = seeded_client.get("/m2/login").text
    for username in ("teacher01", "leader01", "approver01", "student01"):
        assert username in body
    assert "虚构数据" in body
