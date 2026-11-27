# G2-LOCAL-001：登录、会话与固定角色 RBAC

原任务日期：2026-10-20。原分支记录：方案已由用户确认，按模块实施，交付后待人工验收。

2026-11-27 文档整合草稿，来源为 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042`。原编号为 SPEC-001，整合时改用组内任务编号。以下实现说明已按该分支代码校正：身份依赖为 `current_user(request)`，会话自登录起固定 30 分钟到期。2026-10-21 的实验记录保留原日期与命令；本次未重新执行这些实验。

需求：[D-R01](../requirements.md)（登录与会话，必做）、D-R02 的固定角色部分（管理页面延期）、[M2-R01](../requirements.md) 的权限判定前置。认证取舍见 [ADR-005](../../.agents/notes/proposed/architecture/2026-10-21-adr-005-session-authentication.md)。

## 背景与原任务依据

原分支记录：用户（G2 负责人）在 2026-10-20 明确两项口径：`room:apply` 授予 `teacher` 与学生组织负责人 `org_leader`，不授予 `student`；页面采用静态 HTML + 原生 JS 调用 JSON 接口。并在同日要求把工作放回本仓库、按模块分步提交。

本任务只完成 [需求基线](../requirements.md) 中 D-R01 与 D-R02 的固定角色部分。原任务以 Review 1 计划为输入，该计划文件现已删除，当前范围由需求基线维护。原任务的实施记录不代表三组已完成公共字段会议或 ADR 表决；D-R05 审计、动态角色管理、密码找回与注册仍按计划延期。

## 范围

- `database/migrations/V1__init.sql` 中 G2 依赖的六张表：`app_user`、`role`、`permission`、`user_role`、`role_permission`、`session`（DDL 见下）。
- 口令派生：PBKDF2-HMAC-SHA256、200 000 次迭代、16 字节随机盐，格式 `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`；配套 `python -m app.d.auth.password` 生成与校验命令，供种子和排查使用。
- 会话：`secrets.token_urlsafe(32)` 令牌，数据库只存 `sha256(令牌)` 的十六进制；Cookie 名 `campus_session`，`HttpOnly`、`SameSite=Lax`、`Path=/`。`SESSION_TTL_MINUTES = 30`，有效期从创建会话时计算，请求期间不续期。
- 接口：`POST /m2/auth/login`、`POST /m2/auth/logout`、`GET /m2/auth/me`；依赖 `current_user(request)` 与 `require_permission(code)` 供三组复用。
- 固定角色与权限种子，以及虚构演示账号；原分支 `tests/d/test_auth_*.py` 在整合中归入 G2 的 `tests/d/auth/`。

## 不做项

动态角色/权限管理页面（D-R02 延期部分）、密码找回与改密、自助注册、JWT 或外部身份提供方、多设备会话列表、滑动续期、登录限流与审计（D-R05 延期）。不提供硬编码“已登录”依赖。

## 约束

- 零新增依赖：只用标准库 `sqlite3`、`hashlib`、`secrets`、`hmac`；不引入 passlib、bcrypt、python-jose 或 ORM（[ADR-002](../../.agents/notes/proposed/architecture/2026-10-20-adr-002-minimal-stack.md)）。
- 口令与令牌不得进入数据库明文、日志、异常消息或测试快照。
- 认证由 G2 拥有，挂在既有 `/m2` 挂载点下的 `/m2/auth/*`；`app/main.py` 装配认证路由及统一错误处理。
- 时间一律存 UTC 文本 `YYYY-MM-DDTHH:MM:SSZ`；会话过期比较在 SQL 内用 `strftime('%Y-%m-%dT%H:%M:%SZ','now')` 完成，避免宿主机时区影响。
- 数据库文件与真实凭据不提交；演示账号口令为虚构值，种子只保存派生值，演示说明标注使用范围。
- 已提交 V1 保持不变；后续 schema 变化新增版本，数据库文件由 G3 汇总。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A 服务端 `session` 表 + HttpOnly Cookie，仅存令牌哈希 | 与 D-R01 原文“服务端只存令牌哈希”一致；退出立即失效；零依赖；便于撤销 | 每次请求多一次主键查询；需要自己写过期清理 | 原任务采用 |
| B JWT 或签名 Cookie | 无状态、不查表 | 需新依赖；退出无法真正失效（只能靠短 TTL 或黑名单），与 D-R01 冲突 | 不采用 |
| C 使用 fastapi-users | 成熟的会话与校验行为 | 强依 SQLAlchemy，违反“不引入 ORM”；需新依赖 | 不采用 |

原任务参考记录：只读取结构与约定，未复制实现。[fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)（MIT）可用于借鉴依赖注入鉴权组织与 pytest 写法，但其 `security.py` 是 JWT + pwdlib(argon2)，与本需求冲突；[fastapi-users](https://github.com/fastapi-users/fastapi-users)（MIT）模型清晰但绑定 SQLAlchemy；[fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices) 当时无 LICENSE，只作阅读，不复制代码。以上为原任务的参考记录，本次未重新核对外部项目。

## 相关文件

`database/migrations/V1__init.sql`（G3 汇总的公共文件，公共契约仍需相关组评审）、`database/seed.sql`（演示账号，幂等）、`app/d/auth/password.py`、`session.py`、`users.py`、`dependencies.py`、`router.py`、`errors.py`、`app/main.py`、`tests/d/auth/`、本文件。

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

整合后的待执行命令：`python -m pytest tests/d/auth -q`、`python scripts/ci.py`；本机 `uvicorn` 启动后用 `curl` 走一遍登录、`/me`、退出、旧 Cookie 复验。实际结果须另记日期和提交号。本次文档整理未运行这些验证。

## 故意破坏实验（2026-10-21，原分支记录）

本节保留原命令中的 `tests/d` 路径和原结果，说明 2026-10-21 的实验。整合后的测试路径见上节；以下数量不是本次整合结果。

目的：证明测试真的依赖实现，而不是断言常量。

- **实验 A（口令校验）**：把 `app/d/auth/password.py::verify_password` 首行改成恒 `return True`，`python -m pytest tests/d -q` → **12 failed, 16 passed**（错误口令、非法散列 8 组参数、非字符串入参、登录错误凭据、账号不存在与口令错误文案一致等用例全部失败）。恢复后 → **28 passed**。
- **实验 C（权限判断）**：把 `app/d/auth/dependencies.py::require_permission` 的判断改成 `if False:`（恒通过），`python -m pytest tests/m2 tests/d -q` → **2 failed, 43 passed**（学生越权提交、教师越权审批）。恢复后 → **45 passed**。
- 过程教训：实验 A 第一次改错了函数签名（`stored_hash` vs `stored`），文本未替换、测试全绿；后来在脚本里加 `assert 文本已变化` 才确认破坏真的生效。“测试没红”时先确认破坏是否生效。
- 原实验未覆盖：`Secure` Cookie 属性、会话清理任务、并发争抢 `BEGIN IMMEDIATE` 的超时行为，均需真实 HTTPS/并发环境，2026-10-21 未验证。
