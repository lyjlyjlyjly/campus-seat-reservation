# 架构与分工

本文件说明目录、调用边界和接入依赖；需求状态和本轮合入证据统一见 [需求基线](requirements.md)，整合批次见 [LOCAL-010](specs/LOCAL-010-branch-integration.md)。架构取舍的权威记录在 [决策索引](decisions/README.md) 所链接的 Note 中。ADR-001、ADR-002、ADR-003 仍为提案，源码合入不代表三组已完成确认。

## 当前应用结构

浏览器访问同一个 FastAPI 进程。`app/main.py` 装配首页、健康/版本接口、`/assets` 静态资源，以及 `/m1`、`/m2`、`/m3` 三个业务路由挂载点。M1、M2 当前 main 的业务路由仍为空；M3 规则、持久化、接口与页面按批次整合，不新增第四个业务挂载点。

SQLite 文件由 `app/bootstrap.py` 显式创建和迁移，运行时通过 `app/common/db.py` 的独立连接访问。配置集中在 `app/common/config.py`；默认数据库位于被 Git 忽略的 `var/`。页面使用 HTML/CSS 和必要的原生 JavaScript，通过同源 API 读写数据，不引入前端构建。

查看 [按三组组织的项目逻辑图](diagrams/project-logic.html)；[图源及校验说明](diagrams/README.md) 包含生成方式。图展示首轮开发目标与分工，不能作为业务已交付的证据。

## 三组职责

| 组 | 业务路由 | 公共职责 | 主要目录 |
|---|---|---|---|
| G1（A、B） | `/m1`：搜索与预约 | M1 拥有预约时段、冲突校验和座位预约状态 | `app/m1/`、`tests/m1/` |
| G2（C、D） | `/m2`：整教室申请、一级审批 | 认证、固定 RBAC、登录页面/公共布局；审计本轮延期 | `app/m2/`、`app/d/auth/`、`app/d/audit/`、`tests/m2/` |
| G3（E、F） | `/m3`：报修、派单、状态推进 | 空间/座位主数据、迁移种子汇总、即时反馈约定 | `app/m3/`、`app/d/spaces/`、`database/`、`tests/m3/` |

A–F 是计划中的角色占位，人员与 GitHub 账号须在实际认领时更新。G2 的公共布局与 G3 的反馈约定由三组页面共同使用。项目负责人协调 `main.py`、`common/` 和 CI 的修改。

## M3 的调用边界

```text
HTML / 原生 JavaScript
  → /m3 路由及严格输入模型
  → authenticated_reporter：共享身份入口
  → service：事务内复核身份、权限和对象范围
  → repository：参数绑定、查询与条件更新
  → SQLite：用户/权限/房间只读，repair_order 由 M3 写入
```

`app/m3/identity.py` 是唯一共享认证适配位置，调用 G2 的 `app.d.auth.dependencies.current_user(request)` 并提取服务端用户 ID。当前 main 尚无该认证实现，受保护入口返回 `503 auth_unavailable`；不会从业务参数、浏览器开关或自定义请求头认领身份。

M3 service 在真实连接中复核 ACTIVE 身份和数据库权限。查询通过 SQL 限定本人或获准对象范围；创建、派单和开始维修在写事务中校验并保存。repository 的低层读取不自带完整鉴权，不能直接暴露给 HTTP。派单与开始维修保留条件 UPDATE 和 rowcount 检查。完整接口、字段与错误约定只在 [M3 整合交接](m3/INTEGRATION.md) 维护，公共契约仍待相关负责人确认。

已合入的 M3 页面源码与模块能力如下；公共接入状态见 [需求基线](requirements.md)，各批 PR 与 CI 见 [LOCAL-010](specs/LOCAL-010-branch-integration.md)：

| 页面 | 模块能力 |
|---|---|
| `/m3/report` | 房间文字报修；[005 规格](specs/M3-LOCAL-005-report-create.md) |
| `/m3/my-orders`、`/m3/orders/{order_id}` | 本人工单列表与有权限的详情读取；[006 规格](specs/M3-LOCAL-006-order-queries.md) |
| `/m3/dispatch` | 管理队列、合法维修人员候选与手动派单；[007 规格](specs/M3-LOCAL-007-manual-assignment.md) |
| `/m3/assigned` | 本人受理列表与开始维修；[008 规格](specs/M3-LOCAL-008-start-repair.md) |

页面是公开外壳，私有数据和写入操作由 API 鉴权。默认初始化不会准备这些功能所需的真实账号、正式工单表或授权数据。M3 自动测试使用临时数据库，并在外部身份边界注入测试身份；这类结果不等同于真实共享登录或浏览器验收。

独立的 `state_rules.py` 和 `report_validation.py` 已进入 main。004–008 来源实现中的状态检查及创建文本处理仍各自存在，尚未统一复用这两个函数；不能因文件同时存在就声称调用整合完成。

## 数据与公共依赖

- D 管房间、座位身份、位置和属性；M1 管预约、可约时段和占用状态。共享一个 SQLite 文件不代表可以跨模块直接写表。
- 当前 main 的正式迁移目录没有业务迁移，默认初始化的数据库版本为 0；种子尚不生成账号或主数据。原 G2 的 `V1__init.sql`、种子和说明已拆为 G3 数据库 PR，仍待跨组人工评审。已有 V1 保留原内容，后续结构变更使用新的正式版本；详见 [数据库说明](../database/README.md)。
- `app/m3/sql/repair_order.sql` 是模块工单 SQL 源，尚未纳入 `database/migrations/`。`tests/m3/fixtures/V1__init.sql` 是固定来源快照，测试将它和工单 SQL 装配为临时迁移；它们不是正式迁移或默认演示环境。
- G2 的会话、固定 RBAC、教室申请及其页面仍有待合入批次，已整理的文档见 [G2-LOCAL-001](specs/G2-LOCAL-001-auth-session-rbac.md)、[G2-LOCAL-002](specs/G2-LOCAL-002-room-application.md)。其来源身份接口为 `current_user(request)`，用户对象为 `SessionUser`，认证路径为 `/m2/auth/*`，登录页为 `/m2/login`；这些是待接入实现的约定，不代表当前 main 已提供这些端点。
- M3 的 `repair:report`、`repair:read_own`、`repair:assign`、`repair:read_assigned`、`repair:start` 权限尚无正式初始化。模块不得自动创建权限或按角色名绕过检查；最终映射由相关负责人确认后按迁移/种子流程接入。G2 原种子仅提供 `room:*` 授权，合入它也不会自动接通 M3。
- 每次连接启用外键并明确事务范围；输入值采用 SQL 参数绑定，连接用完关闭。模块测试使用独立临时 SQLite，不读取开发库。
- M3 当前房间范围和三状态为 `REPORTED → ASSIGNED → IN_REPAIR`。座位报修、待验收/完成/退回、评价、超时与 M3→M1 写回仍未实现；后续 HTTP 写回取舍见 [ADR-003](../.agents/notes/proposed/architecture/2026-10-20-adr-003-seat-state-integration.md)。

## 后续接入顺序

1. 按 LOCAL-010 完成已存在的单组源码批次，逐项记录对应 PR 与实际 CI。
2. 完成共享数据库、认证公共层的跨组人工评审，再按依赖合入 G2 会话及教室申请批次；保留原分支与 V1 历史。
3. 相关负责人确认 M3 正式迁移版本与五项权限映射，接入正式初始化并协调使用正式迁移的测试夹具。当前整合不自动扩展这些未交付范围。
4. 在已准备的真实演示环境完成登录、报修、派单、开始维修、对象隔离、失败提示和浏览器交互验收，实际填写验收人与结果。

需求状态以 [需求基线](requirements.md) 为准。服务器部署、生产审批、动态角色管理、定时任务和跨模块写回继续保留在后续范围。
