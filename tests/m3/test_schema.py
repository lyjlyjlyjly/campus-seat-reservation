from itertools import product
import sqlite3

import pytest

from app.bootstrap import MigrationError, initialize_database
from app.common.db import connect_database
from app.m3.repository import create_repair_order, get_repair_order


def shared_rows(database):
    tables = ("app_user", "room", "room_application", "role", "permission",
              "user_role", "role_permission", "session")
    with connect_database(database, read_only=True) as connection:
        return {
            table: [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
            for table in tables
        }


def order_rows(database):
    with connect_database(database, read_only=True) as connection:
        return [tuple(row) for row in connection.execute("SELECT * FROM repair_order ORDER BY id")]


def test_m3_r01_empty_database_applies_real_shared_and_module_sql(tmp_path, migrations_dir):
    path = tmp_path / "empty.sqlite3"
    assert initialize_database(path, migrations_dir=migrations_dir) == 2
    with connect_database(path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM app_user").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM room").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM repair_order").fetchone()[0] == 0
        # V1 的授权配置是真实迁移产物，不是手写的简化依赖表。
        assert connection.execute("SELECT code FROM role WHERE code = 'repairer'").fetchone()[0] == "repairer"


def test_m3_r01_upgrade_and_repeat_preserve_shared_and_order_data(v1_database, migrations_dir):
    before = shared_rows(v1_database)
    assert initialize_database(v1_database, migrations_dir=migrations_dir) == 2
    order_id = create_repair_order(
        v1_database, reporter_id=1, room_id=10, fault_type="OTHER", description="升级后报修"
    )
    saved = get_repair_order(v1_database, order_id)
    for _ in range(2):
        assert initialize_database(v1_database, migrations_dir=migrations_dir) == 2
        assert shared_rows(v1_database) == before
        assert get_repair_order(v1_database, order_id) == saved
        assert len(order_rows(v1_database)) == 1


@pytest.mark.parametrize("field", ["reporter_id", "room_id", "assigned_to", "assigned_by"])
def test_m3_r01_all_user_and_room_foreign_keys_are_enforced(database, insert_order, field):
    values = {"status": "IN_REPAIR", "assigned_to": 2, "assigned_by": 1,
              "assigned_at": "2026-11-12T04:00:00Z", "started_at": "2026-11-12T05:00:00Z"}
    values[field] = 9999
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        with connect_database(database) as connection:
            insert_order(connection, **values)
    assert order_rows(database) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("fault_type", "UNKNOWN"), ("fault_type", ""), ("fault_type", None),
        ("description", ""), ("description", " \t\n\u3000"),
        ("description", "中" * 1001), ("description", "a\x00" + "中" * 1001),
        ("description", " 未规范化 "), ("description", b"bytes"), ("description", None),
        ("status", "DONE"), ("status", None),
        ("reporter_id", None), ("room_id", None),
        ("created_at", None), ("updated_at", None),
    ],
)
def test_m3_r01_invalid_insert_leaves_existing_order_unchanged(database, insert_order, field, value):
    with connect_database(database) as connection:
        insert_order(connection)
    before = order_rows(database)
    with pytest.raises(sqlite3.IntegrityError):
        with connect_database(database) as connection:
            insert_order(connection, **{field: value})
    assert order_rows(database) == before


@pytest.mark.parametrize("status", ["REPORTED", "ASSIGNED", "IN_REPAIR"])
@pytest.mark.parametrize("present", list(product((False, True), repeat=4)))
def test_m3_r02_r03_null_combinations_on_insert_and_update(database, insert_order, status, present):
    # 预期来自需求表；每个状态仅一个合法组合，实际执行 INSERT 和 UPDATE。
    allowed = {"REPORTED": (False, False, False, False),
               "ASSIGNED": (True, True, True, False),
               "IN_REPAIR": (True, True, True, True)}
    fields = ("assigned_to", "assigned_by", "assigned_at", "started_at")
    non_null = (2, 1, "2026-11-12T04:00:00Z", "2026-11-12T05:00:00Z")
    values = {field: value if exists else None for field, value, exists in zip(fields, non_null, present)}
    values["status"] = status
    with connect_database(database) as connection:
        original_id = insert_order(connection)
    before = order_rows(database)

    def insert():
        with connect_database(database) as connection:
            return insert_order(connection, **values)

    def update():
        with connect_database(database) as connection:
            connection.execute(
                """UPDATE repair_order SET status = ?, assigned_to = ?, assigned_by = ?,
                   assigned_at = ?, started_at = ? WHERE id = ?""",
                (status, *(values[field] for field in fields), original_id),
            )

    if present == allowed[status]:
        inserted_id = insert()
        update()
        for order_id in (original_id, inserted_id):
            saved = get_repair_order(database, order_id)
            assert {key: saved[key] for key in values} == values
    else:
        with pytest.raises(sqlite3.IntegrityError):
            insert()
        assert order_rows(database) == before
        with pytest.raises(sqlite3.IntegrityError):
            update()
        assert order_rows(database) == before


@pytest.mark.parametrize("status", [None, "UNKNOWN"])
def test_m3_r03_invalid_update_rolls_back_the_entire_transaction(database, insert_order, status):
    with connect_database(database) as connection:
        original_id = insert_order(connection)
    before = order_rows(database)
    with pytest.raises(sqlite3.IntegrityError):
        with connect_database(database) as connection:
            insert_order(connection, description="事务中的第二条工单")
            connection.execute("UPDATE repair_order SET description = ? WHERE id = ?", ("临时修改", original_id))
            connection.execute("UPDATE repair_order SET status = ? WHERE id = ?", (status, original_id))
    assert order_rows(database) == before


def test_m3_r01_failed_module_migration_keeps_v1_and_removes_partial_schema(v1_database, migrations_dir):
    before = shared_rows(v1_database)
    migration = migrations_dir / "V2__m3_test_only.sql"
    with migration.open("a", encoding="utf-8") as stream:
        stream.write("\nINSERT INTO intentionally_missing_table VALUES (1);\n")
    with pytest.raises(MigrationError):
        initialize_database(v1_database, migrations_dir=migrations_dir)
    with connect_database(v1_database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT name FROM sqlite_master WHERE name LIKE 'repair_order%'").fetchall() == []
    assert shared_rows(v1_database) == before
