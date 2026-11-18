"""房间报修事务：共享数据只读，业务写入仅涉及 repair_order。"""

from pathlib import Path
import sqlite3

from app.common.db import connect_database
from app.m3.errors import ReportError
from app.m3.models import ReportCreate
from app.m3.repository import insert_repair_order


def _database_ready(database_path: Path) -> None:
    if not database_path.is_file():
        raise ReportError(503, "storage_unavailable", "报修数据库尚未准备完成，当前暂不可提交")


def _schema_ready(connection: sqlite3.Connection) -> None:
    required = {"app_user", "user_role", "role_permission", "permission", "room", "repair_order"}
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not required <= tables:
        raise ReportError(503, "schema_unavailable", "报修所需迁移尚未接入，当前暂不可提交")


def _require_reporter(connection: sqlite3.Connection, reporter_id: int) -> None:
    row = connection.execute("SELECT status FROM app_user WHERE id = ?", (reporter_id,)).fetchone()
    if row is None or row["status"] != "ACTIVE":
        raise ReportError(401, "unauthenticated", "账号已失效或被禁用，请重新登录")
    permission = connection.execute(
        """SELECT 1 FROM user_role AS ur
           JOIN role_permission AS rp ON rp.role_id = ur.role_id
           JOIN permission AS p ON p.id = rp.permission_id
           WHERE ur.user_id = ? AND p.code = 'repair:report' LIMIT 1""",
        (reporter_id,),
    ).fetchone()
    if permission is None:
        raise ReportError(403, "forbidden", "当前账号没有 repair:report 报修权限")


def reportable_rooms(connection: sqlite3.Connection, room_id: int | None = None) -> list[dict]:
    """列表与创建的唯一位置规则：存在即允许，包括 is_active=0 的停借资产。"""
    if room_id is not None and room_id > 9223372036854775807:
        return []  # SQLite INTEGER 主键范围之外一定不存在，避免绑定溢出成为 500。
    sql = "SELECT id, name, is_active FROM room"
    parameters = ()
    if room_id is not None:
        sql += " WHERE id = ?"
        parameters = (room_id,)
    return [dict(row) for row in connection.execute(sql + " ORDER BY name, id", parameters)]


def list_rooms(database_path: Path, reporter_id: int) -> list[dict]:
    _database_ready(database_path)
    with connect_database(database_path, read_only=True) as connection:
        connection.execute("BEGIN")
        _schema_ready(connection)
        _require_reporter(connection, reporter_id)
        return reportable_rooms(connection)


def create_report(database_path: Path, reporter_id: int, payload: ReportCreate) -> dict:
    _database_ready(database_path)
    with connect_database(database_path) as connection:
        # 在身份/权限读取之前取得写事务；其他写入者不能在检查与插入之间撤权。
        connection.execute("BEGIN IMMEDIATE")
        _schema_ready(connection)
        _require_reporter(connection, reporter_id)
        if not reportable_rooms(connection, payload.room_id):
            raise ReportError(422, "unknown_room", "所选房间不存在或当前不可报修，请重新加载房间")
        order_id = insert_repair_order(
            connection, reporter_id=reporter_id, room_id=payload.room_id,
            fault_type=payload.fault_type, description=payload.description,
        )
        item = dict(connection.execute(
            "SELECT id, status, created_at FROM repair_order WHERE id = ?", (order_id,)
        ).fetchone())
    # 上面的上下文已成功 COMMIT；失败包括提交阶段的锁冲突会回滚并抛出。
    return item
