"""显式初始化 SQLite；迁移和演示种子分别执行事务。"""

import argparse
import re
import sqlite3
from pathlib import Path
from typing import Optional

from app.common.config import PROJECT_ROOT, get_settings
from app.common.db import connect_database


MIGRATIONS_DIR = PROJECT_ROOT / "database" / "migrations"
SEED_PATH = PROJECT_ROOT / "database" / "seed.sql"
MIGRATION_NAME = re.compile(r"V([1-9][0-9]*)__([A-Za-z0-9][A-Za-z0-9_-]*)\.sql")


class MigrationError(RuntimeError):
    """迁移文件或数据库版本不符合仓库约定。"""


def find_migrations(directory: Path) -> list[tuple[int, Path]]:
    """要求完整迁移历史从 V1 连续编号，拒绝拼错的 SQL 文件名。"""
    if not directory.is_dir():
        raise MigrationError(f"迁移目录不存在：{directory}")
    migrations = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() != ".sql":
            continue
        match = MIGRATION_NAME.fullmatch(path.name)
        if match is None:
            raise MigrationError(f"迁移文件名须为 Vn__name.sql：{path.name}")
        migrations.append((int(match.group(1)), path))
    migrations.sort(key=lambda item: item[0])
    if [version for version, _ in migrations] != list(range(1, len(migrations) + 1)):
        raise MigrationError("迁移必须从 V1 连续编号，不能缺号或重复版本")
    return migrations


def _authorize_script(action, argument, _value, _database, _source):
    # 事务与版本由初始化器管理，脚本不得自行提交或修改版本绕过回滚。
    if action in (sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_SAVEPOINT):
        return sqlite3.SQLITE_DENY
    if action == sqlite3.SQLITE_PRAGMA and (argument or "").lower() in (
        "user_version",
        "foreign_keys",
    ):
        return sqlite3.SQLITE_DENY
    return sqlite3.SQLITE_OK


def _execute_statements(connection: sqlite3.Connection, sql: str) -> None:
    # executescript 会隐式提交现有事务；使用 SQLite 自己的语句完整性判断
    # 逐条执行，保留整个迁移的事务，也支持字符串中的分号和 CREATE TRIGGER。
    pending = []
    for character in sql:
        pending.append(character)
        if character == ";" and sqlite3.complete_statement("".join(pending)):
            connection.execute("".join(pending))
            pending.clear()
    remaining = "".join(pending).strip()
    if remaining:
        connection.execute(remaining)


def _apply_script(
    connection: sqlite3.Connection, path: Path, version: Optional[int] = None
) -> None:
    sql = path.read_text(encoding="utf-8-sig")
    try:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.set_authorizer(_authorize_script)
            try:
                _execute_statements(connection, sql)
            finally:
                # Python 3.10 无法用 None 取消回调；恢复为放行回调后提交/回滚。
                connection.set_authorizer(lambda *_: sqlite3.SQLITE_OK)
            if version is not None:
                # PRAGMA 不支持参数绑定；version 只来自已校验的连续整数编号。
                connection.execute(f"PRAGMA user_version = {version}")
    except sqlite3.Error as error:
        raise MigrationError(f"{path.name} 执行失败，当前事务已回滚：{error}") from error


def initialize_database(
    database_path: Path,
    *,
    migrations_dir: Path = MIGRATIONS_DIR,
    seed_path: Optional[Path] = None,
) -> int:
    """只执行尚未应用的迁移；传入 seed_path 才执行幂等种子。"""
    migrations = find_migrations(migrations_dir)
    database_path = database_path.expanduser().resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_database(database_path, create=True) as connection:
        current_version = connection.execute("PRAGMA user_version").fetchone()[0]
        if current_version < 0 or current_version > len(migrations):
            raise MigrationError(
                f"数据库版本 {current_version} 不在当前迁移范围 0–{len(migrations)} 内"
            )
        if not migrations:
            # 为骨架的版本 0 写入有效 SQLite 文件头，不定义任何业务表。
            connection.execute("PRAGMA user_version = 0")
        for version, path in migrations:
            if version > current_version:
                _apply_script(connection, path, version)
                current_version = version
        if seed_path is not None:
            _apply_script(connection, seed_path)
    return current_version


def main() -> int:
    parser = argparse.ArgumentParser(description="初始化校园资源服务平台 SQLite 数据库")
    parser.add_argument("--database", type=Path, help="数据库文件；默认读取 CAMPUS_DATABASE_PATH")
    parser.add_argument("--seed", action="store_true", help="迁移后显式执行演示种子")
    arguments = parser.parse_args()
    database_path = arguments.database or get_settings().database_path
    try:
        version = initialize_database(
            database_path, seed_path=SEED_PATH if arguments.seed else None
        )
    except (MigrationError, OSError, sqlite3.Error, UnicodeError) as error:
        parser.exit(1, f"初始化失败：{error}\n")
    seed_status = "已执行" if arguments.seed else "未执行"
    print(
        f"SQLite 已初始化：{database_path.expanduser().resolve()}"
        f"（schema_version={version}，seed={seed_status}）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
