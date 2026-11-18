-- M3 待整合 SQL 源；不是公共迁移版本，不自行管理事务或 user_version。
-- 正式接入步骤与暂定契约：docs/m3/INTEGRATION.md。
CREATE TABLE repair_order (
    id INTEGER PRIMARY KEY,
    reporter_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
    room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE RESTRICT,
    fault_type TEXT NOT NULL
        CHECK (fault_type IN ('ELECTRICAL', 'WATER', 'FURNITURE', 'OTHER')),
    description TEXT NOT NULL CHECK (
        typeof(description) = 'text'
        AND length(description) BETWEEN 1 AND 1000
        -- SQLite length(TEXT) 在 U+0000 处停止计数，拒绝 NUL 防止绕过上限。
        AND instr(description, char(0)) = 0
        -- 与 Python 3.10 str.strip() 的空白集合一致；数据库只接收规范化文本。
        AND description = trim(description, char(
            9, 10, 11, 12, 13, 28, 29, 30, 31, 32, 133, 160, 5760,
            8192, 8193, 8194, 8195, 8196, 8197, 8198, 8199, 8200,
            8201, 8202, 8232, 8233, 8239, 8287, 12288
        ))
    ),
    status TEXT NOT NULL DEFAULT 'REPORTED'
        CHECK (status IN ('REPORTED', 'ASSIGNED', 'IN_REPAIR')),
    assigned_to INTEGER REFERENCES app_user(id) ON DELETE RESTRICT,
    assigned_by INTEGER REFERENCES app_user(id) ON DELETE RESTRICT,
    assigned_at TEXT,
    started_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (
        (status = 'REPORTED'
         AND assigned_to IS NULL AND assigned_by IS NULL
         AND assigned_at IS NULL AND started_at IS NULL)
     OR (status = 'ASSIGNED'
         AND assigned_to IS NOT NULL AND assigned_by IS NOT NULL
         AND assigned_at IS NOT NULL AND started_at IS NULL)
     OR (status = 'IN_REPAIR'
         AND assigned_to IS NOT NULL AND assigned_by IS NOT NULL
         AND assigned_at IS NOT NULL AND started_at IS NOT NULL)
    )
);

CREATE INDEX repair_order_reporter_created ON repair_order (reporter_id, created_at, id);
CREATE INDEX repair_order_assignee_status ON repair_order (assigned_to, status, id);
CREATE INDEX repair_order_status_created ON repair_order (status, created_at, id);
