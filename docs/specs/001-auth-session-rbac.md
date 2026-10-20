# SPEC-001：登录、会话与固定角色 RBAC

日期：2026-10-20。状态：方案已由用户确认，按模块实施，交付后待人工验收。

需求：[D-R01](../requirements.md)（登录与会话，必做）、D-R02 的固定角色部分（管理页面延期）、[M2-R01](../requirements.md) 的权限判定前置。

## 背景与授权

用户（G2 负责人）在 2026-10-20 明确两项口径：`room:apply` 授予 `teacher` 与学生组织负责人 `org_leader`，不授予 `student`；页面采用静态 HTML + 原生 JS 调用 JSON 接口。并在同日要求把工作放回本仓库、按模块分步提交。

本任务只完成本轮 [Review 1 计划](../Review1计划.md) 中 D-R01 与 D-R02 的固定角色部分。用户对具体任务的指令是该范围的实施授权，不代表三组已完成公共字段会议或 ADR 表决；D-R05 审计、动态角色管理、密码找回与注册仍按计划延期。

## 范围

- `database/migrations/V1__init.sql` 中 G2 的六张表：`app_user`、`role`、`permission`、`user_role`、`role_permission`、`session`（DDL 见下）。
- 口令派生：PBKDF2-HMAC-SHA256、200 000 次迭代、16 字节随机盐，格式 `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`；配套 `python -m app.d.auth.password` 生成与校验命令，供种子和排查使用。
- 会话：`secrets.token_urlsafe(32)` 令牌，数据库只存 `sha256(令牌)` 的十六进制；Cookie 名 `campus_session`，`HttpOnly`、`SameSite=Lax`、`Path=/`、默认 30 分钟滑动过期。
- 接口：`POST /m2/auth/login`、`POST /m2/auth/logout`、`GET /m2/auth/me`；依赖 `require_user` 与 `require_permission(code)` 供 M2/M3 复用。
- 固定角色与权限种子，以及虚构演示账号；`tests/d/` 下按需求 ID 命名的行为测试。

## 不做项

动态角色/权限管理页面（D-R02 延期部分）、密码找回与改密、自助注册、JWT 或外部身份提供方、多设备会话列表、登录限流与审计（D-R05 延期）。不提供硬编码“已登录”依赖。

## 约束

- 零新增依赖：只用标准库 `sqlite3`、`hashlib`、`secrets`、`hmac`；不引入 passlib、bcrypt、python-jose 或 ORM（[ADR-002](../../.agents/notes/proposed/architecture/2026-10-20-adr-002-minimal-stack.md)）。
- 口令与令牌不得进入数据库明文、日志、异常消息或测试快照。
- 认证由 G2 拥有，挂在既有 `/m2` 挂载点下的 `/m2/auth/*`，不新增第四个业务挂载点；`app/main.py` 只增加一行 `include_router`。
- 时间一律存 UTC 文本 `YYYY-MM-DDTHH:MM:SSZ`；会话过期比较在 SQL 内用 `strftime('%Y-%m-%dT%H:%M:%SZ','now')` 完成，避免宿主机时区影响。
- 数据库文件与凭据不提交；演示账号口令为虚构值，写入种子并标注“仅演示”。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A 服务端 `session` 表 + HttpOnly Cookie，仅存令牌哈希 | 与 D-R01 原文“服务端只存令牌哈希”一致；退出立即失效；零依赖；便于撤销 | 每次请求多一次主键查询；需要自己写过期清理 | 采用 |
| B JWT 或签名 Cookie | 无状态、不查表 | 需新依赖；退出无法真正失效（只能靠短 TTL 或黑名单），与 D-R01 冲突 | 不采用 |
| C 使用 fastapi-users | 成熟的会话与校验行为 | 强依 SQLAlchemy，违反“不引入 ORM”；需新依赖 | 不采用 |

参考项目只读取结构与约定，未复制实现：[fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)（MIT）可用于借鉴依赖注入鉴权组织与 pytest 写法，但其 `security.py` 是 JWT + pwdlib(argon2)，与本需求冲突；[fastapi-users](https://github.com/fastapi-users/fastapi-users)（MIT）模型清晰但绑定 SQLAlchemy；[fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) 无 LICENSE（保留所有权利），只作阅读，不复制代码。

## 预计改动

`database/migrations/V1__init.sql`（G3 汇总的公共文件，本任务先提交 G2 片段并在提交信息说明需 G3/G1 评审）、`database/seed.sql`（演示账号，幂等）、`app/d/auth/password.py`、`session.py`、`dependencies.py`、`router.py`、`app/main.py`、`tests/d/`、本文件。

## 数据契约（供三组确认）

```sql
CREATE TABLE app_user (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','DISABLED')),
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE TABLE role (
  id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL
);
CREATE TABLE permission (
  id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, description TEXT NOT NULL
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
CREATE TABLE session (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT
);
CREATE INDEX session_user_id ON session (user_id);
```

固定角色：`student`、`teacher`、`org_leader`、`approver`、`repairer`、`admin`。G2 声明的权限码：`room:apply` → `teacher`、`org_leader`；`room:approve` → `approver`、`admin`。`student` 不授予 `room:apply`，用于演示拒绝路径。其他组只追加自己的权限码，不改动这些授权。

## 验收标准

- Given 正确用户名与口令，When `POST /m2/auth/login`，Then `200`，`Set-Cookie` 含 `HttpOnly`、`SameSite=Lax`、`Path=/`；库中 `session` 行的 `token_hash` 为 64 位十六进制且不等于响应中携带的令牌。
- Given 错误用户名、错误口令或 `DISABLED` 账号，When 登录，Then `401`，不创建会话，响应不区分“用户不存在”与“口令错误”。
- Given 有效 Cookie，When `GET /m2/auth/me`，Then `200` 返回 `username`、`display_name`、`roles`、`permissions`。
- Given 已退出，When 用旧 Cookie 请求 `/me`，Then `401`，且该会话 `revoked_at` 非空。
- Given `expires_at` 早于当前 UTC 的会话，When 请求 `/me`，Then `401`。
- Given `teacher` 或 `org_leader`，When 校验 `room:apply`，Then 放行；Given `student`，Then `403`。
- Given 无 Cookie 访问受保护接口，Then `401`；`403` 只用于已登录但无权限。
- Given 同一口令，When 派生两次，Then 盐与散列不同且都能校验通过；错误口令校验为 `False`。
- Given 重复执行 `python -m app.bootstrap --seed`，Then 演示账号与角色权限不重复（`INSERT OR IGNORE` 或 `ON CONFLICT`）。

## 验证计划

`python -m pytest tests/d -q`；`python scripts/ci.py`；本机 `uvicorn` 启动后用 `curl` 走一遍登录、`/me`、退出、旧 Cookie 复验，并把实际命令与结果补到本节下方。
