from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from app.common.config import Settings
from app.common.db import connect_database
from app.main import create_app
from app.m3 import identity as m3_identity
from app.m3.identity import authenticated_reporter
from app.m3.repository import get_repair_order


@pytest.fixture
def dispatch_data(database, insert_order):
    with connect_database(database) as connection:
        connection.executemany(
            "INSERT INTO app_user(id,username,password_hash,display_name) VALUES (?,?,'not-a-login-fixture',?)",
            [(i, f"dispatch_user_{i}", "相同姓名" if i in (4, 5) else f"虚构用户{i}") for i in range(3, 11)],
        )
        connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=9")
        connection.execute("UPDATE room SET name='<img src=x onerror=alert(1)>' WHERE id=10")
        connection.executemany("INSERT INTO permission(code,description) VALUES (?, '临时测试授权')",
                               [(code,) for code in ['repair:assign','repair:start','repair:read_own','repair:read_assigned']])
        for role, code in [('admin','repair:assign'), ('teacher','repair:start'), ('approver','repair:start'), ('student','repair:read_own'), ('repairer','repair:read_assigned')]:
            connection.execute("INSERT INTO role_permission SELECT r.id,p.id FROM role r,permission p WHERE r.code=? AND p.code=?", (role,code))
        # 维修角色本身没有 start；合法 start 可以来自另一个角色，不能错误要求来自 repairer。
        for user, roles in [(1,['student']), (3,['admin']), (4,['repairer','teacher']), (5,['repairer','teacher','approver']),
                            (6,['repairer']), (7,['teacher']), (9,['repairer','teacher']), (10,['admin'])]:
            for role in roles:
                connection.execute("INSERT INTO user_role SELECT ?,id FROM role WHERE code=?", (user,role))
        ids = {}
        for name, reporter, when in [('older',1,'2026-11-17T01:00:00Z'),('first',1,'2026-11-18T01:00:00Z'),('same',2,'2026-11-18T01:00:00Z')]:
            ids[name] = insert_order(connection, reporter_id=reporter, created_at=when, updated_at=when)
        ids['assigned'] = insert_order(connection, status='ASSIGNED', assigned_to=4, assigned_by=3, assigned_at='2026-11-18T02:00:00Z')
        ids['repair'] = insert_order(connection, status='IN_REPAIR', assigned_to=4, assigned_by=3, assigned_at='2026-11-18T02:00:00Z', started_at='2026-11-18T03:00:00Z')
    return ids


@pytest.fixture
def dispatch_identity():
    return {'id': 3}


@pytest.fixture
def dispatch_app(database, dispatch_data, dispatch_identity):
    app = create_app(Settings(database_path=database, version='m3-dispatch-test'))
    app.dependency_overrides[authenticated_reporter] = lambda: dispatch_identity['id']
    return app


@pytest.fixture
def dispatch_client(dispatch_app):
    with TestClient(dispatch_app) as client:
        yield client


def assign(client, order_id, target=4):
    return client.post(f'/m3/work-orders/{order_id}/assign', json={'assigned_to':target})


def snapshot(database):
    with connect_database(database, read_only=True) as connection:
        return [tuple(row) for row in connection.execute('SELECT * FROM repair_order ORDER BY id')]


def test_m3_r02_queue_default_filter_static_route_and_sort(dispatch_client, dispatch_data):
    response = dispatch_client.get('/m3/work-orders/dispatch')
    assert response.status_code == 200
    rows = response.json()['items']
    assert response.json()['total'] == 3
    assert [row['id'] for row in rows] == [dispatch_data[key] for key in ['same','first','older']]
    assert set(rows[0]) == {'id','room_id','room_name','fault_type','status','created_at','assigned_to','assigned_at','detail_url'}
    assert rows[0]['detail_url'] == f"/m3/orders/{rows[0]['id']}"
    for state, name in [('ASSIGNED','assigned'),('IN_REPAIR','repair')]:
        data = dispatch_client.get('/m3/work-orders/dispatch', params={'status':state}).json()
        assert data['total'] == 1 and data['items'][0]['id'] == dispatch_data[name]
    for state in ['', 'reported', 'DONE', "REPORTED' OR 1=1"]:
        assert dispatch_client.get('/m3/work-orders/dispatch', params={'status':state}).status_code == 422


def test_m3_r02_empty_queue_and_candidates_are_normal(dispatch_client, database):
    with connect_database(database) as connection:
        connection.execute('DELETE FROM repair_order')
        connection.execute("DELETE FROM role_permission WHERE permission_id=(SELECT id FROM permission WHERE code='repair:start')")
    assert dispatch_client.get('/m3/work-orders/dispatch').json() == {'items':[], 'total':0}
    assert dispatch_client.get('/m3/repairers').json() == {'items':[]}


def test_m3_r02_candidates_require_active_role_and_permission_across_roles(dispatch_client):
    response = dispatch_client.get('/m3/repairers')
    assert response.status_code == 200
    assert response.json() == {'items':[{'id':4,'display_name':'相同姓名'}, {'id':5,'display_name':'相同姓名'}]}


def test_m3_r02_success_commits_exact_fields_without_extra_operator_permissions(dispatch_client, dispatch_data, database):
    order_id = dispatch_data['first']
    before = get_repair_order(database, order_id)
    shared_before = None
    with connect_database(database, read_only=True) as connection:
        shared_before = {table:[tuple(row) for row in connection.execute(f'SELECT * FROM {table}')] for table in ['app_user','role','permission','user_role','role_permission','room']}
    start = datetime.now(timezone.utc).replace(microsecond=0)
    response = assign(dispatch_client, order_id)
    end = datetime.now(timezone.utc).replace(microsecond=0)
    assert response.status_code == 200
    after = get_repair_order(database, order_id)  # 独立连接，读取已提交结果。
    assert set(response.json()) == set(after) | {'room_name'}
    assert all(response.json()[key] == value for key, value in after.items())
    assert after['status'] == 'ASSIGNED' and after['assigned_to'] == 4 and after['assigned_by'] == 3
    assert after['assigned_at'] == after['updated_at'] and after['started_at'] is None
    assert start <= datetime.strptime(after['assigned_at'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc) <= end
    changed = {'status','assigned_to','assigned_by','assigned_at','updated_at'}
    assert {key:value for key,value in after.items() if key not in changed} == {key:value for key,value in before.items() if key not in changed}
    with connect_database(database, read_only=True) as connection:
        assert shared_before == {table:[tuple(row) for row in connection.execute(f'SELECT * FROM {table}')] for table in shared_before}
    assert dispatch_client.get('/m3/work-orders').status_code == 403  # assign 不隐含 read_own。


def test_m3_r02_permission_grants_not_admin_name_control_assignment(dispatch_client, dispatch_identity, database, dispatch_data):
    with connect_database(database) as connection:
        connection.execute("INSERT INTO role_permission SELECT r.id,p.id FROM role r,permission p WHERE r.code='student' AND p.code='repair:assign'")
        connection.execute("DELETE FROM role_permission WHERE role_id=(SELECT id FROM role WHERE code='admin') AND permission_id=(SELECT id FROM permission WHERE code='repair:assign')")
    assert assign(dispatch_client, dispatch_data['first']).status_code == 403
    dispatch_identity['id'] = 1
    assert assign(dispatch_client, dispatch_data['first']).status_code == 200
    assert get_repair_order(database, dispatch_data['first'])['assigned_by'] == 1
    assert all(row['id'] != dispatch_data['same'] for row in dispatch_client.get('/m3/work-orders').json()['items'])


def test_m3_r02_no_permission_precedes_object_queries(dispatch_client, dispatch_identity, dispatch_data, database):
    dispatch_identity['id'] = 2
    before = snapshot(database)
    for order_id in [dispatch_data['first'],dispatch_data['assigned'],99999]:
        assert assign(dispatch_client, order_id).status_code == 403
    for path in ['/m3/repairers','/m3/work-orders/dispatch']:
        assert dispatch_client.get(path).status_code == 403
    assert snapshot(database) == before
    with connect_database(database) as connection:
        connection.execute('ALTER TABLE repair_order RENAME COLUMN description TO hidden_for_permission_check')
    assert assign(dispatch_client, dispatch_data['first']).status_code == 403  # 若先取正文会变成 500。


@pytest.mark.parametrize('change,expected', [('disabled',401),('deleted',401),('revoked',403)])
def test_m3_r02_operator_rechecked_after_identity(dispatch_client, dispatch_app, database, dispatch_data, change, expected):
    before = snapshot(database)
    def identity_then_change():
        with connect_database(database) as connection:
            if change == 'disabled': connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=10")
            elif change == 'deleted': connection.execute('DELETE FROM app_user WHERE id=10')
            else: connection.execute("DELETE FROM role_permission WHERE permission_id=(SELECT id FROM permission WHERE code='repair:assign')")
        return 10
    dispatch_app.dependency_overrides[authenticated_reporter] = identity_then_change
    assert assign(dispatch_client, dispatch_data['first']).status_code == expected
    assert dispatch_client.get('/m3/repairers').status_code == expected
    assert dispatch_client.get('/m3/work-orders/dispatch').status_code == expected
    assert snapshot(database) == before


@pytest.mark.parametrize('target', [99999,9,6,7,3,2**80])
def test_m3_r02_ineligible_target_leaves_all_order_fields_unchanged(dispatch_client, dispatch_data, database, target):
    before = snapshot(database)
    response = assign(dispatch_client, dispatch_data['first'], target)
    assert response.status_code == 422 and response.json()['error'] == 'invalid_repairer'
    assert snapshot(database) == before


@pytest.mark.parametrize('change', ['disable','revoke','remove_role'])
def test_m3_r02_candidate_cache_cannot_authorize_later_write(dispatch_client, dispatch_data, database, change):
    assert 4 in [item['id'] for item in dispatch_client.get('/m3/repairers').json()['items']]
    before = snapshot(database)
    with connect_database(database) as connection:
        if change == 'disable': connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=4")
        elif change == 'revoke': connection.execute("DELETE FROM user_role WHERE user_id=4 AND role_id=(SELECT id FROM role WHERE code='teacher')")
        else: connection.execute("DELETE FROM user_role WHERE user_id=4 AND role_id=(SELECT id FROM role WHERE code='repairer')")
    assert assign(dispatch_client, dispatch_data['first']).status_code == 422
    assert snapshot(database) == before


def test_m3_r02_duplicate_and_in_repair_conflict_preserve_every_field(dispatch_client, dispatch_data, database):
    assert assign(dispatch_client, dispatch_data['first']).status_code == 200
    before = snapshot(database)
    for order_id in [dispatch_data['first'],dispatch_data['assigned'],dispatch_data['repair']]:
        response = assign(dispatch_client, order_id, 5)
        assert response.status_code == 409 and response.json()['error'] == 'conflict'
    assert snapshot(database) == before


@pytest.mark.parametrize('payload', [{'assigned_to':value} for value in [True,False,4.0,'4',None,0,-1,[],{}]] + [{}, {'assigned_to':4,'assigned_by':1}, {'assigned_to':4,'status':'ASSIGNED'}, {'assigned_to':4,'assigned_at':'x'}, {'assigned_to':4,'updated_at':'x'}, {'assigned_to':4,'reporter_id':1}])
def test_m3_r02_strict_payload_does_not_leak_input_or_wrong_field_hints(dispatch_client, dispatch_data, database, payload):
    before = snapshot(database)
    response = dispatch_client.post(f"/m3/work-orders/{dispatch_data['first']}/assign", json=payload)
    assert response.status_code == 422 and response.json()['error'] == 'invalid_request'
    assert 'assigned_to' in response.json()['message'] and 'room_id' not in response.text
    assert snapshot(database) == before


@pytest.mark.parametrize('raw', ['{','[]','null','"secret-user-input"'])
def test_m3_r02_invalid_json_has_assignment_specific_safe_message(dispatch_client, dispatch_data, database, raw):
    before = snapshot(database)
    response = dispatch_client.post(f"/m3/work-orders/{dispatch_data['first']}/assign", content=raw, headers={'Content-Type':'application/json'})
    assert response.status_code == 422
    assert 'assigned_to' in response.json()['message'] and 'room_id' not in response.text and 'secret-user-input' not in response.text
    assert snapshot(database) == before


@pytest.mark.parametrize('raw,expected', [('0',422),('-1',422),('true',422),('1.0',422),('１',422),('1 OR 1=1',422),('99999',404),('9223372036854775808',404),('9'*5000,404)])
def test_m3_r02_path_ids_fail_safely(dispatch_client, database, raw, expected):
    before = snapshot(database)
    assert assign(dispatch_client, quote(raw,safe='')).status_code == expected
    assert snapshot(database) == before


def test_m3_r02_two_independent_requests_cannot_overwrite_winner(dispatch_app, dispatch_data, database):
    barrier = Barrier(2)
    def compete(target):
        with TestClient(dispatch_app) as client:
            barrier.wait(timeout=10)
            response = assign(client, dispatch_data['first'], target)
            return target, response.status_code, response.json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(compete, [4,5]))
    winners = [result for result in results if result[1] == 200]
    assert len(winners) == 1
    assert all(result[1] in (200,409,503) for result in results)
    saved = get_repair_order(database, dispatch_data['first'])
    assert saved['assigned_to'] == winners[0][0]
    assert all(winners[0][2][key] == value for key,value in saved.items())
    with TestClient(dispatch_app) as client:
        assert assign(client, dispatch_data['first'], 5 if winners[0][0] == 4 else 4).status_code == 409
    assert get_repair_order(database, dispatch_data['first']) == saved


@pytest.mark.parametrize('failure', ['update','ignored_update','commit_constraint'])
def test_m3_r02_real_update_or_commit_failure_rolls_back(dispatch_client, dispatch_data, database, failure):
    before = snapshot(database)
    with connect_database(database) as connection:
        if failure == 'update':
            connection.execute("""CREATE TRIGGER fail_assignment AFTER UPDATE ON repair_order BEGIN
                UPDATE repair_order SET description='must roll back' WHERE id<>NEW.id;
                SELECT RAISE(FAIL,'private trigger detail'); END""")
        elif failure == 'ignored_update':
            connection.execute("CREATE TRIGGER ignore_assignment BEFORE UPDATE ON repair_order BEGIN SELECT RAISE(IGNORE); END")
        else:
            # 真实延迟外键只在 COMMIT 失败，触发器写入也必须随工单回滚。
            connection.execute('CREATE TABLE commit_guard (user_id INTEGER REFERENCES app_user(id) DEFERRABLE INITIALLY DEFERRED)')
            connection.execute('CREATE TRIGGER fail_commit AFTER UPDATE ON repair_order BEGIN INSERT INTO commit_guard VALUES (99999); END')
    response = assign(dispatch_client, dispatch_data['first'])
    assert response.status_code == (409 if failure == 'ignored_update' else 500)
    assert 'private trigger' not in response.text and str(database) not in response.text
    assert snapshot(database) == before
    if failure == 'commit_constraint':
        with connect_database(database) as connection:
            assert connection.execute('SELECT COUNT(*) FROM commit_guard').fetchone()[0] == 0


@pytest.mark.parametrize('phase', ['begin','commit'])
def test_m3_r02_real_lock_timeout_is_503_and_preserves_order(dispatch_client, dispatch_data, database, phase):
    before = snapshot(database)
    with connect_database(database) as blocker:
        blocker.execute('BEGIN IMMEDIATE' if phase == 'begin' else 'BEGIN')
        blocker.execute('SELECT * FROM repair_order').fetchall()
        response = assign(dispatch_client, dispatch_data['first'])
        assert response.status_code == 503 and response.json()['error'] == 'database_busy'
    assert snapshot(database) == before


def test_m3_r02_queue_and_candidates_are_read_only_without_write_lock(dispatch_client, database):
    before = database.read_bytes()
    with connect_database(database) as writer:
        writer.execute('BEGIN IMMEDIATE')
        assert dispatch_client.get('/m3/work-orders/dispatch').status_code == 200
        assert dispatch_client.get('/m3/repairers').status_code == 200
    assert database.read_bytes() == before


def test_m3_r02_missing_role_table_reports_schema_dependency(dispatch_client, database, dispatch_data):
    before = snapshot(database)
    with connect_database(database) as connection:
        connection.execute('ALTER TABLE role RENAME TO not_installed_role')
    responses = [dispatch_client.get('/m3/repairers'), dispatch_client.get('/m3/work-orders/dispatch'), assign(dispatch_client,dispatch_data['first'])]
    assert all(response.status_code == 503 and response.json()['error'] == 'schema_unavailable' for response in responses)
    assert snapshot(database) == before
    with connect_database(database) as connection:
        assert not connection.execute("SELECT 1 FROM sqlite_master WHERE name='role'").fetchall()


def test_m3_r02_missing_auth_and_invalid_session_fail_closed(dispatch_app, dispatch_client, dispatch_data, database, monkeypatch):
    # 明确模拟外部认证模块缺失，不依赖 G2 是否合入。
    def missing_auth_module(name):
        assert name == "app.d.auth.dependencies"
        raise ModuleNotFoundError(
            "shared authentication module unavailable",
            name="app.d.auth.dependencies",
        )

    monkeypatch.setattr(m3_identity, "import_module", missing_auth_module)
    before = snapshot(database)
    def expired(): raise HTTPException(401,'private session')
    for identity, code in [(expired,401), (None,503)]:
        if identity is None: dispatch_app.dependency_overrides.clear()
        else: dispatch_app.dependency_overrides[authenticated_reporter] = identity
        responses = [dispatch_client.get('/m3/repairers'),dispatch_client.get('/m3/work-orders/dispatch'),assign(dispatch_client,dispatch_data['first'])]
        assert all(response.status_code == code for response in responses)
        assert all('private session' not in response.text for response in responses)
    assert snapshot(database) == before
    assert dispatch_client.get('/health').status_code == 200


def test_m3_r02_public_page_assets_and_navigation(dispatch_client, dispatch_app, monkeypatch):
    # 显式隔离外部登录页面，不依赖 G2 是否合入。
    monkeypatch.setattr(
        dispatch_app.router,
        "routes",
        [
            route for route in dispatch_app.router.routes
            if getattr(route, "path", None) != "/m2/login"
        ],
    )
    html = dispatch_client.get('/m3/dispatch')
    assert html.status_code == 200 and 'data-login-available="false"' in html.text
    assert 'for="assigned-to"' in html.text and 'id="assignment-fields" disabled' in html.text
    assert 'not-a-login-fixture' not in html.text
    for path in ['/assets/m3/dispatch.js','/assets/m3/dispatch.css','/assets/m3/time.js']:
        assert dispatch_client.get(path).status_code == 200
    for path in ['/m3/report','/m3/my-orders','/m3/orders/1']:
        assert 'href="/m3/dispatch"' in dispatch_client.get(path).text
