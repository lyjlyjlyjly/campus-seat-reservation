import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from app.bootstrap import MigrationError, initialize_database
from app.common.config import PROJECT_ROOT
from app.common.db import connect_database


def test_migrations_and_seed_can_be_replayed_without_duplicate_data(
    tmp_path: Path, empty_migrations: Path
):
    database = tmp_path / "data" / "campus.sqlite3"
    # 故意先写 V2，验证执行顺序取自版本号；V2 依赖 V1 的真实表。
    (empty_migrations / "V2__label.sql").write_text(
        "ALTER TABLE sample_items ADD COLUMN label TEXT;", encoding="utf-8"
    )
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE sample_items (code TEXT PRIMARY KEY);", encoding="utf-8"
    )
    seed = tmp_path / "seed.sql"
    seed.write_text(
        "INSERT OR IGNORE INTO sample_items (code, label) VALUES ('one', '示例');",
        encoding="utf-8",
    )

    initialize_database(database, migrations_dir=empty_migrations, seed_path=seed)
    initialize_database(database, migrations_dir=empty_migrations, seed_path=seed)

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        rows = connection.execute("SELECT code, label FROM sample_items").fetchall()
        assert [tuple(row) for row in rows] == [("one", "示例")]


def test_seed_is_explicit_and_does_not_run_during_default_initialization(
    tmp_path: Path, empty_migrations: Path
):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE sample_items (code TEXT PRIMARY KEY);", encoding="utf-8"
    )
    seed = tmp_path / "seed.sql"
    seed.write_text("INSERT OR IGNORE INTO sample_items VALUES ('one');", encoding="utf-8")

    initialize_database(database, migrations_dir=empty_migrations)
    with connect_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sample_items").fetchone()[0] == 0

    initialize_database(database, migrations_dir=empty_migrations, seed_path=seed)
    with connect_database(database) as connection:
        assert connection.execute("SELECT code FROM sample_items").fetchone()[0] == "one"


def test_failed_first_migration_rolls_back_tables_and_version(tmp_path: Path, empty_migrations: Path):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE partial_table (id INTEGER); INSERT INTO absent_table VALUES (1);",
        encoding="utf-8",
    )

    with pytest.raises(MigrationError, match="V1__init.sql"):
        initialize_database(database, migrations_dir=empty_migrations)

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = ?", ("partial_table",)
        ).fetchone() is None


def test_failed_later_migration_preserves_previous_version(tmp_path: Path, empty_migrations: Path):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE stable_table (id INTEGER PRIMARY KEY);", encoding="utf-8"
    )
    (empty_migrations / "V2__broken.sql").write_text(
        "CREATE TABLE partial_table (id INTEGER);\n"
        "INSERT INTO stable_table VALUES (1);\n"
        "INSERT INTO absent_table VALUES (1);\n",
        encoding="utf-8",
    )

    with pytest.raises(MigrationError, match="V2__broken.sql"):
        initialize_database(database, migrations_dir=empty_migrations)

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM stable_table").fetchone()[0] == 0
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = ?", ("partial_table",)
        ).fetchone() is None


def test_failed_seed_rolls_back_rows_and_keeps_completed_migrations(
    tmp_path: Path, empty_migrations: Path
):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE sample_items (code TEXT PRIMARY KEY);", encoding="utf-8"
    )
    seed = tmp_path / "seed.sql"
    seed.write_text(
        "INSERT INTO sample_items VALUES ('one'); INSERT INTO absent_table VALUES (1);",
        encoding="utf-8",
    )

    with pytest.raises(MigrationError, match="seed.sql"):
        initialize_database(database, migrations_dir=empty_migrations, seed_path=seed)

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM sample_items").fetchone()[0] == 0


@pytest.mark.parametrize("forbidden_sql", ["COMMIT;", "PRAGMA user_version = 99;"])
def test_migration_cannot_bypass_transaction_or_version_management(
    tmp_path: Path, empty_migrations: Path, forbidden_sql: str
):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE partial_table (id INTEGER); " + forbidden_sql, encoding="utf-8"
    )

    with pytest.raises(MigrationError):
        initialize_database(database, migrations_dir=empty_migrations)

    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE name = ?", ("partial_table",)
        ).fetchone() is None


def test_sql_with_trigger_and_semicolon_in_string_runs_in_one_transaction(
    tmp_path: Path, empty_migrations: Path
):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE sample_items (code TEXT PRIMARY KEY);\n"
        "CREATE TABLE recorded_items (code TEXT);\n"
        "CREATE TRIGGER record_item AFTER INSERT ON sample_items BEGIN\n"
        "  INSERT INTO recorded_items VALUES (NEW.code);\n"
        "END;\n"
        "INSERT INTO sample_items VALUES ('one;two'); -- 注释里也有分号;\n",
        encoding="utf-8",
    )
    initialize_database(database, migrations_dir=empty_migrations)
    with connect_database(database) as connection:
        assert connection.execute("SELECT code FROM recorded_items").fetchone()[0] == "one;two"


@pytest.mark.parametrize(
    "names",
    [
        ["V2__missing_first.sql"],
        ["V1__init.sql", "V3__gap.sql"],
        ["V1__init.sql", "V1__duplicate.sql"],
        ["v1__lowercase.sql"],
        ["V01__leading_zero.sql"],
        ["init.sql"],
    ],
)
def test_invalid_migration_history_fails_before_creating_database(
    tmp_path: Path, empty_migrations: Path, names: list[str]
):
    database = tmp_path / "campus.sqlite3"
    for name in names:
        (empty_migrations / name).write_text("SELECT 1;", encoding="utf-8")
    with pytest.raises(MigrationError):
        initialize_database(database, migrations_dir=empty_migrations)
    assert not database.exists()


def test_database_newer_than_available_migrations_is_not_downgraded(
    tmp_path: Path, empty_migrations: Path
):
    database = tmp_path / "campus.sqlite3"
    with connect_database(database, create=True) as connection:
        connection.execute("PRAGMA user_version = 9")
    with pytest.raises(MigrationError, match="9"):
        initialize_database(database, migrations_dir=empty_migrations)
    with connect_database(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 9


def test_connections_enforce_foreign_keys_commit_and_close(tmp_path: Path, empty_migrations: Path):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE parent_rows (id INTEGER PRIMARY KEY);\n"
        "CREATE TABLE child_rows (parent_id INTEGER REFERENCES parent_rows(id));",
        encoding="utf-8",
    )
    initialize_database(database, migrations_dir=empty_migrations)
    with connect_database(database) as connection:
        connection.execute("INSERT INTO parent_rows VALUES (?)", (1,))
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")

    # 每次新连接都应启用外键，且能看到上一个连接提交的数据。
    for _ in range(2):
        with connect_database(database) as next_connection:
            assert next_connection.execute("SELECT id FROM parent_rows").fetchone()[0] == 1
            with pytest.raises(sqlite3.IntegrityError):
                next_connection.execute("INSERT INTO child_rows VALUES (?)", (999,))


def test_connection_rolls_back_writes_when_the_calling_operation_fails(
    tmp_path: Path, empty_migrations: Path
):
    database = tmp_path / "campus.sqlite3"
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE sample_items (code TEXT PRIMARY KEY);", encoding="utf-8"
    )
    initialize_database(database, migrations_dir=empty_migrations)
    with pytest.raises(RuntimeError, match="operation failed"):
        with connect_database(database) as connection:
            connection.execute("INSERT INTO sample_items VALUES (?)", ("one",))
            raise RuntimeError("operation failed")
    with connect_database(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sample_items").fetchone()[0] == 0


def test_normal_connection_requires_explicit_initialization(tmp_path: Path):
    database = tmp_path / "missing.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        with connect_database(database):
            pass
    assert not database.exists()


def test_bootstrap_cli_accepts_database_path_and_explicit_seed(tmp_path: Path):
    database = tmp_path / "cli" / "campus.sqlite3"
    for extra_arguments in ([], ["--seed"]):
        result = subprocess.run(
            [sys.executable, "-m", "app.bootstrap", "--database", str(database), *extra_arguments],
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        assert result.returncode == 0, result.stderr
        with connect_database(database) as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            assert f"schema_version={version}" in result.stdout
        assert database.stat().st_size > 0
    assert "seed=已执行" in result.stdout
