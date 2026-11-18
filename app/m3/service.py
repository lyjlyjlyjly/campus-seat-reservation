"""房间报修事务：共享数据只读，业务写入仅涉及 repair_order。"""

from pathlib import Path
import sqlite3

from app.common.db import connect_database
from app.m3.errors import ReportError
from app.m3.models import AssignmentCreate, ORDER_STATES, ReportCreate, parse_order_id
from app.m3.repository import (
    assign_reported_order, eligible_repairers, find_visible_order, insert_repair_order,
    list_dispatch_orders, list_owned_orders,
)


def _database_ready(database_path: Path) -> None:
    if not database_path.is_file():
        raise ReportError(503, "storage_unavailable", "报修数据库尚未准备完成，当前暂不可提交")


def _schema_ready(connection: sqlite3.Connection, *, assignment: bool = False) -> None:
    required = {"app_user", "user_role", "role_permission", "permission", "room", "repair_order"}
    if assignment:
        required.add("role")
    tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    if not required <= tables:
        raise ReportError(503, "schema_unavailable", "报修所需迁移尚未接入，当前暂不可提交")


def _require_active_user(connection: sqlite3.Connection, user_id: int) -> None:
    row = connection.execute("SELECT status FROM app_user WHERE id = ?", (user_id,)).fetchone()
    if row is None or row["status"] != "ACTIVE":
        raise ReportError(401, "unauthenticated", "账号已失效或被禁用，请重新登录")


def _permissions_for(connection: sqlite3.Connection, user_id: int) -> set[str]:
    return {row["code"] for row in connection.execute(
        """SELECT DISTINCT p.code FROM user_role AS ur
           JOIN role_permission AS rp ON rp.role_id = ur.role_id
           JOIN permission AS p ON p.id = rp.permission_id
           WHERE ur.user_id = ?""", (user_id,),
    )}


def _require_permission(permissions: set[str], code: str) -> None:
    if code not in permissions:
        raise ReportError(403, "forbidden", f"当前账号没有 {code} 权限")


def _require_reporter(connection: sqlite3.Connection, reporter_id: int) -> None:
    # 保留创建/房间候选的调用入口；读取工单不复用 repair:report 要求。
    _require_active_user(connection, reporter_id)
    _require_permission(_permissions_for(connection, reporter_id), "repair:report")


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


def list_my_orders(database_path: Path, user_id: int) -> dict:
    _database_ready(database_path)
    with connect_database(database_path, read_only=True) as connection:
        connection.execute("BEGIN")
        _schema_ready(connection)
        _require_active_user(connection, user_id)
        _require_permission(_permissions_for(connection, user_id), "repair:read_own")
        items = list_owned_orders(connection, user_id)
        return {"items": items, "total": len(items)}


def read_order(database_path: Path, user_id: int, raw_order_id: str) -> dict:
    _database_ready(database_path)
    with connect_database(database_path, read_only=True) as connection:
        connection.execute("BEGIN")
        _schema_ready(connection)
        _require_active_user(connection, user_id)
        permissions = _permissions_for(connection, user_id)
        if not permissions.intersection({"repair:read_own", "repair:read_assigned", "repair:assign"}):
            raise ReportError(403, "forbidden", "当前账号没有工单查看权限")
        # 先验证功能权限，再解析/查询目标；不按目标存在性改变 403。
        order_id = parse_order_id(raw_order_id)
        item = None if order_id is None else find_visible_order(
            connection, order_id, user_id=user_id,
            allow_management="repair:assign" in permissions,
            allow_own="repair:read_own" in permissions,
            allow_assigned="repair:read_assigned" in permissions,
        )
        if item is None:
            raise ReportError(404, "not_found", "工单不存在或不可访问")
        return item


def _require_dispatcher(connection: sqlite3.Connection, user_id: int) -> None:
    _require_active_user(connection, user_id)
    _require_permission(_permissions_for(connection, user_id), "repair:assign")


def dispatch_queue(database_path: Path, user_id: int, status: str) -> dict:
    _database_ready(database_path)
    with connect_database(database_path, read_only=True) as connection:
        connection.execute("BEGIN")
        _schema_ready(connection, assignment=True)
        _require_dispatcher(connection, user_id)
        if status not in ORDER_STATES:
            raise ReportError(422, "invalid_request", "status 仅允许 REPORTED、ASSIGNED 或 IN_REPAIR")
        items = list_dispatch_orders(connection, status)
        return {"items": items, "total": len(items)}


def list_repairers(database_path: Path, user_id: int) -> dict:
    _database_ready(database_path)
    with connect_database(database_path, read_only=True) as connection:
        connection.execute("BEGIN")
        _schema_ready(connection, assignment=True)
        _require_dispatcher(connection, user_id)
        return {"items": eligible_repairers(connection)}


def assign_order(database_path: Path, user_id: int, raw_order_id: str, payload: AssignmentCreate) -> dict:
    _database_ready(database_path)
    with connect_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        _schema_ready(connection, assignment=True)
        _require_dispatcher(connection, user_id)  # 功能权限先于目标存在性及状态。
        order_id = parse_order_id(raw_order_id)
        item = None if order_id is None else find_visible_order(
            connection, order_id, user_id=user_id,
            allow_management=True, allow_own=False, allow_assigned=False,
        )
        if item is None:
            raise ReportError(404, "not_found", "工单不存在或不可访问")
        # 后续在此接入通用状态规则；不能替代事务内重查、条件更新和 rowcount。
        if item["status"] != "REPORTED":
            raise ReportError(409, "conflict", "工单状态已变化，仅已报修工单可以派单，请刷新详情")
        if not eligible_repairers(connection, payload.assigned_to):
            raise ReportError(422, "invalid_repairer", "所选人员不具备当前维修资格，请重新加载候选")
        if assign_reported_order(connection, order_id, payload.assigned_to, user_id) != 1:
            raise ReportError(409, "conflict", "工单状态已变化，本次未派单，请刷新详情")
        updated = find_visible_order(
            connection, order_id, user_id=user_id,
            allow_management=True, allow_own=False, allow_assigned=False,
        )
        if updated is None:
            raise RuntimeError("派单后无法读取工单")
    return updated  # COMMIT 完成后返回；提交错误由上下文回滚并抛出。
