# M3 整合交接（唯一维护入口）

本文件维护 M3 的模块能力、实际合入状态及公共接入依赖；各批 spec 保留各自范围、选择和验证记录。最新功能来源为 [M3-LOCAL-008](../specs/M3-LOCAL-008-start-repair.md)，原交接复核见 [009](../specs/M3-LOCAL-009-integration-review.md)。派单、查询、创建与持久化基础分别见 [007](../specs/M3-LOCAL-007-manual-assignment.md)、[006](../specs/M3-LOCAL-006-order-queries.md)、[005](../specs/M3-LOCAL-005-report-create.md)、[004](../specs/M3-LOCAL-004-persistence.md)。各批按可替换的暂定契约独立开发；**暂定契约不等于团队批准**，公共接入仍须协调相关负责人。

LOCAL-010 整合复核日期：2026-11-27。本次 M3 业务代码接收基线为 [a6d1b74aaee60805c952424663ac4b3539290237](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/a6d1b74aaee60805c952424663ac4b3539290237)，对应 #21 合入后的代码。以下状态以该次接收为准，后续整合记录见 [LOCAL-010](../specs/LOCAL-010-branch-integration.md)。

#21 的 head 为 `c922f3ae4592e1311a38df184eedaae19f0a3ef4`，其远端 [CI 运行 45954773978](https://github.com/lyjlyjlyjly/campus-seat-reservation/actions/runs/45954773978)、[CI 运行 45954749407](https://github.com/lyjlyjlyjly/campus-seat-reservation/actions/runs/45954749407) 均为 completed / success，push 与 PR 的两项检查均成功。文档修订自身的 PR 与 CI 在 LOCAL-010 中记录。

## 当前能力与边界

- **M3 已发布模块代码覆盖房间创建、本人查询、手动派单、本人受理及开始维修；当前 main 的接收范围见下表。真实共享登录及正式业务数据库尚未接通。** 模块代码合入和 CI 成功不等于真实账号流程、浏览器或公共契约已验收。
- 当前 main 尚无正式业务迁移；按默认迁移目录初始化新库仍为 `schema_version=0`，不会安装 `repair_order`。正式 M3 迁移及五项 `repair:*` 权限初始化均未接入；测试使用的 V1 快照和临时 V2 不改变该事实，也不改变用户已有数据库。
- G2 的 `current_user`、会话路由及登录页面尚未合入。正常 M3 受保护 API 经真实身份入口返回 `503/auth_unavailable`，页面显示认证尚未接入并拒绝数据读取及提交；没有演示身份或自动授权兜底。
- 独立状态规则和文本规范化已分别经 #12、#13 合入，但 `service.assign_order` / `service.start_repair` 尚未调用 `state_rules.validate_transition`，`models.ReportCreate` 尚未调用 `report_validation.validate_report_text`。现有服务/模型仍执行各自原有校验，函数复用属于后续接线工作。
- 待验收、完成、退回、重新派单、座位、评价、超时及 M3→M1 仍未实现，M3-R03 只能记录首阶段子范围。repository 本身不提供完整鉴权，正常路由必须经过身份入口及 service。

### 原批次与本次整合 PR

原分支和原 PR 保留来源、讨论及历史证据。本次以独立责任组的小批整合 PR 接收变更；原 PR 的开关状态与对应内容是否经新 PR 进入 main 分别核对，不能再按旧 PR 表认定所有成果都未合入。

| 原批次 / 来源 | 原提交 | 整合 PR | 已确认状态 |
|---|---|---|---|
| [原 #1：002 状态规则](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/1) | `5dd7cd5` | [#12](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/12) | 已合入 main；该批 CI 成功 |
| [原 #2：003 文本规范化](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/2) | `8011cfe` | [#13](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/13) | 已合入 main；该批 CI 成功 |
| [原 #3：001 契约提案](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/3) | `f1e1820` | [#14](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/14) | 文档已合入；该批 CI 成功；公共契约仍待确认 |
| [原 #4：004 持久化](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/4) | `fa5a35b` | [#15](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/15) | 已合入 main；该批 CI 成功；SQL 仍未成为正式迁移 |
| [原 #5：005 创建](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/5) | `49892f7` | [#18](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/18) | 已合入 main；该批 CI 成功；缺认证场景及页面测试按外部依赖隔离 |
| [原 #6：006 本人查询](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/6) | `e1fbd94` | [#19](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/19) | 已合入 [812ff1f](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/812ff1fd4725c56a9842050d140e0697e0e8a428)；push/PR 两项检查均 completed / success |
| [原 #7：007 手动派单](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/7) | `094f12d` | [#20](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/20) | 已合入 [b9a9b62](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/b9a9b6264c5a9f2a684717b4118c6afc9c06ae02)；push/PR 两项检查均 completed / success |
| [原 #8：008 开始维修](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/8) | `c3369bf` | [#21](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/21) | 已合入 [a6d1b74](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/a6d1b74aaee60805c952424663ac4b3539290237)；push/PR 两项检查均 completed / success |
| 009 原交接文档 | `5af01c2` | 本次文档修订 | 整合 PR 与 CI 见 [LOCAL-010](../specs/LOCAL-010-branch-integration.md) |

004→005→006→007→008→009 是原有连续提交链；002、003 和契约提案都是独立分支，不包含在原 008 中。本次分别接收这些来源，保留每批差异及 CI 记录，不合并重写原分支历史。

### 公共接入仍依赖的工作

| 依赖 | 当前状态与影响 |
|---|---|
| [#11：共享 schema](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/11) | 尚无实际评审记录，待另一组成员评审，未合入；正式初始化尚无共享业务 V1 |
| [#17：G2 口令工具](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/17) | 尚无实际评审记录，待跨组评审，未合入；口令工具本身不提供 `current_user` 或登录路由 |
| G2 会话、认证/RBAC 与登录页面 | 其余实现尚未整合，M3 正常请求仍按缺少认证拒绝 |
| 正式 M3 迁移与 `repair:*` 授权 | 尚未接入；迁移编号、共享测试调整与最终角色映射须协调后实施 |
| 真实账号流程、浏览器及公共契约验收 | 均待执行或确认；模块 CI 不替代这些验收 |

### 已合入独立文件的接线位置

| 文件 | 当前作用与后续适配 |
|---|---|
| [state_rules.py](../../app/m3/state_rules.py) | 已合入的合法顺序校验，尚未由服务调用。后续接入 `service.assign_order`、`service.start_repair` 的状态检查，映射非法转换为既有 409；保留身份/对象授权顺序、同事务重查、条件 UPDATE 和 rowcount |
| [report_validation.py](../../app/m3/report_validation.py) | 已合入的宽松规范化函数，尚未由模型调用。后续接入 `models.ReportCreate` 并适配错误；创建层继续执行四分类、1–1000 码点、NUL/孤立代理码点拒绝，不改变通用函数约定 |
| [M3-LOCAL-001 契约提案](../specs/M3-LOCAL-001-contract-spec.md) | 文档已合入，P/G/S/D 待确认标记继续保留。它没有实现认证、授权或正式 schema，合入文档不表示公共契约获批 |

### 历史发布与验证记录

2026-11-19 及 2026-11-24 的原分支复核曾确认：当时 `origin/main` 为 `d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b`，原 PR #1–#8 均 open、未合并，已请求 lyjlyjlyjly 评审，正式 review 列表为空。这些是对应日期的历史记录，当前接收状态以上表为准。

原完整功能来源为 [m3/local-008-start-repair](https://github.com/lyjlyjlyjly/campus-seat-reservation/tree/m3/local-008-start-repair) 的 [c3369bfddd0e81189702f13d5ba76a308bc72982](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/c3369bfddd0e81189702f13d5ba76a308bc72982)，包含 004–008。2026-11-24 的 009 文档批次以原 008 分支为目标，只补本交接文件和 009 spec；本轮修订以其 [5af01c2a96a1f6f8a95a17c812d7ce39969edbd6](https://github.com/lyjlyjlyjly/campus-seat-reservation/commit/5af01c2a96a1f6f8a95a17c812d7ce39969edbd6) 为文档来源。

原 008 固定 SHA 的 [CI 运行 44339164395](https://github.com/lyjlyjlyjly/campus-seat-reservation/actions/runs/44339164395) 在原记录中已核实为 completed / success，事件为 workflow_dispatch；当时执行 Note、Python 编译及测试，未执行 Node。该记录不能替代本次新整合 SHA 的 CI，也不能证明真实共享登录或正式迁移已经接通。

### 后续分支范围复核

每个前置批次进入 main 后，重新检查下一批的实际 base、Files changed、提交范围与 head SHA 的 CI。整合采用新提交后，原分支的祖先关系未必反映 main 已接收的内容；不能依据原 PR 仍 open 就重复导入，也不能把原后续分支整条直接并入。

例如复核原 005 的来源范围时可使用以下只读命令；实际待合入的整合分支须另外核对：

```powershell
git fetch origin
git merge-base origin/main origin/m3/local-005-report-create
git log --oneline origin/main..origin/m3/local-005-report-create
git diff --stat origin/main...origin/m3/local-005-report-create
git diff origin/main...origin/m3/local-005-report-create
```

记录实际合入 SHA、merge-base、已经接收的文件和本批独有差异。原堆叠分支若继续用于 PR，squash 或新 SHA 会使后续范围重复；应先核实范围，再在最新 main 建立组内整合分支接收本批差异并关联来源。保留原分支和历史，不强推、不改写他人历史；冲突处理遵守 [AGENTS.md](../../AGENTS.md)。

## 实际路径与调用约定

| 入口 | 当前职责 / 后续适配位置 |
|---|---|
| [app/m3/sql/repair_order.sql](../../app/m3/sql/repair_order.sql) | 唯一 M3 SQL 源；字段、四分类、1–1000 Unicode 码点、外键、三状态 NULL 组合及索引；没有版本/事务 PRAGMA |
| [app/m3/repository.py](../../app/m3/repository.py) | 保留 `create_repair_order` / `get_repair_order` 独立连接入口；`insert_repair_order` 接受调用者连接。006 新增 `list_owned_orders`、`find_visible_order` 连接内查询，SQL 限定本人/对象范围和输出列；不能将无授权 get_repair_order 直接暴露给 HTTP |
| [app/m3/service.py](../../app/m3/service.py) | 创建仍用 BEGIN IMMEDIATE；`list_my_orders` / `read_order` 用只读连接 + BEGIN，在同一快照内检查 ACTIVE、真实权限并查询。`_require_active_user`、`_permissions_for` 分离身份有效性与权限；`_require_reporter` 保留为创建入口。房间规则集中在 `reportable_rooms` |
| 上述 service / repository 的派单入口 | `dispatch_queue` / `list_repairers` 只读事务；`assign_order` 写事务。`eligible_repairers` 统一人员资格；`assign_reported_order` 只更新 id/status 匹配记录，调用者检查 rowcount 并提交。派单相关 `_schema_ready(..., assignment=True)` 额外检查 role 表 |
| 上述 service / repository 的受理/开始入口 | `assigned_orders` / `list_assigned_orders` 同一只读快照授权并按本人 SQL 过滤；`start_repair` 写事务，`find_start_target` 只取 id/status/assigned_to，`start_assigned_order` 条件更新。开始操作不复用详情读取或派单候选资格 |
| [app/m3/identity.py](../../app/m3/identity.py) | `authenticated_reporter(request)`：唯一真实身份接入入口，仅提取服务端用户 ID，不接受请求身份参数 |
| [app/m3/models.py](../../app/m3/models.py) / [app/m3/errors.py](../../app/m3/errors.py) / [app/m3/router.py](../../app/m3/router.py) | 严格创建模型、路径 ID 校验、M3 专属错误转换及路由；动态 work-orders/{order_id} 排在静态路径之后，没有全局 handler 改动 |
| [web/templates/m3/report.html](../../web/templates/m3/report.html) / [report.js](../../web/assets/m3/report.js) / [report.css](../../web/assets/m3/report.css) | 房间表单；复用公共 CSS 和静态资源挂载，失败保留输入，结果不明时禁止直接重发 |
| [my-orders.html](../../web/templates/m3/my-orders.html) / [order-detail.html](../../web/templates/m3/order-detail.html) / [orders.js](../../web/assets/m3/orders.js) / [orders.css](../../web/assets/m3/orders.css) | 本人列表与详情；安全文本、保留正文换行、北京时间、空/加载/失败状态。刷新鉴权失败时清除上次正文 |
| [dispatch.html](../../web/templates/m3/dispatch.html) / [dispatch.js](../../web/assets/m3/dispatch.js) / [dispatch.css](../../web/assets/m3/dispatch.css) / [time.js](../../web/assets/m3/time.js) | 管理队列、状态筛选、带 label 的派单表单；time.js 从原查询页提取，查询与派单共用北京时间转换，没有新增依赖 |
| [assigned.html](../../web/templates/m3/assigned.html) / [assigned.js](../../web/assets/m3/assigned.js) | 本人受理列表、筛选和开始按钮；复用 orders.css/time.js，四张既有 M3 页面新增入口。无浏览器身份开关 |
| [tests/m3/conftest.py](../../tests/m3/conftest.py) | 临时迁移组装及真实共享数据夹具；只在 pytest 临时目录使用 V1 + 临时 V2，无正式版本占号 |
| [app/bootstrap.py](../../app/bootstrap.py) / [app/common/db.py](../../app/common/db.py) | 复用 `initialize_database(..., migrations_dir=...)` 及 `connect_database`，没有修改公共实现 |

低层 repository 保留 `ValueError` / `sqlite3.IntegrityError` / `sqlite3.OperationalError`，不偷偷修库；005 创建服务与 M3Route 将明确输入/身份/依赖错误转换为下面的响应。未知数据库或代码异常记录服务端日志并返回不含内部细节的 500，不能一律伪装成 422/503。

## 实际接口与身份接入

- GET `/m3/report`：公开静态表单，加载房间失败时禁用提交；只有当前应用挂载 `/m2/login` 且 API 返回 401 才显示登录链接，无自动跳转。
- GET `/m3/rooms`：需要有效身份和数据库中的 `repair:report`，返回 `{"items":[{"id":10,"name":"测试教室","is_active":1},{"id":20,"name":"测试停借教室","is_active":0}]}`（此处为虚构示例，实际列表查询真实 room）。
- POST `/m3/work-orders`：只接受 `{"room_id":10,"fault_type":"ELECTRICAL","description":"第一排灯管闪烁"}`。成功提交后返回 **201**，例如 `{"id":1,"status":"REPORTED","created_at":"2026-11-18T09:00:00Z"}`；不提供幂等承诺。
- GET `/m3/work-orders`：ACTIVE + `repair:read_own`；SQL 固定过滤当前 reporter_id，管理员同样只看本人。按 `created_at DESC, id DESC` 排序，不分页；拒绝所有查询参数，包括 reporter_id。例如 `{"items":[{"id":1,"room_id":10,"room_name":"测试教室","fault_type":"ELECTRICAL","status":"REPORTED","created_at":"2026-11-18T09:00:00Z"}],"total":1}`；无记录为 `{"items":[],"total":0}`。
- GET `/m3/work-orders/{order_id}`：先 ACTIVE，再检查下表权限，然后才查询对象；只返回 `id, reporter_id, room_id, room_name, fault_type, description, status, assigned_to, assigned_by, assigned_at, started_at, created_at, updated_at`。REPORTED 工单四个派单/维修字段为 null，不输出密码、会话或整行用户信息。ASCII 十进制正整数允许前导零；非法值 422，超出 SQLite INTEGER 范围视为不存在，不发生转换溢出。
- GET `/m3/my-orders`、`/m3/orders/{order_id}`：公开页面外壳，不嵌入私有工单，数据由上述受控 API 加载。分类/状态为中文，所有详情及列表时间固定转换为北京时间；正文 textContent + pre-wrap。报修页提供“我的工单”，仅在 201 明确返回 ID 后显示本次详情链接。结果不明时可手动核对列表，不自动重发或认领最新工单。

详情读取规则（模块暂定，公共契约仍待整合人员确认）：

| 实际数据库权限 | 可读取范围 |
|---|---|
| repair:assign | 管理范围，允许读取任意工单 |
| repair:read_own | 仅 reporter_id 等于当前用户 |
| repair:read_assigned | 仅 assigned_to 等于当前用户 |
| 以上权限均无 | 403，不先查目标工单 |

多个权限取允许范围的并集；仅 repair:report 不允许读取，仅读取者不必有 report。身份、权限、工单使用同一只读连接与 BEGIN 事务，不跨连接授权/取数，也不取得 BEGIN IMMEDIATE 写锁。

### 手动派单（007）

- GET `/m3/work-orders/dispatch?status=REPORTED`：ACTIVE + repair:assign，默认 REPORTED，只允许 REPORTED/ASSIGNED/IN_REPAIR。静态路由注册在动态 ID 之前；SQL 按 created_at DESC、id DESC，返回 `{"items":[],"total":0}` 或真实队列。每项白名单为 `id, room_id, room_name, fault_type, status, created_at, assigned_to, assigned_at, detail_url`，不含完整用户记录。原本人列表保持本人范围。
- GET `/m3/repairers`：同样要求 ACTIVE + repair:assign。例如 `{"items":[{"id":4,"display_name":"虚构维修员"}]}`；实际读取共享表。候选必须 ACTIVE、拥有 repairer 角色且具有 repair:start；角色与权限为独立 EXISTS 条件，start 可来自该用户其他合法角色。按 display_name、id 排序且去重，候选和提交复用 `repository.eligible_repairers`。
- POST `/m3/work-orders/{order_id}/assign`：只接收 `{"assigned_to":4}`，严格正整数，拒绝 bool/小数/数字字符串、缺失值和额外字段。操作者只要求 ACTIVE + repair:assign，不要求 report/read_own/start，不按 admin 名称自动放行。
- 成功 **200** 返回与详情相同的 13 个白名单字段，例如 `{"id":1,"reporter_id":1,"room_id":10,"room_name":"虚构教室","fault_type":"OTHER","description":"灯管闪烁","status":"ASSIGNED","assigned_to":4,"assigned_by":3,"assigned_at":"2026-11-18T15:00:00Z","started_at":null,"created_at":"2026-11-18T14:00:00Z","updated_at":"2026-11-18T15:00:00Z"}`。示例不代表真实用户/实际操作。
- 同一连接 `BEGIN IMMEDIATE` 内先复核操作者 ACTIVE/assign，再查工单存在性和 REPORTED 状态，再复核目标资格，执行 `WHERE id=? AND status='REPORTED'` 的 UPDATE，要求 rowcount=1，并读取更新结果。成功提交后才返回。assigned_by 使用真实服务端身份，assigned_at/updated_at 取同一个服务端 UTC 值；started_at 保持 NULL，其余原字段不变。
- 未知工单 404；已派单/维修中/重复请求或条件更新未命中 409 conflict；非法目标 422 invalid_repairer。超大路径 ID 按不存在处理，超大目标按非法资格处理，不绑定溢出。更新及提交错误回滚全部字段，真实锁超时 503 database_busy，未知错误 500；不把未知 SQL 故障伪装为输入错误。队列/候选只读 BEGIN，不取写锁，不写共享表。
- GET `/m3/dispatch` 为公开页面壳，现有 M3 导航提供入口。队列/候选加载后仍由服务端重新授权；提交中禁用重复操作，成功/409 刷新队列，422 刷新候选；网络结果不明仅链接原工单详情核对，同一页面不会自动重发或再次提交。重新加载鉴权失败清除旧队列、候选和详情入口；没有浏览器测试身份开关。

M3-R02 的以上模块契约仍为暂定方案；真实登录、正式授权与公共迁移联调必须另行验收。原 PR #1 的通用 state_rules 已经 #12 合入，但尚未接入 `service.assign_order`。后续函数复用仍须保留事务内复核、条件 UPDATE 和 rowcount 检查。

### 本人受理与开始维修（008）

- GET `/m3/work-orders/assigned`：ACTIVE + repair:read_assigned，同一只读连接/BEGIN 中授权并查询，SQL 固定 assigned_to=当前用户，管理员同样仅本人。默认全部，可选 `?status=ASSIGNED` 或 `IN_REPAIR`；其他参数、空/非法状态或重复 status 均 422。按 created_at DESC、id DESC，无分页；静态路径先于动态 ID。
- 返回 `{"items":[],"total":0}` 或真实列表。每项白名单为 `id, room_id, room_name, fault_type, status, created_at, assigned_at, started_at, updated_at, can_start`。示例：`{"items":[{"id":1,"room_id":10,"room_name":"虚构教室","fault_type":"OTHER","status":"ASSIGNED","created_at":"2026-11-18T15:00:00Z","assigned_at":"2026-11-18T15:00:00Z","started_at":null,"updated_at":"2026-11-18T15:00:00Z","can_start":true}],"total":1}`。can_start 仅代表读取时具有 start 且状态为 ASSIGNED；列表不要求 start。
- POST `/m3/work-orders/{order_id}/start`：必须显式发送 `{}`，不接受任何字段、缺失体或非对象。身份来自原适配入口。**开始只要求 ACTIVE + repair:start + assigned_to 为本人，不要求 repairer 角色或任一读取/报修/派单权限**；派单时的候选资格是独立约束，不能直接套用，也没有 admin 绕过。
- 同一 BEGIN IMMEDIATE 内依次验证用户与 start 权限（401/403，先于目标查询）、解析 ID/查询存在性（404）、本人受理（403）、ASSIGNED 状态（409），然后执行 `WHERE id=? AND status='ASSIGNED' AND assigned_to=?` 更新并要求 rowcount=1。REPORTED 因 assigned_to 为 NULL 按对象授权拒绝 403，不构造不合法状态记录。
- 只改 status=IN_REPAIR、started_at、updated_at；两时间为同一个服务端 UTC 秒值，允许与派单/创建时间相同。派单字段、created_at 和正文保持原样。成功提交后 **200** 最小摘要，例如 `{"id":1,"status":"IN_REPAIR","started_at":"2026-11-18T15:00:00Z","updated_at":"2026-11-18T15:00:00Z"}`；没有读取权限的用户不会因此获得完整详情。超大 ID 404；未知异常 500、真实锁超时 503，更新/提交失败全部回滚。
- GET `/m3/assigned` 是公开壳，数据与写操作均鉴权；页面显示只读记录、筛选、详情链接、北京时间，仅 can_start 的 ASSIGNED 显示按钮。提交中禁止重复；成功更新当前列表的状态/开始时间，筛选 ASSIGNED 时移出；409 重新查询，鉴权失败清除私有内容和操作入口。结果不明不自动重发，即使手动查询仍不会重发同一条结果不明的请求，提示核对当前状态。
- 原 PR #1 的通用状态规则已经 #12 合入，但 `service.start_repair` 尚未调用它。后续可在对象授权后、状态检查处复用该函数；事务内重查、对象授权、条件 UPDATE 与 rowcount 不能移除。008 的原实现及本次接收均未安装正式 M3 迁移或授权。

错误形状统一为 `{"error":"<code>","message":"<中文说明>"}`，仅作用于上述 M3 路由：

| 状态 | error / 场景 |
|---|---|
| 401 | `unauthenticated`：没有有效会话，或事务内发现用户不存在/已禁用 |
| 403 | `forbidden`：缺少对应功能权限（report/read_own/read_assigned/assign/start）；开始操作不是实际受理人。详情仍按独立权限矩阵 |
| 404 | `not_found`：详情不可见/不存在、派单或开始目标不存在均用 `{"error":"not_found","message":"工单不存在或不可访问"}`。开始操作按本批明确规则对存在但非本人受理返回 403，不返回正文 |
| 409 | `conflict`：派单非 REPORTED、开始非 ASSIGNED 或相应条件更新未命中，不覆盖首次派单/开始时间 |
| 422 | `invalid_request`：类型/字段、状态筛选或路径 ID 错误；`unknown_room`：房间不存在；`invalid_repairer`：目标不满足派单资格。派单提示 assigned_to 格式，开始提示必须空 JSON 对象，不输出原始输入 |
| 503 | `auth_unavailable`：指定 G2 认证模块未安装；`storage_unavailable` / `schema_unavailable`：本模块明确检查到库/必需表未准备；`database_busy`：真实锁竞争；`dependency_unavailable`：G2 明确返回 503 |
| 500 | `internal_error`：未知数据库/代码故障，不向客户端泄漏 SQL、库路径或堆栈 |

接入 G2 的具体步骤（整合人员）：

1. 按固定参考提交核对 `app.d.auth.dependencies.current_user(request)` 的同步调用及 `SessionUser.id` 契约。M3 当前按请求懒加载此入口；只有 `app.d.auth` / `app.d.auth.dependencies` 本身缺失才是 503，传递依赖损坏为 500，不导致整个应用导入失败。若 G2 改为额外 Depends/异步签名，只修改 `identity.py` 适配，不散落到页面。
2. 接入 G2 的真实会话实现及现有应用装配，保留 `campus_session` 的服务端验证；参考提交的认证路由挂在 `/m2/auth/login`、`/m2/auth/logout`、`/m2/auth/me`，页面为 `/m2/login`。M3 不复制密码、Cookie 或登录代码，也不从自定义用户 ID 请求头取身份。
3. 在同一个配置数据库应用正式迁移和授权初始化。`require_permission` 的认证时权限快照不能替代事务内复核；当前 `service._require_active_user` / `_permissions_for` 只读 `app_user`、`user_role`、`role_permission`、`permission`。未来共享层提供同连接校验能力时集中替换，保留创建与读取权限的独立要求。
4. 移除测试边界替换后，用真实会话进行创建 201、查询 200、401/403/相同 404、撤权/禁用和事务验收。当前测试 `dependency_overrides` 仅在 `tests/m3/` 中装配，不是应用配置开关，不能部署为正常路径兜底。

## 外部依赖与固定测试快照

共享业务迁移尚未合入，M3 测试继续采用仓库 `lyjlyjlyjly/campus-seat-reservation`、提交 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042` 的原始 [database/migrations/V1__init.sql](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/database/migrations/V1__init.sql)，逐字节保存为 [tests/m3/fixtures/V1__init.sql](../../tests/m3/fixtures/V1__init.sql)。**只供测试，不是第二份正式 V1**；没有将其复制到公共迁移目录，也未复制 M2 业务实现或手写假用户/房间表。

- 源 schema 版本：1；大小：3588 字节；Git blob：`9e811019bda02bb8a2fefac2712ec1fe6fb96a61`。
- SHA-256：`a23f6dbaed498d2bfda0d5942306a6d3535b8bf8f724ed0401474ac57259d319`。测试组装前实际校验，根 `.gitattributes` 保持 SQL 为 LF；更新依赖须重新记录来源及校验，不能静默改快照。
- 只读字段：`app_user(id, status, display_name)`（ACTIVE 有效）；`role(id, code)`、`permission(id, code)`、`user_role(user_id, role_id)`、`role_permission(role_id, permission_id)`；`room(id, name, is_active)`，capacity 是共享字段但不参与 M3 资格校验。候选要求 role.code=repairer，权限按实际角色组合查询。工单的 reporter/assignee/assigner 引用真实 app_user，room_id 引用真实 room；ON DELETE RESTRICT 保留历史。外键不能代替身份、ACTIVE、功能权限或对象授权。
- 认证参考同提交的 [app/d/auth/dependencies.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/dependencies.py)：`current_user`、`require_permission(code)`；[app/d/auth/users.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/users.py)：`SessionUser(id, username, display_name, roles, permissions)`，会话 Cookie 为 campus_session。这些认证实现尚未合入当前 main，也没有完成 M3 真实登录联调。
- 当前共享读取集中在 `identity.authenticated_reporter`、`service._require_active_user` / `_permissions_for` 与 `service.reportable_rooms`。不修改共享身份、授权或空间数据；五个 M3 权限仅在测试临时库初始化，正式初始化仍由整合人员执行。

## 暂定规则与可调整位置

- 首阶段仅房间报修。**is_active=0 暂按“停借但资产仍存在”处理，允许报修**；列表和创建均调用 `service.reportable_rooms`，前端显示停借标记；改变含义时只在该入口调整并补测试。capacity 不限制报修，不写 room/M1 表；座位仍未实现。
- 分类为 ELECTRICAL（电气故障）、WATER（给排水故障）、FURNITURE（家具故障）、OTHER（其他故障）。`models.ReportCreate` 严格类型、禁止额外字段，strip 后检查分类和描述；SQL 同时兜底。原 PR #2 的宽松函数已经 #13 合入，但规范化仍由模型自身执行。后续在 validator 内复用该函数时须保留当前分类/长度限制，不修改通用函数的原约定。
- 描述保存 strip 后的 1–1000 个 Unicode 码点，中文/非 BMP 字符按字符而非 UTF-8 字节计数；保留正文内部空白，不截断、不做额外 Unicode 合并。SQL 显式列出与 Python 3.10 strip 一致的空白字符，直接写入未规范化文本也拒绝。升级 Python 时须复核该集合。
- **当前创建与存储边界：拒绝描述中的 U+0000（NUL）**。SQLite length(TEXT) 在它之前停止计数，会与 Python len 产生偏差，因此 SQL 用 instr 排除；这会拒绝含 NUL 的输入。独立 `report_validation` 函数仍可接受该字符串，限制由模型和存储层执行。
- 005 进一步拒绝 JSON 中不能编码为 UTF-8 的孤立代理码点，返回 422 而非把编码错误带入数据库。前端同样按 Python 空白集合规范化并用 `Array.from` 计码点，未设置按 UTF-16 计数的 maxlength，也不截断正文。结果不明不自动重发 POST，并阻止再次提交，提示先核实已有工单。
- REPORTED：assigned_to、assigned_by、assigned_at、started_at 全部 IS NULL；ASSIGNED：前三项 IS NOT NULL、started_at IS NULL；IN_REPAIR：四项全 IS NOT NULL。status 自身 NOT NULL 且限三值。数据库约束只保证字段组合；007/008 已实现派单/开始的事务内重查和条件更新。后续复用 `state_rules` 不能替代事务与操作者授权。
- created_at/updated_at 由 repository 生成 UTC `YYYY-MM-DDTHH:MM:SSZ`，初始相同。数据库外键不代替真实认证、ACTIVE/角色检查、对象授权或后续并发更新检查。

沿用五权限提案，初始化及最终授权由整合人员与 G2 处理：

| 权限 | 暂定授权 |
|---|---|
| repair:report、repair:read_own | student、teacher、org_leader、approver、repairer、admin；本人报修/本人查询 |
| repair:assign | admin；管理派单 |
| repair:read_assigned、repair:start | repairer；仅本人受理工单，开始时须 ASSIGNED |

派单目标资格暂定为 ACTIVE + repairer + repair:start，普通 admin 不自动成为合法受理人。008 开始操作仅要求 ACTIVE + start + 实际受理人，不额外复核 repairer 角色或要求 read_assigned；仅读取者也不必有 start。006 详情和本人列表的原权限/范围保持独立。

## 正式接入步骤与责任

1. 整合人员核对最新 main 的完整迁移历史、用户/角色/房间实际字段及共享认证入口。已有正式迁移时优先使用它们验证，不把测试快照拷回公共目录，不修改已提交 V1；与当前快照不同的部分显式适配并补测试。
2. 分配真实新迁移编号和编写人，将已经验证的 M3 SQL **迁入公共迁移目录**。同一接入变更删除 `app/m3/sql/repair_order.sql` 的副本并更新本文件、测试 SQL 引用，明确公共版本迁移是唯一维护位置，避免双份 SQL 分叉。之后 schema 变化新增版本，不重写已提交迁移。
3. 测试改为组合正式完整迁移历史，移除对旧快照的运行依赖；核验空库、旧库升级、重复执行、真实数据保留和所有约束，不能仅改预期版本号使测试通过。具体修改 `tests/m3/conftest.py` 的 M3_SQL、migrations_dir/v1_database/database 夹具，以及 `tests/m3/test_schema.py` 的版本/升级断言；正式初始化权限后，还要让 M3 测试权限装配按角色/权限 code 解析实际 ID，不能继续假定权限表为空或硬编码 ID 未被占用。
4. 权限初始化由迁移/整合负责人按 G2 确认的五权限映射写入正式后续版本，保留原 room 授权；不由 M3 请求写授权表。共享测试由其负责人调整，具体位置如下；M3 不替其他成员直接修改。
5. 005–008 已实现创建、查询、手动派单和开始维修，正式接入时完成上述 G2 装配和真实会话验收；008 本身没有新增表或迁移。核对 repairer/五权限初始化，保留派单资格与开始权限的区别。核对 M3Route 在共享错误处理器存在时保持局部响应及派单/开始各自校验提示，避免双层包装。需求基线依据实际合入及验证证据维护，分别记录模块能力、公共接入和人工验收，不能仅凭代码合入就宣布整条业务链已交付。

| 测试位置 / 责任 | 正式接入时调整与保留 |
|---|---|
| 固定参考提交的 [tests/d/test_auth_schema.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/tests/d/test_auth_schema.py)，G2 / 迁移负责人 | `test_d_r03_seed_runs_twice_without_duplicates` 的正式版本=1、permission=2、role_permission=4；固定授权测试的全表四行，以及 student 的 rows==[]。改为核对正式迁移、完整获准映射及幂等；仍断言原 room:apply/room:approve 授权不扩大，student 不能 room:apply。该文件尚不在 008 中 |
| [tests/m3/conftest.py](../../tests/m3/conftest.py)、[test_schema.py](../../tests/m3/test_schema.py)、[test_report_create.py](../../tests/m3/test_report_create.py) 及各 API 权限夹具，M3 / 整合人员 | 用正式迁移源验证空库/旧库升级，保留真实共享数据逐行比较、外键、非法状态组合、只缺共享依赖时的拒绝用例；测试账号及特定权限组合仍只写临时库 |
| [tests/test_app.py](../../tests/test_app.py)、[tests/test_bootstrap.py](../../tests/test_bootstrap.py)，共享测试负责人 | 这里的 0/1/2 多数来自显式临时探针迁移，不能因正式版本增加就全局替换数字。保留空迁移、事务回滚、健康检查报告实际版本的语义；真实基线测试另覆盖正式历史 |

### 需求追踪的记录口径

需求状态由 [docs/requirements.md](../requirements.md) 维护，当前结构与依赖由 [docs/architecture.md](../architecture.md) 维护。整合人员与 G1 汇总人按本文件的实际合入和验收证据更新这两个入口；M3 路由已有实现与默认 schema 仍为 0 可以同时成立，不能继续笼统记成“所有业务路由为空”，也不能据此将公共初始化标成已完成。

| 追踪项 | 应写入的事实与证据 |
|---|---|
| M3-R01 | 房间文字创建、持久化及本人列表/详情对应 004/005/006，实际新 PR 与接收状态见前表；公共集成验收通过后再填该层结果。座位仍未实现，不能整项完成 |
| M3-R02 | 007 提供手动派单模块，历史测试见该批 spec，本次 CI 见整合 PR；真实登录、候选资格与并发/重复拒绝的公共整合验收仍需单独记录 |
| M3-R03（首阶段） | 008 提供 ASSIGNED → IN_REPAIR 及模块流程，历史测试与本次整合 CI 分别引用；待验收/完成/退回等仍延期，不标记全部状态流转完成 |
| D-R01 / D-R02 / D-R03 / D-R04 | 分别由认证、权限、空间/迁移及公共页面负责人记录真实接入、初始化和页面验收。M3 只提供依赖及本模块证据，不据此宣称公共层整体完成 |
| 行为与故意破坏实验、schema 演进演示 | 引用 [006 spec](../specs/M3-LOCAL-006-order-queries.md) 的隔离破坏→失败→恢复记录；正式空库重放/旧库升级须补整合记录，不能用模块临时 V2 预占或代替正式演进 |
| M3-R04/R05/R06 及 R01 座位、R03 后续状态 | 保留延期范围和原因；本轮没有超时、评价、M1 联动或座位实现 |

## 可复现验证与接入后清单

在项目根目录 PowerShell 执行（仅写 pytest 临时库，不初始化默认开发库）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/m3/test_schema.py tests/m3/test_repository.py -q
.\.venv\Scripts\python.exe -m pytest tests/m3 -q
.\.venv\Scripts\python.exe scripts/ci.py
node --test tests/m3/report_page.test.cjs tests/m3/order_pages.test.cjs tests/m3/dispatch_page.test.cjs tests/m3/assigned_page.test.cjs
```

004–008 在 2026-11-12、2026-11-18 的历史测试结果分别见各批 spec；006 的隔离规则破坏实验保留原日期和结果，本次没有重复该实验。2026-11-24 的 009 仅复核文档与原记录，没有重跑整套业务测试。上面的命令是复现入口，不表示 LOCAL-010 已在本地执行。

本次新整合 SHA 的远端 CI 结果见前表及 #21 的两次运行链接。LOCAL-010 本地检查范围为 Python 编译、Git 门禁/差异、Note 和文档链接；行为测试仅由远端自动 CI 执行。整合中对现有缺认证用例显式模拟外部认证模块未安装，对页面用例显式隔离外部 `/m2/login` 路由；原有 401/503、页面 false/true 和真实数据库断言保留。真实 `authenticated_reporter`、M3Route、SQL 与事务仍执行，未用业务替身替代结果，也没有把这些模块用例称为共享登录联调。

Node 页面检查使用标准库，无 npm 依赖。本次未运行 Node 页面测试，远端 CI 也未包含 Node；历史 Node 结果仅对应原版本。

HTTP 启动检查和浏览器工具可用性记录见 008 spec。HTTP 200、HTML 断言和 DOM 替身测试均不等于浏览器交互验收；真实共享登录、公共正式迁移的联合验收仍未执行。

008 在 2026-11-18 的记录显示：本人受理列表、开始操作及模块内报修→派单→维修中流程通过；具体命令、数量及 HTTP/浏览器工具证据保留在 008 spec。该流程使用真实权限/SQL/事务及测试外部身份边界，不是共享登录联调。当时浏览器工具 native pipe 不可用，两个临时 HTTP 服务随后停止；这些是历史环境记录，不推定当前工具或进程状态。真实浏览器验收仍待完成。009 的源码哈希与文档复核记录保留在 009 spec，不改记为本次重新执行。

本机查看页面：在项目根目录运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`，打开 `http://127.0.0.1:8000/m3/assigned`，其余 M3 页面导航也可进入。当前正常基线必须显示认证未接入、拒绝数据读取及提交，不提供演示身份开关。正向模块行为可复现 `.\.venv\Scripts\python.exe -m pytest tests/m3/test_start_repair.py -q`；真实浏览器报修→派单→开始需完成上述登录、授权和正式迁移后再验收。

测试使用真实 SQL/初始化器/连接，不 mock 数据库；fixture 的虚构用户没有登录用途，既有 M2 申请记录只存在于临时库中，用于证明升级未破坏业务数据。临时故障触发器仅用于证明 repository 事务回滚，不进入应用 SQL。

### 公共整合与浏览器验收（以下均待执行）

前置条件：整合人员已复核 PR 目标与完整差异，接入 G2 真正的会话及应用装配、正式迁移和获准的五权限映射，更新上述测试夹具。使用专用验收库和虚构但**可以真实登录**的账号 R1/R2（报修人）、A（派单人员）、T1/T2（维修人员），另备仅读取、仅开始或无权限的隔离验收账号/角色组合。不得启用 dependency_overrides、请求用户 ID 或浏览器假登录开关；不在默认开发库做故障实验。

正式迁移接入后，在项目根的新 PowerShell 窗口创建专用空库并重复初始化（**尚未执行公共整合验收**；当前默认迁移目录不会自动安装 M3，不能提前据此宣布验收通过）：

```powershell
$m3CheckDir = Join-Path $env:TEMP ("m3-integration-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $m3CheckDir | Out-Null
$m3CheckDb = Join-Path $m3CheckDir "empty.sqlite3"
.\.venv\Scripts\python.exe -m app.bootstrap --database $m3CheckDb
.\.venv\Scripts\python.exe -m app.bootstrap --database $m3CheckDb
```

确认正式种子包含获准的虚构账号/房间后，再显式执行 `--database $m3CheckDb --seed`；pytest 用户不能登录，不可用它们代替真实账号。端口空闲时启动：

```powershell
$env:CAMPUS_DATABASE_PATH = $m3CheckDb
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

结束时在该窗口 Ctrl+C 停止本次服务并关闭窗口，不处理其他进程或递归清理临时库。下表使用独立浏览器会话登录 `http://127.0.0.1:8000/m2/login`；边界请求使用当前登录会话的同源请求，不传伪造身份。

| 状态 / 验收项 | 执行步骤（前置条件） | 预期与应保留证据 |
|---|---|---|
| 待执行：正式空库与重复迁移 | 重放正式历史两次；检查 user_version、外键和工单表；运行已切换正式迁移源的 schema/repository 测试 | 版本等于实际最高正式版本，第二次不重复迁移或丢数据；工单为空；非法外键、分类、长度、NUL、NULL 状态/字段组合仍拒绝 |
| 待执行：旧库升级 | 在旧基线专用库保存用户、房间和合法 M2 业务记录；停止写入取得一致备份，将副本放入验收目录。逐表保存原行，向副本执行 `python -m app.bootstrap --database <副本绝对路径>` 两次 | 用户/房间/M2 原行业务值逐项保留，原权限不丢失；新增授权符合批准映射。升级后经真实接口建单再初始化，工单也保留；记录版本、比较结果和命令 |
| 待执行：真实身份及权限 | 通过 G2 登录 R1/A/T1，确认服务端会话；退出后请求 API。核对五权限及角色映射，重复授权初始化 | 有效用户通过；未登录/失效会话 401，ACTIVE 但缺功能权限 403，缺依赖 503；无自动授权、假身份或重复映射。记录账号代号与结果，不记录令牌/密码 |
| 待执行：房间报修 | R1 在 `/m3/report` 选择普通/停借房间提交；测试空白、未知房间/分类、额外 reporter_id/seat_id、描述 1/1000/1001、中文/非 BMP/换行/NUL | 合法 201，新连接读到本人名下 REPORTED、四个派单/维修字段 NULL；停借房间按暂定规则允许。非法 422 且工单数不增，服务端决定身份/时间 |
| 待执行：本人列表与详情 | R1/R2/A 各建单，分别打开 `/m3/my-orders`，请求他人工单及不存在 ID；测试仅 report、仅读取及空账号 | 列表仅本人、稳定倒序/正常空列表；仅 report 查询 403，仅读取不要求 report。无管理范围者越权和不存在详情均相同 404；A 详情按 assign 权限、列表仍仅本人 |
| 待执行：派单资格 | A 在 `/m3/dispatch` 把 R1 工单派给 T1；尝试不存在、禁用、无 repairer 角色或无 start 权限目标。加载候选后在验收库撤权/移除角色再提交 | 候选只含 ACTIVE + repairer + start；合法 200 / ASSIGNED、assigned_by=A、assigned_to=T1、派单/更新时间相同、started_at NULL。非法目标 422，所有原字段不变；旧候选不能绕过复核 |
| 待执行：本人受理与开始 | 分别给 T1/T2 派单，打开 `/m3/assigned` 并筛选；T1 对本人单 POST `/m3/work-orders/{id}/start`，体为 `{}`；T2/A 尝试代操作 | 列表只含本人受理。仅 read_assigned 可查不能开始；仅 start 的实际受理人可开始但不能隐式读详情；缺 start 为 403，有 start 的非受理人仍 403。合法 200 只四字段摘要、IN_REPAIR、两时间相同，原派单和正文不变 |
| 待执行：重复、撤权及禁用 | 重复派单/开始；加载页面后撤销操作者权限或禁用再提交；从两个真实会话并发操作同一对象；发送非空 start 体及超大 ID | 重复 409、不覆盖首次时间；禁用 401/撤权 403，在新事务中复核；并发最多一次成功，其余 409 或锁超时 503。非法体 422、超大目标 404；REPORTED 开始按对象授权拒绝 |
| 待执行：锁与失败回滚 | 正式迁移夹具适配后运行下方故障回归：独立连接持有锁，测试触发器/延迟外键制造 UPDATE/COMMIT 失败 | 锁 503 database_busy，未知故障 500；包括 updated_at、started_at 的全行及辅助写入均回滚，无 SQL/路径泄漏。故障装置仅在临时测试库 |
| 待执行：真实浏览器 | 逐页操作加载、空/成功/失败和筛选；输入 HTML 字面量、中文、emoji、换行；核对时间与 API UTC+8，触发 401/403、409、422 | HTML 不执行，换行保留、字数按码点；列表/详情/派单/受理显示北京时间，创建回执 UTC 与详情代表同一时刻。错误可读，刷新鉴权失败清除私有工单/操作入口，提交中防重复 |
| 待执行：结果不明 | 专用浏览器让 POST 发出后丢失响应或断网，观察 Network 请求数，再按提示手动查询 | 不自动重发、不先宣称成功/失败；创建不认领最新工单，派单/开始核对原工单。保留无凭据操作记录，Node/HTTP 不能替代本项 |
| 待执行：真实账号流程 | R1 登录报修 → A 派给 T1 → T1 开始 → R1 查详情、A 查 IN_REPAIR 队列；R2/T2 验证隔离 | 同一工单 REPORTED→ASSIGNED→IN_REPAIR，身份与持久化一致，秒级时间允许相等；记录实际整合 SHA、库版本、CI、验收人/时间及未通过项，不预填通过 |

故障回归及模块流程命令（整合后先完成正式迁移夹具适配；仍是模块自动测试，真实账号流程单独执行）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/m3/test_report_create.py tests/m3/test_assignment.py tests/m3/test_start_repair.py -k "lock or failed_real_sql_transaction or real_update or two_" -q
.\.venv\Scripts\python.exe -m pytest tests/m3/test_start_repair.py -k module_flow -q
```

最后运行本节开头的全套 M3、scripts/ci.py 和四个 Node 页面测试，记录整合分支实际数量及对应 SHA，不照搬 008 数量。待验收、完成、退回、重新派单、评价、超时、座位及 M1 联动继续保留后续范围。
