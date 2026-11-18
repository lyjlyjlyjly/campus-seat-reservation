"""仅在临时数据库使用原始共享 V1；测试版本号不是正式迁移编号。"""

import hashlib
from pathlib import Path
import shutil

import pytest

from app.bootstrap import initialize_database
from app.common.config import PROJECT_ROOT
from app.common.db import connect_database


V1_SNAPSHOT = Path(__file__).parent / "fixtures" / "V1__init.sql"
V1_SHA256 = "a23f6dbaed498d2bfda0d5942306a6d3535b8bf8f724ed0401474ac57259d319"
M3_SQL = PROJECT_ROOT / "app" / "m3" / "sql" / "repair_order.sql"


@pytest.fixture
def migrations_dir(tmp_path):
    assert hashlib.sha256(V1_SNAPSHOT.read_bytes()).hexdigest() == V1_SHA256
    directory = tmp_path / "migrations"
    directory.mkdir()
    shutil.copyfile(V1_SNAPSHOT, directory / "V1__init.sql")
    shutil.copyfile(M3_SQL, directory / "V2__m3_test_only.sql")
    return directory


@pytest.fixture
def v1_database(tmp_path):
    directory = tmp_path / "v1_only"
    directory.mkdir()
    shutil.copyfile(V1_SNAPSHOT, directory / "V1__init.sql")
    database = tmp_path / "campus.sqlite3"
    assert initialize_database(database, migrations_dir=directory) == 1
    with connect_database(database) as connection:
        # 虚构临时数据，不是可登录账号，不写共享演示种子。
        connection.executemany(
            """INSERT INTO app_user (id, username, password_hash, display_name)
               VALUES (?, ?, ?, ?)""",
            [(1, "m3_test_reporter", "not-a-login-fixture", "测试报修人"),
             (2, "m3_test_operator", "not-a-login-fixture", "测试操作人")],
        )
        connection.executemany(
            "INSERT INTO room (id, name, capacity, is_active) VALUES (?, ?, ?, ?)",
            [(10, "测试教室", 40, 1), (20, "测试停借教室", 20, 0)],
        )
        connection.execute(
            """INSERT INTO room_application (
                id, applicant_id, room_id, start_at, end_at, purpose, attendee_count
            ) VALUES (50, 1, 10, '2026-11-12T01:00:00Z', '2026-11-12T02:00:00Z',
                      '测试既有业务保留', 8)"""
        )
    return database


@pytest.fixture
def database(v1_database, migrations_dir):
    assert initialize_database(v1_database, migrations_dir=migrations_dir) == 2
    return v1_database


@pytest.fixture
def insert_order():
    def insert(connection, **overrides):
        values = {
            "reporter_id": 1, "room_id": 10, "fault_type": "ELECTRICAL",
            "description": "灯管闪烁", "status": "REPORTED",
            "assigned_to": None, "assigned_by": None,
            "assigned_at": None, "started_at": None,
            "created_at": "2026-11-12T03:00:00Z", "updated_at": "2026-11-12T03:00:00Z",
        }
        assert set(overrides) <= set(values)
        values.update(overrides)
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        return connection.execute(
            f"INSERT INTO repair_order ({columns}) VALUES ({placeholders})",
            tuple(values.values()),
        ).lastrowid
    return insert
