# M3-LOCAL-001：M3 整体契约提案与开发基线

初稿日期：2026-11-11；契约修订及独立提案发布授权：2026-11-12（北京时间）。准备工作及两个独立规则任务已有实际成果，详见第 1 节。本文作为独立文档提案提交团队评审，公共契约状态仍为 **推荐方案，待相关负责人确认，尚未获团队批准**。本次发布仅包含本文，不修改业务代码、迁移或其他成员文件，不合并 PR、不开始 A/B 实现。

## 1. 授权、范围与事实依据

初次准备任务的授权：保留旧目录，克隆正式仓库，建立项目虚拟环境，安装既有依赖，初始化本地 SQLite，运行现有 CI 与启动检查，从 `origin/main` 创建 `m3/local-001-contract-spec`，仅新增本文；其历史验证保留在第 10 节。

上次用户明确授权修订这份本地提案，替代此前“旧提案保持不变”的要求，但只对本文生效。用户要求收敛房间报修、分类/长度、权限、状态约束及分批方案。随后用户明确授权将本文单独提交、推送并创建面向 main 的提案 PR，向 lyjlyjlyjly 请求评审。修订和发布授权均不等于项目负责人、G2、空间负责人或迁移负责人已批准公共契约，也不是下一批编码授权。

旧目录 `G:\Mycode\campus-seat-reservation-main` 完整保留。正式工作副本为 `G:\Mycode\campus-seat-reservation`，origin 为 `https://github.com/lyjlyjlyjly/campus-seat-reservation.git`。本文不编造 Issue 链接、公共契约审批或代填评审人。

2026-11-12 本次 fetch 后核实的依赖快照（与初次准备时相同）：

| 分支 | 提交 | 相对 origin/main | 已核实的内容 |
|---|---|---|---|
| `origin/main` | `d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b` | 基准 | M3 路由为空；`tests/m3/` 只有占位文件；迁移执行器存在，但无业务迁移、用户或工单表 |
| `origin/m2/g2-login-and-room-application` | `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042` | 领先 9、落后 0，未合并 | 认证、固定 RBAC、用户及最小房间表、V1、种子、M2 页面和行为测试 |
| `origin/infra/spec-001-module-scoped-git` | `bc1f1354c4b21eefdc718ffbd05912c734366070` | 领先 2、落后 0，未合并 | 模块推送门禁、hook 安装器；删除 Review1 计划并修改文档入口 |

已交付到功能分支的 M3 子任务，不能当成已进入共同基线：

| 实际 PR / 功能 | 实现、验证与人工验收 | 提交、推送与当前团队评审 / 合并状态 |
|---|---|---|
| [PR #1：基础状态规则](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/1) | `app/m3/state_rules.py`，仅允许 REPORTED → ASSIGNED、ASSIGNED → IN_REPAIR；本批实际测试 26 项、完整检查 114 项通过；用户已人工验收 | 已提交并推送 `5dd7cd52439bb70e5b793fc0833e429752adf058`，分支 `m3/local-002-state-transitions`；PR open、merged=false；已请求 lyjlyjlyjly 评审，已提交的 review 记录为空，尚无团队批准 |
| [PR #2：报修文本规范化](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/2) | `app/m3/report_validation.py::validate_report_text`，检查字符串、strip 后非空，保留正文；本批实际测试 16 项、完整检查 104 项通过；用户已人工验收 | 已提交并推送 `8011cfe4711814ae913ac1dcf0888ac2bdccea5c`，分支 `m3/local-003-report-validation`；PR open、merged=false；已请求 lyjlyjlyjly 评审，已提交的 review 记录为空，尚无团队批准 |

评审/合并状态来自本次实际读取的 PR 元数据及 review 列表；测试数是各任务已经执行的历史结果，不是本轮重跑结果，也不能相加当作共同基线的测试数。两份代码均未进入 `origin/main`。M3-R01 仅文本校验完成；M3-R02/M3-R03 仅基础状态规则完成；**真实报修接口、认证/权限集成、工单迁移与持久化、表单均未完成**。

上次契约修订时，本地位于 `m3/local-003-report-validation`，HEAD 为 `8011cfe`，只有本文未跟踪，暂存区为空。本次发布已从重新 fetch 后的 `origin/main`（`d8918bbc`）创建独立分支 `infra/m3-contract-proposal`，安全带入本文，不携带 PR #1/#2、M2 或 infra 分支的未合并提交。后续真实功能仍须从依赖合入后重新核实的 `origin/main` 创建新分支。

依据：[main 基准提交](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b)、[M2 分支快照](https://github.com/lyjlyjlyjly/campus-seat-reservation/tree/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042)、[infra 分支快照](https://github.com/lyjlyjlyjly/campus-seat-reservation/tree/bc1f1354c4b21eefdc718ffbd05912c734366070)。仅使用 `git show`、树和提交差异读取其他分支；没有把它们的代码放入当前工作树。

当前适用入口：[AGENTS.md](../../AGENTS.md)、[docs/requirements.md](../requirements.md)、[docs/architecture.md](../architecture.md)、[docs/Review1计划.md](../Review1计划.md)、[docs/PJ-计划书.md](../PJ-计划书.md)、[database/migrations/README.md](../../database/migrations/README.md)。未合并 infra 中的规则尚不是 main 的生效规则；后续依赖合入后重新读取。

与本文有关的未合并实现，引用固定提交和完整文件名，避免与另一分支的 SPEC/ADR 编号混淆：

- [app/d/auth/dependencies.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/dependencies.py)：实际接口是 `current_user`、`require_permission(code)`。
- [app/d/auth/users.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/users.py)：`SessionUser(id, username, display_name, roles, permissions)`，仅 ACTIVE 用户取得身份。
- [database/migrations/V1__init.sql](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/database/migrations/V1__init.sql)：已有 `app_user`、授权/会话表、`room`、`room_application`，没有座位或工单表。首次提交为 [4c58d12b63b6cc6df3aac5baa622657ae250783b](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/4c58d12b63b6cc6df3aac5baa622657ae250783b)。
- [docs/specs/001-auth-session-rbac.md](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/docs/specs/001-auth-session-rbac.md)、[docs/specs/002-m2-room-application.md](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/docs/specs/002-m2-room-application.md)：提供依赖背景，不视作三组已批准契约。
- [tests/conftest.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/tests/conftest.py)、[tests/d/test_auth_schema.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/tests/d/test_auth_schema.py)：真实迁移/种子模板库、真实登录 fixture，以及需要协调的全局计数断言。

文档与代码差异必须由依赖负责人澄清：认证 spec 写 `require_user`、30 分钟“滑动过期”，代码实际是 `current_user`、登录后固定 30 分钟过期；房间列表实际为 `GET /m2/rooms`。M2 架构文档仍有“没有业务表”等旧说明及指向旧 ADR 文件名的链接。后续接入以确认后的实际代码契约为准，不照旧文字另写认证。

## 2. 个人职责与需求追踪

本人负责 **M3 物业报修**，主要改动范围是 `app/m3/`、`tests/m3/`、M3 专属页面/资源及对应任务 spec。功能交付时再同步 M3 需求证据和必要使用说明。本轮仅修订本文，不改需求状态表。

`database/`、`app/d/spaces/`、`app/bootstrap.py`、公共认证、应用入口、共享布局与公共测试均需先确定任务负责人和受影响组；目录归 G3 不等于已由本人认领。不得修改 M1/M2 业务逻辑或写入它们拥有的业务表。保持 sqlite3、HTML/CSS 和少量原生 JavaScript，不引入 ORM、状态机库、前端构建或通知系统。

| 需求 | 首阶段目标 | 保留的未完成范围 |
|---|---|---|
| M3-R01 | 文字报修：房间、类型、描述，成功生成 REPORTED 工单 | 推荐先交付房间报修；座位报修待空间契约，不得把房间子集标为整项完成；图片不在本轮 |
| M3-R01 / M3-R03 配套查询 | 本人工单列表、详情及当前状态 | 查询是既有需求的配套验收，不编造新的需求 ID；映射请需求负责人确认 |
| M3-R02 | 管理员手动指派合法维修人员 | 不做自动派单、重新派单或撤回 |
| M3-R03（部分） | ASSIGNED → IN_REPAIR；拒绝非法和重复转换 | 完工、PENDING_ACCEPT、DONE、验收退回后续单独交付 |
| M3-R04 | 首阶段不实现 | 派单/维修超时阈值、升级规则、调度方式保留待后续确认 |
| M3-R05 | 首阶段不实现 | 报修人验收、失败退回、1–5 星及文字评价保留 |
| M3-R06 | 首阶段不实现 | M3→M1 的真实 HTTP 下架/恢复、幂等与失败一致性保留；不得直接改 M1 表 |

D-R01/D-R02 是由 G2 提供的依赖；D-R03 是需另一位 G3 成员或指定负责人交付的空间依赖；M3 页面采用 D-R04 的当前操作提示，但不认领整个公共提示框架。跨模块后续依据链接到现有 [2026-10-20-adr-003-seat-state-integration.md](../../.agents/notes/proposed/architecture/2026-10-20-adr-003-seat-state-integration.md)，本文不新增 ADR 或重复编号。

## 3. 实施基线的两个方案

| 方案 | 基点、PR 与顺序 | 收益 | 代价与结论 |
|---|---|---|---|
| A：共享依赖合入 main 后开始集成 | 负责人安排 V1/认证/必要共享测试及两个 M3 PR 分别评审合入；随后按各批所需依赖，从重新 fetch 的 `origin/main` 建功能分支，PR 指向 main | 不携带另一组代码；复用经过评审的 M3 函数；测试针对共同基线 | 需要等待依赖。**默认推荐**；创建业务依赖 PR #2，派单/开始维修再复用 PR #1；等待期间评审契约，不再拆零碎辅助函数或把替身当集成 |
| B：临时依赖未合并 M2 | 如另获明确授权，基点为当时核实的 M2 提交（本次 dd747491）；M3 的堆叠 PR 暂指向 `m2/g2-login-and-room-application`，M2 先合入后再由负责人安排目标切换及完整差异复核 | 可以提前进行真实接口联调 | M2 未确认契约会变；infra hook 按 origin/main 累计检查，可能在推送前拒绝混合范围，即使 PR 指向 M2 也不自动解决；目标变化会暴露额外提交。**本轮不采用**，不得绕过门禁或自行复制、merge、rebase、cherry-pick 他人代码 |

截至本轮，已发生的授权覆盖准备任务、两个已验收规则任务及本文修订；下一批真实业务实现尚未授权。A 是推荐方案，B 未授权。依赖推进由项目负责人和相应成员完成，本人不代为合并 PR 或认领公共实现。

## 4. 工单数据与状态提案

本节及第 5–8 节所有新增表名、字段、权限码、API、限制与状态操作规则均为 **推荐提案，待相关负责人确认**。首个持久化任务推荐集中创建支持首阶段三状态的最小 `repair_order` 表，避免每增加一个操作就重建状态约束；此表结构不代表派单和维修接口已实现。

| 字段 | 类型 / 约束建议 | 来源与用途 |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | 数据库生成，不允许客户端指定 |
| `reporter_id` | INTEGER NOT NULL，引用 `app_user(id)`，ON DELETE RESTRICT | 来自 `current_user.id`；不能从请求体认领身份 |
| `room_id` | INTEGER NOT NULL，引用 `room(id)`，ON DELETE RESTRICT | 房间是必填位置；不能填自由文本假位置 |
| `fault_type` | TEXT NOT NULL，CHECK 枚举 | 推荐 `ELECTRICAL`（电气故障）、`WATER`（给排水故障）、`FURNITURE`（家具故障）、`OTHER`（其他故障）；规范化后须精确匹配枚举，页面显示中文；待确认 |
| `description` | TEXT NOT NULL，保存规范化结果；1–1000 个 Unicode 字符（码点） | 先 strip，再用 Python `len` 检查，不按 UTF-8 字节数；数据库长度约束须与应用口径一并评审，不替代规范化校验；页面使用 textContent 展示 |
| `status` | TEXT NOT NULL，默认 REPORTED | 首阶段 CHECK 仅允许 REPORTED、ASSIGNED、IN_REPAIR |
| `assigned_to`、`assigned_by` | 可空 INTEGER，分别引用 `app_user(id)`，ON DELETE RESTRICT | 维修人员和派单操作者；不能按演示账号 ID 硬编码 |
| `assigned_at`、`started_at` | 可空 TEXT | 派单/开始维修时写入服务器 UTC 时间 |
| `created_at`、`updated_at` | TEXT NOT NULL | 服务器生成 UTC `YYYY-MM-DDTHH:MM:SSZ`；页面转换为北京时间 |

建议索引：`(reporter_id, created_at, id)`、`(assigned_to, status, id)`、`(status, created_at, id)`。同一秒内创建的工单仍按 id 稳定排序。首阶段不保存真实联系方式、图片、评价、升级记录或 M1 占用信息。

保留 PR #2 的通用 `validate_report_text` 函数及其宽松约定，不修改已提交函数来加入分类和长度限制。PR #2 合入共同基线后，创建工单业务层先调用它取得规范化文本，再校验上述枚举及 `1 <= len(description) <= 1000`，通过后才持久化。中文、非 BMP 字符均按 Unicode 码点计数，组合字符不额外合并；不按编码字节数，也不折叠正文空格/换行。函数单独通过不代表最终创建请求合法；分类、长度、位置、身份及权限检查必须共同通过。未来测试覆盖规范化后的 1/1000 边界、0/1001 拒绝、中文/非 BMP 内容及未知分类，不截断超长正文。

数据库状态不变量推荐如下；`status` 本身必须 NOT NULL，四个可空字段逐项使用显式 `IS NULL` / `IS NOT NULL`，不使用 `= NULL` 或依赖可空比较的真假：

| status | assigned_to | assigned_by | assigned_at | started_at |
|---|---|---|---|---|
| REPORTED | IS NULL | IS NULL | IS NULL | IS NULL |
| ASSIGNED | IS NOT NULL | IS NOT NULL | IS NOT NULL | IS NULL |
| IN_REPAIR | IS NOT NULL | IS NOT NULL | IS NOT NULL | IS NOT NULL |

供迁移负责人评审的 CHECK 表达式示意（仅文档，不是已执行迁移）：

```sql
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
```

配合 `status NOT NULL`、三状态枚举、用户/房间外键，不允许未知状态或缺失身份/创建更新时间。未来迁移行为测试须对每种状态覆盖四字段的 NULL/非 NULL 组合，仅接受表中对应组合；非法 INSERT/UPDATE、缺失外键及失败事务均应拒绝且保留原数据。“受理人是 ACTIVE 且具有维修授权”仍由事务内真实查询验证，不用 SQLite CHECK 代替跨表校验。

| 当前状态 / 操作 | 操作者要求（提案） | 结果 |
|---|---|---|
| 无记录 → 提交 | ACTIVE 登录用户且有 `repair:report` | 新增 REPORTED，记录本人和位置；201 |
| REPORTED → 派单 | 有 `repair:assign`；目标人员满足第 5 节 | 写受理人/派单人/时间，变 ASSIGNED；200 |
| ASSIGNED → 开始维修 | 有 `repair:start` 且 `assigned_to == current_user.id` | 变 IN_REPAIR，写开始时间；200 |
| 重复派单、重复开始或越过步骤 | 即使操作者有权限也不允许 | 409，所有工单字段保持不变 |

写操作使用 `connect_database` 独立连接、参数绑定和显式事务，每个连接启用外键。创建时在事务内复核真实用户/授权及房间存在性、所选停借规则，再写入本人名下的 REPORTED 工单；身份来自认证上下文，时间由服务端生成。派单/开始推荐 `BEGIN IMMEDIATE`，将人员/状态检查和更新放在同一事务内，以 `UPDATE ... WHERE status = ?`（开始时再限定 assigned_to）及 rowcount 判断竞争；复用 PR #1 规则不能替代事务内重查或条件更新。SQLite 锁错误不能被吞掉或返回成功：提案映射为 503 `temporarily_unavailable`，允许用户稍后重试，公共错误码须 G2 确认。

首阶段不存在改状态的通用 PATCH 接口，也不接受客户端的 reporter_id、status、assigned_by 或时间字段。请求 schema 建议拒绝多余字段（422），ID 为严格正整数，拒绝 bool 和非整数。

## 5. 认证、权限与读取范围提案

依赖合入后直接导入 `app.d.auth.dependencies.current_user`、`require_permission` 和 `app.d.auth.users.SessionUser`，使用现有 `campus_session` Cookie。角色与权限取真实数据库，不另建用户表、登录、会话或硬编码“已登录”逻辑。

权限使用 `repair:<动作>`，与现有 `room:<动作>` 形式一致，具体命名与授权须 G2 确认：

| 建议权限码 | 建议授予角色 | 授权范围 |
|---|---|---|
| `repair:report` | 现有全部六种角色：student、teacher、org_leader、approver、repairer、admin | 仅以本人身份报修；未来新增角色不隐式获得权限 |
| `repair:read_own` | 同上 | 本人工单列表及详情 |
| `repair:assign` | admin | 管理员派单队列、全量工单详情、维修人员候选列表及派单 |
| `repair:read_assigned` | repairer | 仅指派给自己的工单 |
| `repair:start` | repairer | 仅开始自己受理且为 ASSIGNED 的工单 |

不新增角色；不更改已有 room:apply / room:approve 授权。普通 admin 不自动获得 repair:start；兼有 repairer 且获相应权限的账号仍须是工单受理人。服务端按权限检查，不在 M3 另造“管理员万能放行”分支。

合法受理人建议同时满足：`app_user.status == ACTIVE`、拥有 repairer 角色、具有 repair:start 权限。候选列表查询与提交时重新校验使用同一条件；禁用、删除、失去角色/权限或不存在的目标均拒绝（422），工单不变。仅按 ID 存在判断不够。M3 对 app_user/role/user_role/role_permission/permission 只读；共享授权初始化由迁移负责人协调，不由报修请求写入。

详情访问推荐采用以下顺序，**待 G2 确认**，替代初稿“他人工单 403”的建议；不因此改动 M2 的业务规则：

1. `current_user` 校验会话；未登录或会话失效返回 401 `unauthenticated`。
2. 已登录但不具备 `repair:assign`、`repair:read_own`、`repair:read_assigned` 中任何一个详情功能权限时，返回 403 `forbidden`，不先查询目标是否存在。
3. 具备上述至少一个功能权限后，仅允许有 `repair:assign` 的管理访问，或“reporter_id 为本人且有 read_own”，或“assigned_to 为本人且有 read_assigned”。无权查看该具体工单与工单不存在均返回相同的 404 `not_found` 和同一消息“工单不存在或不可访问”，不返回工单正文或存在性区别。

列表默认始终按本人过滤，管理员的默认“我的工单”也不返回全量。单权限操作复用 `require_permission(code)`；详情在现有身份及权限集合上组合功能权限和对象范围，不新建认证/RBAC。上述隐藏式 404 限于详情读取；派单/开始维修的未授权写操作仍按各自功能及受理人检查返回 403，未知工单 404，状态冲突只在通过授权后返回 409。

M2 登录页当前固定跳转 `/m2/apply` 或 `/m2/approve`。推荐首阶段复用 `/m2/login`，在 M3 报修入口明确“登录后返回报修页”，允许登录后手动返回该页完成验收，不以自动跳转为前置。若要自动返回，须 G2 另行提供仅允许本站路径的 `return_to` 契约；M3 不修改 `web/assets/m2.js` 或重新实现登录。第 9 节统一列出 G2 需回复的认证入口、权限和错误响应决定。

## 6. 位置、API 与错误响应提案

### 6.1 房间先行，座位另行接入

推荐首阶段只接受 room_id，等共享依赖合入后只读 `room(id, name, capacity, is_active)`。这些字段目前仍在未合并 M2 分支，不能写成 main 已可使用。推荐 M3 在自己 repository 中按确认的共享字段只读查询，不导入 `app/m2/applications.py`，不写 room，不自动把 `/m2/rooms` 当成跨模块依赖接口。若空间负责人要求统一走 D 的读取函数，由其先交付稳定契约，再调整前置依赖。

room_id 推荐为严格正整数，拒绝 bool/非整数；未知房间返回 422 `invalid_request`，不生成工单。`is_active=1` 的已存在房间可报修。`is_active=0` 的处理必须在空间负责人解释字段含义后选定，当前不默认选择：

| 待选择分支 | 空间负责人确认的字段含义 | 对 is_active=0 的推荐处理 |
|---|---|---|
| A：借用可用性 | 0 仅表示停借、不可预约，资产仍存在 | 允许报修；候选房间列表包含并标注停借，提交时仍复核存在性 |
| B：资产停用/撤销 | 0 表示该房间已不在可受理资产范围 | 禁止新建报修，返回 422；候选列表不提供，手工提交也拒绝且不落单；已有历史工单不删除 |

空间负责人须回复 A 或 B（若混合语义则先明确区分条件）；未回复前阻塞依赖此规则的候选列表和创建业务，不凭名称猜测。列表与提交必须采用同一口径，事务内重新验证。capacity 不限制报修，也不读取或改变 M1 可预约状态。

在座位契约完成前，表/API 不先增加无外键的 seat_id；若收到 seat_id 等未支持字段返回 422，不能悄悄降级成房间工单。页面明确“当前仅支持房间报修”。**房间子集交付后 M3-R01 仍为部分完成，D-R03 也未由此完成。**

后续座位阶段建议：由 spaces 负责人提供稳定座位主键、room_id 归属及停用语义，再由协调好的新迁移给工单增加可空 seat_id（外键引用实际确认表）。room_id 继续必填，seat_id 为空表示房间级；非空时必须真实存在且属于该 room_id。拒绝未知座位、房间不匹配；对停用座位采用确认后的资产规则，不能仅因 M1 当前不可约就拒绝故障报告。旧房间工单升级后 seat_id 为空，不删除、伪造或重写历史位置。

### 6.2 API 和页面候选

所有下列路径都是待评审提案，尚未实现；沿用已挂载的 `/m3` router，一般不需要改 `app/main.py`。

| 方法与路径 | 作用 / 返回 | 权限 |
|---|---|---|
| `GET /m3/rooms` | 返回 `{items: [{id, name, is_active}]}`，用于位置选择 | repair:report |
| `POST /m3/work-orders` | JSON `{room_id, fault_type, description}`；返回已持久化工单，201 | repair:report |
| `GET /m3/work-orders` | 本人列表 `{items, total}`；按 created_at、id 倒序 | repair:read_own |
| `GET /m3/work-orders/{order_id}` | 详情 | current_user 加第 5 节对象级判断 |
| `GET /m3/work-orders/dispatch` | 管理队列，可按合法 status 筛选，默认 REPORTED | repair:assign |
| `GET /m3/repairers` | 合法受理人 `{id, display_name}`，不返回密码、会话信息 | repair:assign |
| `POST /m3/work-orders/{order_id}/assign` | JSON `{assigned_to}`；返回更新后的工单 | repair:assign |
| `GET /m3/work-orders/assigned` | 仅分配给当前人员的工单 | repair:read_assigned |
| `POST /m3/work-orders/{order_id}/start` | 不允许指定目标状态；返回更新后的工单 | repair:start 加受理人校验 |

静态列表路径必须先于 `/{order_id}` 注册，避免把 dispatch/assigned 当作 ID。首阶段数据量小，列表暂不引入分页或导出；增加前需单列范围。返回字段使用第 4 节工单字段，可补 room_name、reporter_name、assigned_to_name 以便展示；不序列化完整用户行。时间返回 UTC，浏览器以北京时间显示。

页面建议 `/m3/report`、`/m3/my-orders`、`/m3/orders/{order_id}`、`/m3/dispatch`、`/m3/assigned`；文件放 `web/templates/m3/`，资源放 `web/assets/m3/`。页面壳可公开，所有数据与写操作在 API 做授权；隐藏按钮不能替代服务端校验。成功/失败使用当前页面可读提示，描述用 textContent，表单提供 label。先复用现有公共 CSS 和同源 Cookie，不改全局布局。

等共享依赖合入后复用 `app/d/auth/errors.py::api_error` 及应用安装的处理器，保持 `{"error":"<code>","message":"<中文说明>"}`：401 unauthenticated；缺少功能权限 403 forbidden；详情的不可见/不存在对象同为 404 not_found；已授权操作的状态冲突 409 conflict；输入错误 422 invalid_request。无权查看具体工单不能使用状态错误泄露存在性。未知位置、未支持的 seat_id、非法分类/描述或维修人员均按输入错误返回 422；失败不新增或改变工单。新增 503 见第 4 节，未经 G2 确认不得扩展公共错误码；沿用统一错误体，不把 PR #2 的 Python 异常直接当 HTTP 响应。

重复操作边界：派单/开始维修是条件状态更新，重复请求 409 且时间与人员不变。新建报修没有自然唯一键，首阶段不承诺 POST 自动幂等；相同描述可以是不同故障。页面禁用提交中的按钮，网络结果不明时提示先查看本人工单，不自动重发。若要求超时重试必不重复创建，应另行确认 request_id 契约及迁移，不能用“描述相同”去重。

## 7. 迁移、种子及共享测试协调

- **复用已提交 V1，不复制另造首版，不修改已有 V1。** 等原 V1 按团队流程进入共同基线，再新增 `Vn__m3_repair_orders.sql`；n 只是占位，不是预定 V2。负责人在实施前再次 fetch、核对所有远端迁移并分配连续版本。
- 迁移仅由现有 `app.bootstrap` 顺序执行，通过 PRAGMA user_version 管理。工单表及三状态约束由 M3 提字段、指定迁移负责人落地或明确授权本人写该文件，另一受影响组评审。不在运行时 CREATE TABLE，不手改开发库。
- 房间阶段不依赖楼宇/座位表，也不替另一位 G3 成员交付 D-R03。后续真实座位 schema 进入基线后，另配编号增加工单关联及兼容测试。
- 权限/role_permission 是系统授权配置，建议经 G2 确认后放入后续版本迁移，按 code 查 role/permission ID；不改 V1、不硬编码数值 ID。可与工单迁移同批协调，也可由负责人安排先行依赖 PR；M3 API 不写授权表。
- 复用 M2 的虚构用户/角色与房间种子：已有 maint01/repairer 和 admin01/admin。不在 seed.sql 添加业务工单。跨用户及非法受理人测试需要额外人员时，在临时测试库经真实表插入虚构夹具；不为测试扩张共享演示种子。若浏览器验收确需更多账号，由 G2 和种子负责人协调。
- `tests/d/test_auth_schema.py` 固定断言版本为 1、权限数为 2、映射全表等于四行、student01 完全无权限。新增迁移/报修权限后这些断言会失败，即使 M2 授权并未改变。**推荐由迁移负责人统筹，G2/共享测试负责人维护相关文件**：将 M2 授权断言限定在 room 权限，验证 student 仍无 room:apply；保留完整迁移顺序、版本正确、真实授权行与重复种子不增加数据的验证。共享兼容调整以其负责人的独立 PR 进入基线，不混入 M3 业务 PR。M3 仅维护自己的 schema/repair 权限/创建行为测试，不删除断言或跳过失败用例；具体分工仍待第 9 节确认。
- 复用 seeded_template、seeded_settings、seeded_client、login fixture：它们运行真实迁移/种子并通过真实登录接口取得 Cookie。每个测试使用独立数据库；切换身份时注意 fixture 返回同一个客户端。多用户并行用独立 TestClient/Cookie 容器。不要用 dependency_overrides 假登录来声明真实集成完成。
- `tests/test_app.py` 当前要求 `/m3` 返回 404；上述页面使用子路径即可保留该约定。如果以后增加 `/m3` 首页，须协调共享测试，不把原断言静默删掉。共同基线已安装全局错误处理器时无需 M3 再改 app/main.py；缺失时先交回依赖负责人。

## 8. 分批验收提案

下表是未来任务安排，**不属于本次实现授权**。每次只选一批，再写对应本地任务 spec、运行适用测试并交人工验收；基础设施/纯数据批可通过真实数据库行为独立验收，不为凑次数拆成只有空文件的提交。每批 spec、M3 需求证据和必要使用说明与该批同步，不提前标记下批完成。

依赖确认后的首个完整业务目标：**真实登录用户选择真实房间，提交合法分类和描述，数据库生成本人名下的 REPORTED 工单；错误输入、未知房间、未登录及无权限请求被拒绝且不产生工单。** 推荐用 A、B 两批交付到这一目标：A 提供可通过真实数据库独立验收的持久化基础，B 一次交付创建逻辑、真实接口和表单。现有规则函数已足够作为起点，不再为增加提交次数拆出分类/长度等独立辅助任务。

| 批次 / 需求 | 功能与预计文件 | 前置依赖 | Given–When–Then 与测试范围 |
|---|---|---|---|
| A：工单持久化与迁移；M3-R01 前置、M3-R02/R03 数据支撑 | `app/m3/repository.py`、`tests/m3/test_repository.py`、`tests/m3/test_schema.py`、本批 spec；经专门授权的 `database/migrations/Vn__m3_repair_orders.sql`（n 未分配） | 原 V1 合入；用户/房间外键、字段/分类/长度及三状态约束确认；迁移编号和编写人明确；必要共享测试兼容调整先由其负责人合入 | Given 空库及保留用户/房间的 V1 库，When 真实初始化器升级并重跑，Then 数据保留、版本正确且不重复。Given 合法持久化输入，When 通过 M3 数据访问写入并用新连接读取，Then REPORTED、本人/房间引用及服务端时间确实保存。Given 无效外键、未知/NULL 状态、非法 NULL 字段组合，When INSERT/UPDATE，Then 约束拒绝且事务回滚、原记录不变。此批不提供可绕过认证的 HTTP 写入口，不宣称真实报修创建完成 |
| B：真实房间报修创建；M3-R01 房间范围、D-R04 页面采用 | `app/m3/router.py`、`app/m3/schemas.py`、`app/m3/service.py`、`app/m3/repository.py`；`web/templates/m3/report.html`、`web/assets/m3/report.js`（必要时模块 CSS）；`tests/m3/test_reports.py`、`tests/m3/test_report_page.py`、本批 spec | A；PR #2 已合入；真实认证和错误处理器、房间数据可用；五权限映射及 repair:report 初始化完成；空间负责人选定 is_active 分支；M3 创建请求/错误口径确认 | Given 真实登录及获准房间，When 经表单或真实 API 提交合法报修，Then 201、显示工单编号/成功提示，独立连接读到本人名下 REPORTED、规范化文本和四个 NULL 派单/维修字段。Given 未登录、真实登录但无 report 权限、未知/禁报房间、缺字段、非字符串、空白、未知分类、规范化后超长描述、seat_id 或伪造身份/状态/时间，When 提交，Then 401/403/422 且工单数不增。覆盖 1/1000/1001 Unicode 字符、内部换行保留和失败事务；成功不是只验证函数返回或页面文字 |
| C：本人列表及详情；M3-R01/R03 配套 | M3 查询及路由、`my-orders.html`、`order-detail.html`、对应 JS；`tests/m3/test_queries.py` | B；repair:read_own 及第 5 节对象访问口径确认 | Given 两人真实报修，When A 登录查询，Then 列表只含 A；访问 B 的详情与访问不存在工单均返回相同 404/错误体，不返回正文。未登录 401；没有任何详情功能权限 403。检查排序、空列表及文本安全展示；管理员默认“我的工单”仍只含本人 |
| D：手动派单；M3-R02 | M3 管理队列、候选查询和派单；`dispatch.html`、对应 JS；`tests/m3/test_assignment.py` | B/C；PR #1 已合入并复用；repair:assign、repair:start 及维修人员合法性契约确认，授权进入迁移 | Given REPORTED 与合法维修人员，When admin 派单，Then ASSIGNED 且受理人/操作者/时间正确。Given 普通用户、禁用/未知/非维修/无 start 权限目标，When 派单，Then 403 或 422、工单不变。Given 已派单工单，When 再派，Then 409、人员与时间不变。浏览器完成派单并在详情核对；真实独立连接验证重复/竞争只有一次成功 |
| E：开始维修；M3-R03 首阶段部分 | M3 状态服务、受理列表、开始接口；`assigned.html`；`tests/m3/test_transitions.py` | D；PR #1 已合入并复用；repair:read_assigned、repair:start 及本人受理规则确认 | Given ASSIGNED 且本人是受理人，When 开始，Then IN_REPAIR、started_at 写入。Given 他人维修员、普通 admin、未登录用户，When 操作，Then 403/401。Given 已授权操作中的非法状态或重复请求，When 开始，Then 409、所有字段不变。浏览器受理人开始并与报修人页面核对。此批不调用 M1 |
| S：座位报修补齐；M3-R01 剩余位置范围 | 经协调的新迁移、M3 位置查询/表单/校验与 `tests/m3/test_seat_reports.py` | spaces 负责人交付真实座位数据、归属及停用契约；编号重新分配 | Given 有效座位，When 按其房间报修，Then 持久化座位引用；未知/错房间座位拒绝不落单。Given 旧房间工单，When 升级，Then 仍可查询且 seat_id 为空；不得以伪座位夹具宣称公共集成已完成。依赖就绪后可在 D/E 前安排，不承诺固定日期 |
| 后续：完工验收评价；M3-R03 剩余、M3-R05 | 独立 spec、M3 状态/评价/页面/测试及协调迁移 | 完工操作者、PENDING_ACCEPT/DONE 与评价契约确认 | Given 待验收，When 报修人通过/退回，Then DONE/IN_REPAIR；他人拒绝；1–5 星边界、重复验收及失败不变覆盖 |
| 后续：超时；M3-R04 | 独立 spec，限定调度与升级记录 | 团队确认阈值、执行者、幂等和通知范围 | Given 已到阈值，When 重复执行真实处理，Then 仅升级一次并可追溯；阈值前不升级 |
| 后续：HTTP 联动；M3-R06 | M3 调用端与测试；M1 接收端由 G1 独立交付 | 房间/座位影响范围、真实 HTTP、鉴权、重试/失败一致性契约及课程口径确认 | Given 真实服务及工单，When 维修/验收经 HTTP 调用，Then M1 状态可追溯地下架/恢复；失败、重复及并发行为按冻结契约验证 |

迁移、创建逻辑、接口和表单的依赖与验收边界：

| 构件 / 所属批 | 前置条件 | 产出如何验收 |
|---|---|---|
| 新迁移及 M3 数据访问 / A | 已合入原 V1；第 4 节字段/约束、新编号、编写人及共享测试责任确认 | 真实空库/升级库、重复初始化、跨连接读写与拒绝非法组合；不用伪用户/房间表替代 V1 |
| 创建业务逻辑 / B | A；PR #2 规范化函数、分类/长度及房间规则确认；从真实认证上下文取得身份 | 规范化 → 分类/长度 → 事务内真实身份/权限和房间复核 → 持久化；所有失败均不留工单。与接口/表单同批交付，不单独宣称报修完成 |
| 创建及房间选择接口 / B | 真实 current_user/require_permission、权限初始化和错误体进入共同基线 | 真实登录 Cookie、真实 SQLite，成功 201；未登录 401、缺少 report 权限 403、输入或位置错误 422。无权限测试使用临时真实库中的无授权账号，不用假登录 |
| 报修表单 / B | 上述接口及登录返回约定；已有公共布局可复用 | 登录后在真实候选列表选择房间、用中文分类提交，看到编号；错误可读、不虚报成功，成功结果与数据库一致。自动登录回跳非首阶段前置；本人列表/详情在 C 批交付 |

D 批派单同样在 PR #1 经评审合入后复用其规则，同时保留真实资格检查、事务和条件更新；不直接复制该分支文件。未来每个实现批运行 `.\.venv\Scripts\python.exe -m pytest tests/m3` 及 `.\.venv\Scripts\python.exe scripts/ci.py`；涉及迁移/授权时包含共享 schema 与 auth 测试。成功、拒绝、失败后不变均断言真实响应和数据库。测试夹具可以创建合法临时数据，不能 mock 被测业务或假冒已接通认证/空间接口。计划在 D 或 E 批安排一次任务分支内“故意破坏 → 测试失败 → 恢复通过”，仅记录实际结果，不在本轮伪造实验。

## 9. 可直接回复的团队确认表

下表全部为待确认推荐，不代表已向成员发送消息或取得同意。请对应负责人回复“P/G/S/D 同意”，或注明该行需修改的具体项；S 还须选 A/B 并解释字段语义，P/D 须补负责人、顺序或编号。角色对应的具体人员尚未提供，不代填其他成员认领。

| 项目 | 推荐决定（可按编号回复或修改） | 确认人 | 确认后解锁的工作 |
|---|---|---|---|
| P：共同基线与门禁 | 先分别评审原认证/V1 和 PR #1/#2，合入 main 后从最新 origin/main 开新功能分支；保留既有提交历史。推荐由基础设施负责人在门禁合入前明确“已评审遗留提交按固定 SHA 记录兼容，新提交遵守新规则”的过渡方案并验证，不强制改写 M2 历史、不绕过 hook。现有 M2 含 db/d/auth/web/g2 scope 及多责任组路径，不能假定现有门禁会接受；同时明确纯 M3 spec 的目录归属规则及依赖文档冲突处理。请回复实际评审/合入顺序和协调人 | 项目负责人，协调基础设施负责人 | 确定共同开发基线、A/B 开工和后续合规 PR 路径；不会让 M3 分支混入 M2/infra 历史 |
| G：认证与权限 | 同意第 5 节五权限映射；维修资格为 ACTIVE + repairer + repair:start。详情 401/功能权限不足 403/不可见与不存在同为相同 404；输入 422、授权后状态冲突 409，锁冲突推荐 503 temporarily_unavailable。复用 current_user、require_permission、SessionUser、campus_session、api_error；首阶段经 /m2/login 登录后手动返回报修页，自动 return_to 后续由 G2 提供，不改现有 M2 逻辑 | G2 | B 的真实认证和创建授权、C 的对象访问、D/E 的合法派单及维修；统一响应映射 |
| S：房间范围与只读 | 首阶段只做真实房间，座位继续保留后续范围；推荐允许 M3 repository 只读 room 的 id/name/capacity/is_active，不写 room、不依赖 M2 业务函数。is_active=0 按第 6.1 节选择：A 仅停借则允许报修；B 不可受理资产则拒绝新报修；候选列表与提交口径一致。请明确选择及含义，如要求 D 读取函数请给出入口与交付安排 | 空间负责人 | B 的房间列表及事务内位置校验、房间与座位阶段边界 |
| D：迁移与共享测试责任 | 推荐第 4 节 repair_order 字段、四类中文映射、规范化后 1–1000 Unicode 码点、显式 NULL 状态约束及外键；复用原 V1、不改旧迁移。实施前核对远端并分配实际新版本号、指定编写人，不预占 V2。五权限初始化由迁移负责人按 G2 确认结果纳入后续版本；由其统筹 G2/共享测试负责人先调整版本/全表授权假设，M3 只维护自己的 schema/创建测试；指定另一组实际评审 | 迁移负责人；权限与共享测试分工须 G2 同意 | A 的工单表、升级与持久化；B 可使用真实权限；避免新迁移误伤既有测试 |

**下一个建议编码任务仍是 A 批“工单持久化与迁移行为验证”**，然后以 B 批交付完整房间报修创建。M3-LOCAL-002/003 已用于现有 PR，不再复用；新任务号在获授权开工时核对分配。本轮不开始 A/B。

尚未获得 P/G/S/D 的实际确认；原 V1/认证及两个 M3 PR 也未合入 main。A 至少等待共同 V1 基线、表/外键/约束、迁移编号/编写人及共享测试责任；B 另等待 PR #2、真实认证与权限初始化、位置分支和错误契约就绪。当前不能自建替代用户/房间表或用替身越过这些条件。文档推荐、个人功能验收与团队公共契约批准分开记录。

## 10. 初次准备任务验收与实际验证（历史记录）

本节保留 2026-11-11 的实际准备过程与结果，不表示本轮重新执行。下文的 HEAD、测试数量、无 M3 测试等均指当时；最新功能分支与 PR 状态以第 1 节为准。

本任务验收条件：

- Given 旧目录须保留，When 正式克隆完成，Then 新目录具有正确 origin、完整 Git 历史，旧目录不补 `.git`、不整体复制覆盖。
- Given origin/main 已核实且工作区干净，When 创建准备分支，Then HEAD 等于 origin/main，不混入 M2/infra 提交。
- Given Python 3.10 与 requirements.txt，When 建立隔离 venv 并执行基线检查，Then 记录真实解释器、初始化、CI 和 HTTP 结果；失败不得修改业务/测试/依赖来凑通过。
- Given 本文包含尚未冻结契约，When 组员审阅，Then 可逐条选择字段、权限和依赖方案，看见负责人、分批 GWT、延期项和首个编码阻塞，不误认为团队已批准。
- Given 本轮交付，When 检查 Git 状态，Then 只有本文作为新增待跟踪项目文件；正常 `.venv`、var 数据和测试缓存被忽略，无 commit/push/Issue/PR。

实际验证（2026-11-11）：

| 实际命令 / 操作 | 结果与限度 |
|---|---|
| 直接 `git clone https://github.com/lyjlyjlyjly/campus-seat-reservation.git G:\Mycode\campus-seat-reservation` | 首次失败：连接被重置；只读 ls-remote 检查亦连接超时；失败未形成可用仓库 |
| 使用系统已启用代理重试：`git -c http.proxy=http://127.0.0.1:7897 -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=30 clone https://github.com/lyjlyjlyjly/campus-seat-reservation.git G:\Mycode\campus-seat-reservation` | 成功；重试前确认目标仅为空目录。代理仅用于该命令，没有修改全局或仓库代理配置 |
| `git switch --no-track -c m3/local-001-contract-spec origin/main` | 成功，基准 d8918bbc；未设置上游，避免准备分支误跟踪 main |
| `& 'D:\Anaconda\envs\TLang\python.exe' -m venv .venv` | 使用现有 Python 3.10.20 创建独立 venv；未向其基础 Conda 环境安装依赖。与 CI 的 Python 3.10 主次版本一致 |
| `.\.venv\Scripts\python.exe` 解释器/隔离检查 | Python 3.10.20，64 位；executable 为新项目 `.venv\Scripts\python.exe`；include-system-site-packages=false、user_site=False；SQLite 3.51.2。venv 仍依赖基础解释器目录，不是可搬移的独立 Python 发行版 |
| `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | 成功；使用机器既有清华镜像。直接依赖保持 fastapi 0.150.0、uvicorn 0.54.0、httpx 0.28.1、pytest 9.1.1；没有升级或修改 requirements |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found |
| `.\.venv\Scripts\python.exe -m app.bootstrap` | 成功；`var/campus.sqlite3`，schema_version=0，seed=未执行；main 尚无业务迁移或演示账号 |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note 格式/引用与 Python 编译通过；**88 passed，1 warning，4.66s**，All checks passed。警告为 Starlette TestClient 对 httpx 的弃用提示，未屏蔽、未更换依赖；这是基础设施基线验证，不是 M3 行为通过 |
| `.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 61692`，由一次性 Python 检查脚本启动并发起真实 HTTP 请求 | `/` 200 且为含样式引用的 HTML；`/health` 200，`{"status":"ok","database":"ok","schema_version":0}`；`/version` 200，`{"version":"dev"}`。检查后停止本次服务，确认 61692 端口已释放 |

文档及范围复核：本文 UTF-8、末尾换行、空白检查通过，7 个本地 Markdown 链接均存在；`scripts/check_notes.py` 通过。对未跟踪新文件执行 `git diff --no-index --check -- NUL docs/specs/M3-LOCAL-001-contract-spec.md` 无空白错误输出，退出 1 表示与空文件存在新增差异。Git 状态只有本文未跟踪，没有已跟踪文件修改或暂存内容；HEAD 与 origin/main 相同，新增提交数为 0。虚拟环境、SQLite 和测试缓存均被既有规则忽略。另对旧目录的 79 个原文件逐个计算 Git blob 哈希，仍与基准完全一致，且没有 `.git`。

上述历史 HTTP 检查不等同人工浏览器验收。初次准备时未运行 M2/infra 分支测试，M3 测试也尚不存在；此后的两批规则成果见第 1 节，不改写历史记录。

## 11. 上次契约修订的验证（历史记录）

上次仅修订本文，保留其余已有工作。实际检查本地状态并 fetch，读取两个 PR 的元数据及 review 列表，结果见第 1 节。已执行 `.\.venv\Scripts\python.exe scripts/check_notes.py`，检查通过；UTF-8、末尾换行、空白检查通过，7 个本地 Markdown 链接均存在且受 Git 跟踪，固定提交的文件链接可在已 fetch 对象中定位。当时没有已跟踪文件修改、没有暂存内容，唯一未跟踪文件为本文，HEAD 为 `8011cfe`。这些是修订时的历史状态，不是本次独立提案发布的分支或提交依据。

上次未运行完整 CI 或新的业务测试，因为没有修改业务代码或迁移；历史通过数不作为新增集成验证。公共契约仍待第 9 节相关负责人确认。

上次契约修订未提交、未推送、未创建或合并 PR，没有产生或重置推送时间；本次发布授权与停止点见第 12 节。

## 12. 独立提案发布授权与停止点

用户于 2026-11-12 明确授权：从最新 origin/main 创建或复用 `infra/m3-contract-proposal`，只提交本文，提交和 PR 标题为 `docs(infra): 提交 M3 首阶段契约评审提案`；满足实际推送间隔后推送该分支、创建面向 main 的独立 PR，并向 lyjlyjlyjly 请求评审。未授权另发 Issue、其他渠道消息、合并 PR 或开始 A/B 功能编码。

此 PR 与 PR #1/#2 仅建立背景关联，不包含它们的代码。P/G/S/D 均保持待确认，发布或请求评审不等于公共契约批准；不填写未发生的 Reviewed-by 或团队评审结论。文档检查、精确暂存与完整差异检查的实际结果记录在本 PR；提交、远端 CI 和评审状态以实际 Git/PR 记录为准，不把 8011cfe 或 PR #2 当成本文发布证据。

推送前读取本地 Git 元数据中的最新成功推送记录，核对至少 30 分钟间隔；成功后在同一元数据目录另记本任务实际推送时间、SHA 和下一批最早时间，不提交该记录、不以 commit 时间代替 push 时间。本次完成后停在团队评审点。后续功能仍须各批明确实施授权、实际测试及人工验收，不推 main、不强推、不绕过 hook、不改写他人历史、不用 squash 抹掉课程需要的小提交。
