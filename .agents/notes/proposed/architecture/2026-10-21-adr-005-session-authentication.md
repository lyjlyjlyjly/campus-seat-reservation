# Agent Note: ADR-005 认证与会话采用服务端会话表 + HttpOnly Cookie

Status: proposed — 原分支记录已按 D-R01 实现并通过测试，待三组在字段冻结会上确认。

Date: 2026-10-21
Owner: G2（C、D）
References: [G2-LOCAL-001 登录会话与 RBAC](../../../../docs/specs/G2-LOCAL-001-auth-session-rbac.md)、[架构与分工](../../../../docs/architecture.md)、[需求基线](../../../../docs/requirements.md)

2026-11-27 文档整合草稿，来源为 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042`。原编号 ADR-004 与推送规范重号，现改为 ADR-005，原创建日期和 proposed 状态保留。2026-10-21 的验证记录沿用原日期，本次未重新执行。

## Problem

原任务开始时，三组需要共用一套登录与固定角色（D-R01、D-R02），骨架没有认证实现，公共字段尚未冻结。需要在不引入 ORM、JWT 库或前端构建的前提下，给出一个 M1/M2/M3 都能直接复用、退出后旧凭据立即失效的会话方案，并说明为什么不选另外几种常见做法。

## Alternatives considered

| 方案 | 收益 | 代价 | 结论 |
|---|---|---|---|
| A 服务端 `session` 表 + HttpOnly Cookie，库内只存 `sha256(token)` | 退出即可吊销；无新依赖；令牌明文不落库也不落日志 | 每次请求多一次索引查询；单库写入 | 原分支用于实现，公共契约待评审 |
| B JWT（HS256，常见模板做法） | 无状态，便于横向扩展 | 无法真正注销，只能等过期；要引入签名/编码依赖；令牌一旦泄露在过期前都有效 | 不采用：与 D-R01「退出后旧会话失效」直接冲突 |
| C 签名 Cookie（itsdangerous 一类） | 少一次数据库查询 | 需新增依赖；撤销仍需黑名单表，等于又回到方案 A | 不采用：复杂度没有下降 |
| D 每个请求带 Basic 认证 | 实现最短 | 口令随每次请求传输；无法退出；页面无法共享身份 | 不采用 |

原任务参考 [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)（MIT）时记录，其 `backend/app/core/security.py` 走的是方案 B，只借用其目录分层与测试组织，不照搬认证实现；参考记录与取舍理由见 G2-LOCAL-001。本次未重新核对外部项目。

## Proposal

- 表 `session(token_hash, user_id, created_at, expires_at, revoked_at)`，主键是令牌哈希，**明文令牌不落库**。
- 登录：`POST /m2/auth/login` 校验口令（PBKDF2-HMAC-SHA256，每条记录带随机盐）后生成 32 字节随机令牌，写入哈希，返回 `Set-Cookie: campus_session=…; HttpOnly; SameSite=Lax; Path=/`。
- 会话：`SESSION_TTL_MINUTES = 30`，从创建时固定计算到期时间，请求期间不续期。
- 身份：`GET /m2/auth/me` 返回用户名、展示名、角色和权限码；三组可复用 `current_user(request)` 取得 `SessionUser`，并用 `require_permission("…")` 依赖区分 `401` 与 `403`。
- 退出：`POST /m2/auth/logout` 写入 `revoked_at` 并清 Cookie，旧令牌立即失效。
- 口令错误、账号不存在、账号停用返回同一句 `401`，且不创建会话；账号不存在时也执行一次等价派生，避免用响应时间枚举用户名。
- 认证入口挂在 `/m2` 前缀下（业务上是 `/m2/auth/*`），因为它由 G2 维护；三个模块共用同一套 Cookie 与错误体，登录页只做一次。

## Acceptance criteria

- Given 正确凭据，When 登录，Then `200` 且响应带 `HttpOnly` Cookie，库内 `session` 行数 +1 且 `token_hash == sha256(Cookie 值)`。
- Given 错误口令/不存在账号/停用账号，When 登录，Then `401`、`session` 行数不变、错误文案相同。
- Given 已登录会话，When 退出后重放旧 Cookie，Then `401`。
- Given 过期会话（`expires_at` 已过），When 访问受限接口，Then `401`。
- Given 无 `room:apply` 的账号，When 提交教室申请，Then `403`；Given 未登录，Then `401`。

原分支 2026-10-21 的记录：`python -m pytest tests/d tests/m2 -q` 通过；对应历史实验见 [G2-LOCAL-001](../../../../docs/specs/G2-LOCAL-001-auth-session-rbac.md) 与 [G2-LOCAL-002](../../../../docs/specs/G2-LOCAL-002-room-application.md)。命令保留当时目录，本次未重新运行；整合后认证测试归入 `tests/d/auth/`。

## Risks

- 会话表随时间增长：原任务种子数据只有 6 个演示账号，暂不做清理任务；过期行不影响正确性，清理另排后续任务。
- 单进程 SQLite 写入集中在登录/审批：`BEGIN IMMEDIATE` 会把「查冲突→落库」串行化，并发高峰的锁等待和超时仍需单独验证。
- Cookie 未设 `Secure`，因为本地演示走 HTTP；部署到 HTTPS 时须同步配置安全属性。
- 认证路由挂在 `/m2` 下属于当前口径：若后续改为独立的 `/d` 前缀，需要同步三组页面与测试，属于公共契约变更，须先协调。
