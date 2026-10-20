"""每次使用独立的 SQLite 连接，默认要求数据库已存在。"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


@contextmanager
def connect_database(
    database_path: Path,
    *,
    create: bool = False,
    read_only: bool = False,
) -> Iterator[sqlite3.Connection]:
    """正常退出时提交，异常时回滚；退出后总是关闭连接。

    只有显式初始化入口使用 create=True。普通请求不会意外建空数据库。
    """
    if create and read_only:
        raise ValueError("创建数据库与只读连接不能同时启用")
    mode = "ro" if read_only else "rwc" if create else "rw"
    uri = database_path.expanduser().resolve().as_uri() + "?mode=" + mode
    connection = sqlite3.connect(uri, uri=True, timeout=5.0)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            yield connection
    finally:
        connection.close()
