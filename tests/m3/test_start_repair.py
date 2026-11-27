"""真实 SQLite / M3 API；只替换外部认证边界，不模拟业务或数据库。"""
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
def start_data(database, insert_order):
    with connect_database(database) as connection:
        connection.executemany(
            "INSERT INTO app_user(id,username,password_hash,display_name) VALUES (?,?,'not-a-login-fixture',?)",
            [(i, f'start_test_{i}', f'虚构用户{i}') for i in range(3, 9)],
        )
        codes = ['repair:report','repair:read_own','repair:read_assigned','repair:assign','repair:start']
        connection.executemany("INSERT INTO permission(code,description) VALUES (?,'临时测试授权')", [(c,) for c in codes])
        grants = {'student':['repair:report','repair:read_own'], 'repairer':['repair:read_assigned','repair:start'],
                  'admin':['repair:assign','repair:read_assigned','repair:start'],
                  'teacher':['repair:start'], 'approver':['repair:read_assigned']}
        for role, permissions in grants.items():
            for code in permissions:
                connection.execute('INSERT INTO role_permission SELECT r.id,p.id FROM role r,permission p WHERE r.code=? AND p.code=?', (role,code))
        for user, role in [(1,'student'),(3,'admin'),(4,'repairer'),(5,'repairer'),(6,'teacher'),(7,'approver'),(8,'repairer')]:
            connection.execute('INSERT INTO user_role SELECT ?,id FROM role WHERE code=?', (user,role))
        connection.execute("UPDATE room SET name='<img src=x onerror=alert(1)>' WHERE id=10")
        ids={}
        for name, user, when in [('older',4,'2026-11-12T01:00:00Z'),('own',4,'2026-11-12T02:00:00Z'),
                                 ('same',4,'2026-11-12T02:00:00Z'),('other',5,'2026-11-12T02:00:00Z'),
                                 ('admin',3,'2026-11-12T02:00:00Z'),('start_only',6,'2026-11-12T02:00:00Z'),
                                 ('read_only',7,'2026-11-12T02:00:00Z')]:
            ids[name]=insert_order(connection,status='ASSIGNED',assigned_to=user,assigned_by=3,
                                   assigned_at='2026-11-12T03:00:00Z',created_at=when)
        ids['repair']=insert_order(connection,status='IN_REPAIR',assigned_to=4,assigned_by=3,
                                  assigned_at='2026-11-12T03:00:00Z',started_at='2026-11-12T04:00:00Z')
        ids['reported']=insert_order(connection)
    return ids


@pytest.fixture
def start_identity():
    return {'id':4}


@pytest.fixture
def start_app(database, start_data, start_identity):
    app=create_app(Settings(database_path=database,version='m3-start-test'))
    app.dependency_overrides[authenticated_reporter]=lambda: start_identity['id']
    return app


@pytest.fixture
def start_client(start_app):
    with TestClient(start_app) as client:
        yield client


def start(client, order_id):
    return client.post(f'/m3/work-orders/{order_id}/start',json={})


def snapshot(database):
    with connect_database(database,read_only=True) as connection:
        return [tuple(row) for row in connection.execute('SELECT * FROM repair_order ORDER BY id')]


def test_m3_r03_assigned_scope_sort_white_list_and_static_route(start_client,start_identity,start_data):
    for user,names in [(4,['repair','same','own','older']),(5,['other']),(3,['admin'])]:
        start_identity['id']=user
        response=start_client.get('/m3/work-orders/assigned')
        assert response.status_code==200
        data=response.json()
        assert data['total']==len(names)
        assert [item['id'] for item in data['items']]==[start_data[n] for n in names]
        for item in data['items']:
            assert set(item)=={'id','room_id','room_name','fault_type','status','created_at','assigned_at','started_at','updated_at','can_start'}
            assert item['can_start']==(item['status']=='ASSIGNED')


def test_m3_r03_assigned_filter_empty_and_reject_client_identity(start_client,start_identity,start_data):
    for state,names in [('ASSIGNED',['same','own','older']),('IN_REPAIR',['repair'])]:
        response=start_client.get('/m3/work-orders/assigned',params={'status':state})
        assert response.status_code==200
        assert [row['id'] for row in response.json()['items']]==[start_data[n] for n in names]
    for query in ['status=','status=REPORTED','status=assigned','status=DONE','assigned_to=5','reporter_id=5','user_id=5',
                  'status=ASSIGNED&status=IN_REPAIR','status=ASSIGNED&extra=1']:
        assert start_client.get('/m3/work-orders/assigned?'+query).status_code==422
    start_identity['id']=8
    assert start_client.get('/m3/work-orders/assigned').json()=={'items':[],'total':0}


def test_m3_r03_read_only_and_start_only_permissions_are_independent(start_client,start_identity,start_data,database):
    start_identity['id']=7
    rows=start_client.get('/m3/work-orders/assigned').json()['items']
    assert len(rows)==1 and rows[0]['can_start'] is False
    assert start(start_client,start_data['read_only']).status_code==403
    start_identity['id']=6  # teacher + start，仅此权限；没有 repairer 角色或任何读取权限。
    assert start_client.get('/m3/work-orders/assigned').status_code==403
    assert start_client.get(f"/m3/work-orders/{start_data['start_only']}").status_code==403
    # 开始操作不依赖 role 资格查询；共享表数据不在请求中写入。
    with connect_database(database) as connection:
        connection.execute('ALTER TABLE role RENAME TO role_not_needed_for_start')
    result=start(start_client,start_data['start_only'])
    assert result.status_code==200
    assert set(result.json())=={'id','status','started_at','updated_at'}
    assert start_client.get(f"/m3/work-orders/{start_data['start_only']}").status_code==403


def test_m3_r03_success_commits_same_time_and_preserves_assignment(start_client,start_data,database):
    before=get_repair_order(database,start_data['own'])
    with connect_database(database,read_only=True) as connection:
        shared={table:[tuple(row) for row in connection.execute(f'SELECT * FROM {table}')] for table in ['app_user','role','permission','user_role','role_permission','room']}
    begin=datetime.now(timezone.utc).replace(microsecond=0)
    response=start(start_client,start_data['own'])
    end=datetime.now(timezone.utc).replace(microsecond=0)
    assert response.status_code==200
    saved=get_repair_order(database,start_data['own'])
    assert response.json()=={key:saved[key] for key in ['id','status','started_at','updated_at']}
    assert saved['status']=='IN_REPAIR' and saved['started_at']==saved['updated_at']
    assert begin<=datetime.strptime(saved['started_at'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)<=end
    assert {k:v for k,v in saved.items() if k not in {'status','started_at','updated_at'}}=={k:v for k,v in before.items() if k not in {'status','started_at','updated_at'}}
    with connect_database(database,read_only=True) as connection:
        assert shared=={table:[tuple(row) for row in connection.execute(f'SELECT * FROM {table}')] for table in shared}


def test_m3_r03_permissions_precede_target_and_do_not_grant_details(start_client,start_identity,start_data,database):
    start_identity['id']=1  # report/read_own 不隐含 start/read_assigned。
    before=snapshot(database)
    for target in [start_data['own'],start_data['reported'],99999]:
        assert start(start_client,target).status_code==403
    assert start_client.get('/m3/work-orders/assigned').status_code==403
    with connect_database(database) as connection:
        connection.execute('ALTER TABLE repair_order RENAME COLUMN assigned_to TO hidden_for_auth_check')
    assert start(start_client,start_data['own']).status_code==403  # 先查目标将导致 SQL 错误。
    assert snapshot(database)==before


def test_m3_r03_non_assignee_including_admin_denied_before_state(start_client,start_identity,start_data,database):
    before=snapshot(database)
    for user in [3,5]:  # admin 即便有 assign + start 也不能代替实际受理人。
        start_identity['id']=user
        for name in ['own','repair','reported']:
            response=start(start_client,start_data[name])
            assert response.status_code==403 and response.json()['error']=='forbidden'
            assert 'description' not in response.json()
    start_identity['id']=4
    assert start(start_client,start_data['reported']).status_code==403
    assert snapshot(database)==before


@pytest.mark.parametrize('change,expected',[('disable',401),('delete',401),('revoke',403)])
def test_m3_r03_identity_and_permission_rechecked_in_transaction(start_client,start_app,start_data,database,change,expected):
    before=snapshot(database)
    def identity_then_change():
        with connect_database(database) as connection:
            if change=='disable': connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=4")
            elif change=='delete': connection.execute('DELETE FROM app_user WHERE id=8')
            else: connection.execute("DELETE FROM role_permission WHERE permission_id=(SELECT id FROM permission WHERE code='repair:start')")
        return 8 if change=='delete' else 4
    start_app.dependency_overrides[authenticated_reporter]=identity_then_change
    assert start(start_client,start_data['own']).status_code==expected
    assert snapshot(database)==before


def test_m3_r03_list_rechecks_revoked_read_permission_and_disabled_user(start_client,start_app,database):
    def revoked_identity():
        with connect_database(database) as connection:
            connection.execute("DELETE FROM role_permission WHERE permission_id=(SELECT id FROM permission WHERE code='repair:read_assigned')")
        return 4
    start_app.dependency_overrides[authenticated_reporter]=revoked_identity
    assert start_client.get('/m3/work-orders/assigned').status_code==403
    with connect_database(database) as connection:
        connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=4")
    assert start_client.get('/m3/work-orders/assigned').status_code==401


def test_m3_r03_can_start_snapshot_does_not_authorize_later_write(start_client,start_data,database):
    assert any(row['id']==start_data['own'] and row['can_start'] for row in start_client.get('/m3/work-orders/assigned').json()['items'])
    before=snapshot(database)
    with connect_database(database) as connection:
        connection.execute("DELETE FROM role_permission WHERE permission_id=(SELECT id FROM permission WHERE code='repair:start')")
    assert start(start_client,start_data['own']).status_code==403
    assert all(not row['can_start'] for row in start_client.get('/m3/work-orders/assigned').json()['items'])
    assert snapshot(database)==before


@pytest.mark.parametrize('raw',['','null','[]','true','1','"secret-input"','{','{"status":"IN_REPAIR"}',
                                  '{"assigned_to":4}','{"started_at":"fake"}','{"updated_at":"fake"}',
                                  '{"operator_id":4}','{"extra":null}'])
def test_m3_r03_requires_explicit_empty_json_body(start_client,start_data,database,raw):
    before=snapshot(database)
    response=start_client.post(f"/m3/work-orders/{start_data['own']}/start",content=raw,headers={'Content-Type':'application/json'})
    assert response.status_code==422 and response.json()['error']=='invalid_request'
    assert '空 JSON 对象 {}' in response.json()['message']
    assert 'secret-input' not in response.text and 'room_id' not in response.text and 'assigned_to' not in response.text
    assert snapshot(database)==before


@pytest.mark.parametrize('raw,expected',[('0',422),('-1',422),('1.0',422),('true',422),('１',422),('1 OR 1=1',422),
                                         ('99999',404),('9223372036854775808',404),('9'*5000,404)])
def test_m3_r03_invalid_and_huge_path_ids(start_client,database,raw,expected):
    before=snapshot(database)
    assert start(start_client,quote(raw,safe='')).status_code==expected
    assert snapshot(database)==before


def test_m3_r03_duplicate_start_never_changes_first_time(start_client,start_data,database):
    assert start(start_client,start_data['own']).status_code==200
    before=snapshot(database)
    for name in ['own','repair']:
        result=start(start_client,start_data[name])
        assert result.status_code==409 and result.json()['error']=='conflict'
    assert snapshot(database)==before


def test_m3_r03_two_real_connections_start_at_most_once(start_app,start_data,database):
    barrier=Barrier(2)
    def compete(_):
        with TestClient(start_app) as client:
            barrier.wait(timeout=10)
            response=start(client,start_data['own'])
            return response.status_code,response.json()
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(compete,[1,2]))
    winners=[data for status,data in results if status==200]
    assert len(winners)==1 and all(status in (200,409,503) for status,_ in results)
    saved=get_repair_order(database,start_data['own'])
    assert winners[0]=={key:saved[key] for key in ['id','status','started_at','updated_at']}
    with TestClient(start_app) as client:
        assert start(client,start_data['own']).status_code==409
    assert get_repair_order(database,start_data['own'])==saved


@pytest.mark.parametrize('failure',['update','ignored','commit'])
def test_m3_r03_real_update_and_commit_failures_rollback(start_client,start_data,database,failure):
    before=snapshot(database)
    with connect_database(database) as connection:
        if failure=='update':
            connection.execute("""CREATE TRIGGER fail_start AFTER UPDATE ON repair_order BEGIN
                UPDATE repair_order SET description='must roll back' WHERE id<>NEW.id;
                SELECT RAISE(FAIL,'private SQL failure'); END""")
        elif failure=='ignored':
            connection.execute('CREATE TRIGGER ignore_start BEFORE UPDATE ON repair_order BEGIN SELECT RAISE(IGNORE); END')
        else:
            connection.execute('CREATE TABLE start_commit_guard (user_id INTEGER REFERENCES app_user(id) DEFERRABLE INITIALLY DEFERRED)')
            connection.execute('CREATE TRIGGER fail_start_commit AFTER UPDATE ON repair_order BEGIN INSERT INTO start_commit_guard VALUES (99999); END')
    result=start(start_client,start_data['own'])
    assert result.status_code==(409 if failure=='ignored' else 500)
    assert str(database) not in result.text and 'private SQL' not in result.text
    assert snapshot(database)==before
    if failure=='commit':
        with connect_database(database) as connection:
            assert connection.execute('SELECT COUNT(*) FROM start_commit_guard').fetchone()[0]==0


@pytest.mark.parametrize('phase',['begin','commit'])
def test_m3_r03_real_database_lock_is_503_and_rolls_back(start_client,start_data,database,phase):
    before=snapshot(database)
    with connect_database(database) as blocker:
        blocker.execute('BEGIN IMMEDIATE' if phase=='begin' else 'BEGIN')
        blocker.execute('SELECT * FROM repair_order').fetchall()
        result=start(start_client,start_data['own'])
        assert result.status_code==503 and result.json()['error']=='database_busy'
    assert snapshot(database)==before


def test_m3_r03_list_is_read_only_without_write_lock(start_client,database):
    before=database.read_bytes()
    with connect_database(database) as blocker:
        blocker.execute('BEGIN IMMEDIATE')
        assert start_client.get('/m3/work-orders/assigned').status_code==200
    assert database.read_bytes()==before


def test_m3_r03_missing_auth_and_expired_identity_fail_closed(start_app,start_client,start_data,database,monkeypatch):
    # 明确模拟外部认证模块缺失，不依赖 G2 是否合入。
    def missing_auth_module(name):
        assert name == "app.d.auth.dependencies"
        raise ModuleNotFoundError(
            "shared authentication module unavailable",
            name="app.d.auth.dependencies",
        )

    monkeypatch.setattr(m3_identity, "import_module", missing_auth_module)
    before=snapshot(database)
    def expired(): raise HTTPException(401,'private session detail')
    for identity,status in [(expired,401),(None,503)]:
        if identity is None: start_app.dependency_overrides.clear()
        else: start_app.dependency_overrides[authenticated_reporter]=identity
        for result in [start_client.get('/m3/work-orders/assigned'),start(start_client,start_data['own'])]:
            assert result.status_code==status and 'private session' not in result.text
    assert snapshot(database)==before
    assert start_client.get('/health').status_code==200


def test_m3_r03_module_flow_report_assign_start_query(start_client,start_identity,database):
    """模块流程测试，不是共享登录联调；每一步都经过实际路由、事务和授权。"""
    start_identity['id']=1
    created=start_client.post('/m3/work-orders',json={'room_id':20,'fault_type':'OTHER','description':'  中文灯管故障\n第二行😀  '})
    assert created.status_code==201
    order_id=created.json()['id']
    start_identity['id']=3
    assigned=start_client.post(f'/m3/work-orders/{order_id}/assign',json={'assigned_to':4})
    assert assigned.status_code==200
    start_identity['id']=4
    assert order_id in [row['id'] for row in start_client.get('/m3/work-orders/assigned').json()['items']]
    begun=start(start_client,order_id)
    assert begun.status_code==200
    start_identity['id']=1
    detail=start_client.get(f'/m3/work-orders/{order_id}')
    assert detail.status_code==200
    assert detail.json()['status']=='IN_REPAIR' and detail.json()['description']=='中文灯管故障\n第二行😀'
    assert detail.json()['reporter_id']==1 and detail.json()['assigned_to']==4 and detail.json()['assigned_by']==3
    assert created.json()['created_at']<=assigned.json()['assigned_at']<=begun.json()['started_at']  # 秒精度允许相等。
    start_identity['id']=3
    queue=start_client.get('/m3/work-orders/dispatch?status=IN_REPAIR')
    assert queue.status_code==200 and order_id in [row['id'] for row in queue.json()['items']]
    assert get_repair_order(database,order_id)['started_at']==begun.json()['started_at']


def test_m3_r03_public_page_navigation_and_asset_order(start_client,start_app,monkeypatch):
    # 显式隔离外部登录页面，不依赖 G2 是否合入。
    monkeypatch.setattr(
        start_app.router,
        "routes",
        [
            route for route in start_app.router.routes
            if getattr(route, "path", None) != "/m2/login"
        ],
    )
    response=start_client.get('/m3/assigned')
    assert response.status_code==200 and 'data-login-available="false"' in response.text
    assert 'for="assigned-status"' in response.text
    assert response.text.index('/assets/m3/time.js')<response.text.index('/assets/m3/assigned.js')
    for path in ['/assets/m3/assigned.js','/assets/m3/time.js','/assets/m3/orders.css']:
        assert start_client.get(path).status_code==200
    for path in ['/m3/report','/m3/my-orders','/m3/orders/1','/m3/dispatch']:
        assert 'href="/m3/assigned"' in start_client.get(path).text
