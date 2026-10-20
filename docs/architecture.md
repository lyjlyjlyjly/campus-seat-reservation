# 架构与分工

本文件说明当前目录和依赖关系；架构取舍的权威记录在 [ADR-001](../.agents/notes/proposed/architecture/2026-10-20-adr-001-public-layer-ownership.md)、[ADR-002](../.agents/notes/proposed/architecture/2026-10-20-adr-002-minimal-stack.md)、[ADR-003](../.agents/notes/proposed/architecture/2026-10-20-adr-003-seat-state-integration.md)。三篇目前均待正式确认，不能视作已完成组内表决。

## 当前基础结构

浏览器访问同一个 FastAPI 进程。`app/main.py` 装配首页、健康/版本接口、静态资源和 `/m1`、`/m2`、`/m3` 三个业务路由挂载点。业务路由目前为空；D 通过公共子域包提供后续共享能力，没有重复的登录实现。

SQLite 文件由 `app/bootstrap.py` 显式创建和迁移，运行时通过 `app/common/db.py` 的独立连接访问。配置集中在 `app/common/config.py`；默认数据库位于被 Git 忽略的 `var/`。本轮使用 HTML/CSS，首页以文件响应提供，不引入前端构建。

查看 [按三组组织的项目逻辑图](diagrams/project-logic.html)；[图源及校验说明](diagrams/README.md) 包含生成方式与当前范围。

## 三组职责

| 组 | 业务路由 | 公共职责 | 主要目录 |
|---|---|---|---|
| G1（A、B） | `/m1`：搜索与预约 | M1 拥有预约时段、冲突校验和座位预约状态 | `app/m1/`、`tests/m1/` |
| G2（C、D） | `/m2`：整教室申请、一级审批 | 认证、固定 RBAC、登录页面/公共布局；审计本轮延期 | `app/m2/`、`app/d/auth/`、`app/d/audit/`、`tests/m2/` |
| G3（E、F） | `/m3`：报修、派单、状态推进 | 空间/座位主数据、迁移种子汇总、即时反馈约定 | `app/m3/`、`app/d/spaces/`、`database/`、`tests/m3/` |

A–F 是计划中的角色占位，人员与 GitHub 账号须在实际认领时更新。G2 的公共布局与 G3 的反馈约定由三组页面共同使用。项目负责人协调 `main.py`、`common/` 和 CI 的修改。

## 数据与接口约束

- D 管房间、座位身份、位置和属性；M1 管预约、可约时段和占用状态。共享一个 SQLite 文件不代表可以跨模块直接写表。
- 各模块用同一套用户身份和固定角色检查；G2 已按下方[公共契约](#公共契约g2-提案2026-10-20)提出账号、角色、会话与教室申请字段，工单状态与座位/楼宇主数据仍待 G3 冻结。当前不提供硬编码“已登录”依赖。
- 公共主键、用户/角色字段、房间容量、时间格式/时区、审批状态、工单状态和错误响应须三组冻结。由 G3 汇总唯一首版 schema，各组提交字段需求，避免分别定义重复表；G2 的字段需求见 [SPEC-001](specs/001-auth-session-rbac.md) 与 [SPEC-002](specs/002-m2-room-application.md)。
- 业务表尚不存在，数据库版本为 0。第一版真实业务迁移是 `database/migrations/V1__init.sql`；提交后结构调整新增 V2、V3，不改旧版本。细节见 [数据库说明](../database/README.md)。
- 每次连接启用外键并明确事务范围；输入值采用 SQL 参数绑定，连接用完关闭。测试使用独立临时 SQLite，不读取开发库。
- 后续 M3→M1 以 HTTP 写回座位状态，具体契约见 ADR-003 提案；本轮延期，不把共享数据库调用当网络调用完成。

## 公共契约（G2 提案，2026-10-20）

三组共用身份、权限、时间与错误语义。下列内容由 G2 在 Review 1 提出，写入 `V1__init.sql` 前需 G1/G3 确认；未确认前不视作已冻结，其他组只追加自己的权限码与业务表。任务范围见 [SPEC-001](specs/001-auth-session-rbac.md)、[SPEC-002](specs/002-m2-room-application.md)，取舍理由见 [ADR-004](../.agents/notes/proposed/architecture/2026-10-20-adr-004-server-session-auth.md)。

账号与授权使用 `app_user`、`role`、`permission`、`user_role`、`role_permission` 五表：口令只存 PBKDF2 派生值，`username` 唯一，`status ∈ {ACTIVE, DISABLED}`。固定角色为 `student`、`teacher`、`org_leader`、`approver`、`repairer`、`admin`，本轮不做角色管理页面。权限码按 `<模块>:<动作>` 命名，各组只声明自己的：G2 声明 `room:apply`（授予 `teacher`、`org_leader`）与 `room:approve`（`approver`、`admin`）；`student` 不授予 `room:apply`，用于演示拒绝路径。

会话使用 `session` 表，只存 `sha256(令牌)`，配合 `HttpOnly`、`SameSite=Lax` 的 Cookie `campus_session`；退出写 `revoked_at`，任何地方都不保存明文令牌。

时间一律保存为 UTC 文本 `YYYY-MM-DDTHH:MM:SSZ`，可直接比较与排序；页面与接口按 `Asia/Shanghai` 输入输出，转换在服务端完成。错误响应统一为 `{"error": "<code>", "message": "<中文说明>"}`：`401` 未登录或凭据错误，`403` 无权限或非本人，`404` 不存在，`409` 状态冲突，`422` 字段不合法。

教室申请状态为 `PENDING_L1`、`PENDING_L2`、`APPROVED`、`REJECTED`、`REVOKED`、`CANCELLED`；本轮只实现 `PENDING_L1 → APPROVED | REJECTED`，其余按计划延期。`PENDING_L1`、`PENDING_L2`、`APPROVED` 视为占用教室时段，重叠判定只对这三种状态生效。

## 本轮集成顺序

1. 项目负责人交付应用、连接、规则和 CI 基础结构。
2. 三组冻结公共字段、状态和验收口径；G2 定认证/角色接口，G3 汇总主数据与演示账号。
3. G3 提交迁移及幂等种子；G2 交登录及固定权限；G1/G2/G3 接入各自业务路由和页面。
4. 每组至少覆盖一条成功及一条拒绝路径，负责人汇总运行检查和本机演示。

本轮范围与当前实现状态见 [需求基线](requirements.md)。服务器部署、生产审批、动态角色管理、定时任务和跨模块写回均未因建目录而完成。
