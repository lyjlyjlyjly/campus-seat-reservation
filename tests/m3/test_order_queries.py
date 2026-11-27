from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from app.common.config import Settings
from app.common.db import connect_database
from app.main import create_app
from app.m3 import identity as m3_identity
from app.m3.identity import authenticated_reporter


OWN = "repair:read_own"
ASSIGNED = "repair:read_assigned"
MANAGE = "repair:assign"
NOT_FOUND = {"error": "not_found", "message": "工单不存在或不可访问"}


@pytest.fixture
def set_permissions(database):
    def grant(user_id, codes):
        # 每名测试用户对应一个真实角色；保留原 V1 的 room 权限，只调整临时 repair 授权。
        roles = {1: "student", 2: "teacher", 3: "admin", 4: "repairer", 5: "org_leader", 6: "approver"}
        with connect_database(database) as connection:
            role_id = connection.execute("SELECT id FROM role WHERE code = ?", (roles[user_id],)).fetchone()[0]
            connection.execute("INSERT OR IGNORE INTO user_role VALUES (?, ?)", (user_id, role_id))
            connection.execute("DELETE FROM role_permission WHERE role_id = ? AND permission_id IN (SELECT id FROM permission WHERE code LIKE 'repair:%')", (role_id,))
            for code in codes:
                connection.execute("INSERT OR IGNORE INTO permission (code, description) VALUES (?, '临时测试授权')", (code,))
                connection.execute("INSERT INTO role_permission SELECT ?, id FROM permission WHERE code = ?", (role_id, code))
    return grant


@pytest.fixture
def query_data(database, insert_order, set_permissions):
    with connect_database(database) as connection:
        connection.executemany(
            "INSERT INTO app_user (id, username, password_hash, display_name) VALUES (?, ?, 'not-a-login-fixture', '虚构查询用户')",
            [(i, f"query_user_{i}") for i in range(3, 7)],
        )
        ids = {}
        def order(name, reporter_id, created_at, **fields):
            ids[name] = insert_order(connection, reporter_id=reporter_id, created_at=created_at, updated_at=created_at, **fields)
        order("old", 1, "2026-11-17T09:00:00Z", description="<script>alert(1)</script>\n第二行  保留")
        order("other", 2, "2026-11-18T09:00:00Z")
        order("tie_first", 1, "2026-11-18T09:00:00Z")
        order("tie_last", 1, "2026-11-18T09:00:00Z")
        order("assigned", 2, "2026-11-18T11:00:00Z", status="ASSIGNED", assigned_to=4, assigned_by=3, assigned_at="2026-11-18T11:10:00Z")
        order("repair", 1, "2026-11-18T12:00:00Z", status="IN_REPAIR", assigned_to=2, assigned_by=3, assigned_at="2026-11-18T12:10:00Z", started_at="2026-11-18T12:20:00Z")
        order("admin", 3, "2026-11-18T10:00:00Z")
        connection.execute("UPDATE room SET name = '<img src=x onerror=alert(1)>' WHERE id=10")
    for user_id, codes in [(1, [OWN]), (2, [OWN]), (3, [OWN, MANAGE]), (4, [ASSIGNED]), (5, [OWN]), (6, [OWN])]:
        set_permissions(user_id, codes)
    return ids


@pytest.fixture
def query_identity():
    return {"id": 1}


@pytest.fixture
def query_app(database, query_data, query_identity):
    app = create_app(Settings(database_path=database, version="m3-query-test"))
    app.dependency_overrides[authenticated_reporter] = lambda: query_identity["id"]
    return app


@pytest.fixture
def query_client(query_app):
    with TestClient(query_app) as client:
        yield client


def test_m3_r01_each_user_gets_only_own_orders_in_stable_order(query_client, query_identity, query_data):
    for user_id, names in [(1, ["repair", "tie_last", "tie_first", "old"]), (2, ["assigned", "other"]), (3, ["admin"])]:
        query_identity["id"] = user_id
        response = query_client.get("/m3/work-orders", headers={"X-User-Id": "2"})
        assert response.status_code == 200
        data = response.json()
        assert set(data) == {"items", "total"}
        assert data["total"] == len(names)
        assert [row["id"] for row in data["items"]] == [query_data[name] for name in names]
        assert all(set(row) == {"id", "room_id", "room_name", "fault_type", "status", "created_at"} for row in data["items"])


def test_m3_r01_query_identity_cannot_be_selected_by_client(query_client):
    for query in ["reporter_id=2", "reporter_id=1", "page=2", "search=test"]:
        response = query_client.get("/m3/work-orders?" + query)
        assert response.status_code == 422
        assert response.json()["error"] == "invalid_request"


def test_m3_r01_empty_list_is_normal(query_client, query_identity):
    query_identity["id"] = 5
    assert query_client.get("/m3/work-orders").json() == {"items": [], "total": 0}


@pytest.mark.parametrize("user_id,codes,name,expected", [
    (1, [OWN], "old", 200), (1, [OWN], "other", 404),
    (2, [OWN], "repair", 404), (2, [ASSIGNED], "repair", 200),
    (2, [ASSIGNED], "other", 404), (4, [ASSIGNED], "assigned", 200),
    (4, [ASSIGNED], "old", 404), (3, [MANAGE], "old", 200),
    (3, [OWN, MANAGE], "assigned", 200), (1, [ASSIGNED], "old", 404),
    (2, [OWN, ASSIGNED], "repair", 200), (2, [OWN, ASSIGNED], "other", 200),
    (1, [OWN, ASSIGNED], "assigned", 404), (1, [], "old", 403),
    (1, ["repair:report"], "old", 403), (1, ["repair:start"], "old", 403),
])
def test_m3_r01_detail_permissions_and_object_scope(query_client, query_identity, query_data, set_permissions, user_id, codes, name, expected):
    query_identity["id"] = user_id
    set_permissions(user_id, codes)
    response = query_client.get(f"/m3/work-orders/{query_data[name]}")
    assert response.status_code == expected
    if expected == 404:
        assert response.json() == NOT_FOUND
    elif expected == 200:
        assert response.json()["id"] == query_data[name]
    else:
        assert response.json()["error"] == "forbidden"


def test_m3_r01_admin_assign_permission_alone_does_not_grant_personal_list(query_client, query_identity, query_data, set_permissions):
    query_identity["id"] = 3
    set_permissions(3, [MANAGE])
    assert query_client.get("/m3/work-orders").status_code == 403
    assert query_client.get(f"/m3/work-orders/{query_data['other']}").status_code == 200


def test_m3_r01_invisible_and_absent_have_identical_response(query_client, query_data):
    inaccessible = query_client.get(f"/m3/work-orders/{query_data['other']}")
    absent = query_client.get("/m3/work-orders/99999")
    assert inaccessible.status_code == absent.status_code == 404
    assert inaccessible.content == absent.content
    assert absent.json() == NOT_FOUND


def test_m3_r01_no_function_permission_is_checked_before_target_query(query_client, database, query_data, set_permissions):
    set_permissions(1, [])
    # 临时真实库故障注入：若提前 SELECT 正文会触发列缺失，必须先返回 403。
    with connect_database(database) as connection:
        connection.execute("ALTER TABLE repair_order RENAME COLUMN description TO hidden_for_guard_test")
    for order_id in [query_data["old"], 99999]:
        response = query_client.get(f"/m3/work-orders/{order_id}")
        assert response.status_code == 403
        assert response.json()["error"] == "forbidden"


def test_m3_r01_read_permission_and_report_permission_are_independent(query_client, query_data, set_permissions):
    data = {"room_id": 10, "fault_type": "OTHER", "description": "查询账号没有创建权限"}
    assert query_client.get("/m3/work-orders").status_code == 200
    assert query_client.get(f"/m3/work-orders/{query_data['old']}").status_code == 200
    assert query_client.post("/m3/work-orders", json=data).status_code == 403
    set_permissions(1, ["repair:report"])
    assert query_client.get("/m3/work-orders").status_code == 403
    assert query_client.get(f"/m3/work-orders/{query_data['old']}").status_code == 403
    assert query_client.post("/m3/work-orders", json=data).status_code == 201


@pytest.mark.parametrize("action,expected", [("disable", 401), ("delete", 401), ("revoke", 403)])
def test_m3_r01_read_rechecks_user_and_permissions_after_identity(query_app, query_client, database, query_data, set_permissions, action, expected):
    def authenticated_then_changed():
        user_id = 6 if action == "delete" else 1
        if action == "revoke":
            set_permissions(1, [])
        else:
            with connect_database(database) as connection:
                if action == "delete":
                    connection.execute("DELETE FROM app_user WHERE id=6")
                else:
                    connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=1")
        return user_id
    query_app.dependency_overrides[authenticated_reporter] = authenticated_then_changed
    for path in ["/m3/work-orders", f"/m3/work-orders/{query_data['old']}"]:
        assert query_client.get(path).status_code == expected


def test_m3_r01_read_authentication_errors_and_unavailable_dependency(query_app, query_client, query_data, monkeypatch):
    def unauthenticated():
        raise HTTPException(401, "private session detail")
    query_app.dependency_overrides[authenticated_reporter] = unauthenticated
    for path in ["/m3/work-orders", f"/m3/work-orders/{query_data['old']}"]:
        response = query_client.get(path)
        assert response.status_code == 401
        assert "private" not in response.text
    # 明确模拟外部认证模块缺失，不依赖 G2 是否合入。
    def missing_auth_module(name):
        assert name == "app.d.auth.dependencies"
        raise ModuleNotFoundError(
            "shared authentication module unavailable",
            name="app.d.auth.dependencies",
        )

    monkeypatch.setattr(m3_identity, "import_module", missing_auth_module)
    query_app.dependency_overrides.clear()
    for path in ["/m3/work-orders", f"/m3/work-orders/{query_data['old']}"]:
        response = query_client.get(path)
        assert response.status_code == 503
        assert response.json()["error"] == "auth_unavailable"
    assert query_client.get("/health").status_code == 200


@pytest.mark.parametrize("order_id", ["0", "-1", "true", "1.0", "+1", " 1", "１", "1 OR 1=1"])
def test_m3_r01_bad_path_id_returns_422(query_client, order_id):
    response = query_client.get("/m3/work-orders/" + quote(order_id, safe=""))
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"


@pytest.mark.parametrize("order_id", ["9223372036854775807", "9223372036854775808", "9" * 5000])
def test_m3_r01_oversized_or_absent_id_does_not_overflow(query_client, order_id):
    response = query_client.get("/m3/work-orders/" + order_id)
    assert response.status_code == 404
    assert response.json() == NOT_FOUND


def test_m3_r01_detail_response_whitelist_and_leading_zero(query_client, query_data):
    response = query_client.get(f"/m3/work-orders/000{query_data['old']}")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"id", "reporter_id", "room_id", "room_name", "fault_type", "description", "status", "assigned_to", "assigned_by", "assigned_at", "started_at", "created_at", "updated_at"}
    assert data["description"] == "<script>alert(1)</script>\n第二行  保留"
    assert data["room_name"] == "<img src=x onerror=alert(1)>"
    assert data["assigned_at"] is None and data["started_at"] is None


def test_m3_r01_queries_leave_database_bytes_unchanged(query_client, database, query_data):
    before = database.read_bytes()
    assert query_client.get("/m3/work-orders").status_code == 200
    assert query_client.get(f"/m3/work-orders/{query_data['old']}").status_code == 200
    assert query_client.get(f"/m3/work-orders/{query_data['other']}").status_code == 404
    assert database.read_bytes() == before


def test_m3_r01_queries_do_not_take_write_lock_and_read_committed_snapshot(query_client, database, query_data):
    with connect_database(database) as writer:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE repair_order SET description='尚未提交的修改' WHERE id=?", (query_data["old"],))
        assert query_client.get("/m3/work-orders").status_code == 200
        response = query_client.get(f"/m3/work-orders/{query_data['old']}")
        assert response.status_code == 200
        assert response.json()["description"] == "<script>alert(1)</script>\n第二行  保留"
        writer.rollback()


def test_m3_query_pages_and_navigation_do_not_render_private_data(query_client, query_app, monkeypatch):
    # 显式隔离外部登录页面，不依赖 G2 是否合入。
    monkeypatch.setattr(
        query_app.router,
        "routes",
        [
            route for route in query_app.router.routes
            if getattr(route, "path", None) != "/m2/login"
        ],
    )
    for path in ["/m3/my-orders", "/m3/orders/1"]:
        page = query_client.get(path)
        assert page.status_code == 200
        assert "alert(1)" not in page.text
        assert 'data-login-available="false"' in page.text
    report = query_client.get("/m3/report").text
    assert 'href="/m3/my-orders"' in report and 'id="created-order-link" hidden' in report
    assert query_client.get("/m3/orders/%3Cscript%3E").status_code == 422
    for path in ["/assets/m3/orders.js", "/assets/m3/orders.css"]:
        assert query_client.get(path).status_code == 200
