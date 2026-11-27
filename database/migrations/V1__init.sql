-- V1：G2 的身份、授权、会话、教室申请，以及 M2 依赖的最小房间主数据。
-- 本文件由 G3 汇总，G2 先提交自己需要的表；字段由三组确认后不再改写本版本，
-- 后续变化新增 V2、V3。时间均为 UTC 文本 YYYY-MM-DDTHH:MM:SSZ。
-- 固定角色与权限码属于授权契约，随 schema 一起写入，演示账号放在 seed.sql。

CREATE TABLE app_user (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'DISABLED')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE TABLE role (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE permission (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL
);

CREATE TABLE user_role (
  user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, role_id)
);

CREATE TABLE role_permission (
  role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  permission_id INTEGER NOT NULL REFERENCES permission(id) ON DELETE CASCADE,
  PRIMARY KEY (role_id, permission_id)
);

-- 只保存 sha256(令牌) 的十六进制，明文令牌不落库。
CREATE TABLE session (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT
);

CREATE INDEX session_user_id ON session (user_id);

-- D-R03 由 G3 扩展楼宇、位置和座位等字段；M2 只依赖这四列。
CREATE TABLE room (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  capacity INTEGER NOT NULL CHECK (capacity > 0),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE room_application (
  id INTEGER PRIMARY KEY,
  applicant_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE RESTRICT,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (length(purpose) BETWEEN 1 AND 200),
  attendee_count INTEGER NOT NULL CHECK (attendee_count > 0),
  status TEXT NOT NULL DEFAULT 'PENDING_L1'
    CHECK (status IN ('PENDING_L1', 'PENDING_L2', 'APPROVED', 'REJECTED', 'REVOKED', 'CANCELLED')),
  decided_by INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
  decision_note TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  CHECK (end_at > start_at)
);

CREATE INDEX room_application_room_time ON room_application (room_id, start_at, end_at);

CREATE INDEX room_application_applicant ON room_application (applicant_id);

INSERT INTO role (code, name) VALUES
  ('student', '学生'),
  ('teacher', '教师'),
  ('org_leader', '学生组织负责人'),
  ('approver', '教室审批员'),
  ('repairer', '维修人员'),
  ('admin', '系统管理员');

INSERT INTO permission (code, description) VALUES
  ('room:apply', '提交整教室借用申请'),
  ('room:approve', '审批教室借用申请');

-- 学生不授予 room:apply，用于演示无权限拒绝路径。
INSERT INTO role_permission (role_id, permission_id)
SELECT r.id, p.id
FROM role AS r
JOIN permission AS p
WHERE (r.code IN ('teacher', 'org_leader') AND p.code = 'room:apply')
   OR (r.code IN ('approver', 'admin') AND p.code = 'room:approve')
