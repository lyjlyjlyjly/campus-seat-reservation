# M3 整合交接（唯一维护入口）

本文件随每个 M3 批次更新；各批 spec 只记录范围、选择及验证并引用这里。当前批次：[M3-LOCAL-005](../specs/M3-LOCAL-005-report-create.md)，持久化基础见 [M3-LOCAL-004](../specs/M3-LOCAL-004-persistence.md)。用户已授权模块按可替换的暂定契约独立开发，不再等待 P/G/S/D 全部回复、共享依赖合入或正式迁移编号；**暂定契约不等于团队批准**，公共接入由固定整合人员负责。

## 当前能力与边界

- **模块创建接口与页面已完成，真实共享登录及公共基线尚未接通。** 005 从 [PR #4](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/4) 的 `m3/local-004-persistence` / `fa5a35b403700e3312a0ffcacb49b72a84d67720` 创建。2026-11-18 发布前核实时 #4 未合并，main 仍为 `d8918bbc`。用户已授权本批 15 个文件的提交、推送、依赖 PR 及向 `lyjlyjlyjly` 请求评审；实际状态以 Git / GitHub 记录为准。人工浏览器验收、真实登录联调和团队评审仍待进行，发布授权不等于验收通过。
- 依赖 PR 顺序：若 #4 仍未合并，005 PR 暂以 `m3/local-004-persistence` 为目标展示本批差异；先合入 #4，再调整 005 目标为 main。不得把整个 M2/infra 分支混入历史。004 原分支不变；模块持久化已验证，正式公共迁移接入待整合。
- [PR #1](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/1) 是基础状态函数，[PR #2](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/2) 是通用文本规范化，[PR #3](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/3) 是整体契约提案；本批未合并、复制或改写这些 PR。正式创建业务接入时复用已经合入的函数。
- 已有三条创建入口、严格请求校验、事务内真实授权及房间读取、表单反馈；自动业务测试仅替换外部身份边界，仍查询真实临时数据库。没有本人列表/详情、派单/开始维修、座位、评价、超时及 M3→M1。repository 本身不提供鉴权，正常路由必须经过身份入口及创建服务；缺少认证时返回 503，不默认登录。
- 不改默认开发库、公共初始化器、已有 V1、共享种子或其他组业务；本分支默认初始化仍不安装 M3 表。

## 实际路径与调用约定

| 入口 | 当前职责 / 后续适配位置 |
|---|---|
| [app/m3/sql/repair_order.sql](../../app/m3/sql/repair_order.sql) | 唯一 M3 SQL 源；字段、四分类、1–1000 Unicode 码点、外键、三状态 NULL 组合及索引；没有版本/事务 PRAGMA |
| [app/m3/repository.py](../../app/m3/repository.py) | `create_repair_order(database_path, *, reporter_id, room_id, fault_type, description) -> int`；`get_repair_order(database_path, order_id) -> dict 或 None`。时间由服务端生成，独立连接、绑定参数、异常回滚、只写 repair_order；读取不隐含对象授权 |
| [app/m3/service.py](../../app/m3/service.py) | `create_report` 在 BEGIN IMMEDIATE 的同连接内检查用户 ACTIVE、真实授权、房间，再调用 `insert_repair_order(connection, ...)`；成功提交后才返回信息。`list_rooms` 和创建共用 `reportable_rooms` 规则 |
| [app/m3/identity.py](../../app/m3/identity.py) | `authenticated_reporter(request)`：唯一真实身份接入入口，仅提取服务端用户 ID，不接受请求身份参数 |
| [app/m3/models.py](../../app/m3/models.py) / [app/m3/errors.py](../../app/m3/errors.py) / [app/m3/router.py](../../app/m3/router.py) | 严格请求模型、M3 专属错误转换、三条路由；没有全局 handler 改动 |
| [web/templates/m3/report.html](../../web/templates/m3/report.html) / [report.js](../../web/assets/m3/report.js) / [report.css](../../web/assets/m3/report.css) | 房间表单；复用公共 CSS 和静态资源挂载，失败保留输入，结果不明时禁止直接重发 |
| [tests/m3/conftest.py](../../tests/m3/conftest.py) | 临时迁移组装及真实共享数据夹具；只在 pytest 临时目录使用 V1 + 临时 V2，无正式版本占号 |
| [app/bootstrap.py](../../app/bootstrap.py) / [app/common/db.py](../../app/common/db.py) | 复用 `initialize_database(..., migrations_dir=...)` 及 `connect_database`，没有修改公共实现 |

低层 repository 保留 `ValueError` / `sqlite3.IntegrityError` / `sqlite3.OperationalError`，不偷偷修库；005 创建服务与 M3Route 将明确输入/身份/依赖错误转换为下面的响应。未知数据库或代码异常记录服务端日志并返回不含内部细节的 500，不能一律伪装成 422/503。

## 实际接口与身份接入

- GET `/m3/report`：公开静态表单，加载房间失败时禁用提交；只有当前应用挂载 `/m2/login` 且 API 返回 401 才显示登录链接，无自动跳转。
- GET `/m3/rooms`：需要有效身份和数据库中的 `repair:report`，返回 `{"items":[{"id":10,"name":"测试教室","is_active":1},{"id":20,"name":"测试停借教室","is_active":0}]}`（此处为虚构示例，实际列表查询真实 room）。
- POST `/m3/work-orders`：只接受 `{"room_id":10,"fault_type":"ELECTRICAL","description":"第一排灯管闪烁"}`。成功提交后返回 **201**，例如 `{"id":1,"status":"REPORTED","created_at":"2026-11-18T09:00:00Z"}`；不提供幂等承诺。

错误形状统一为 `{"error":"<code>","message":"<中文说明>"}`，仅作用于上述 M3 路由：

| 状态 | error / 场景 |
|---|---|
| 401 | `unauthenticated`：没有有效会话，或事务内发现用户不存在/已禁用 |
| 403 | `forbidden`：事务内没有真实 `repair:report` 授权 |
| 422 | `invalid_request`：类型/文本/字段错误；`unknown_room`：房间不存在（超出 SQLite 主键范围也视作不存在） |
| 503 | `auth_unavailable`：指定 G2 认证模块未安装；`storage_unavailable` / `schema_unavailable`：本模块明确检查到库/必需表未准备；`database_busy`：真实锁竞争；`dependency_unavailable`：G2 明确返回 503 |
| 500 | `internal_error`：未知数据库/代码故障，不向客户端泄漏 SQL、库路径或堆栈 |

接入 G2 的具体步骤（整合人员）：

1. 按固定参考提交核对 `app.d.auth.dependencies.current_user(request)` 的同步调用及 `SessionUser.id` 契约。M3 当前按请求懒加载此入口；只有 `app.d.auth` / `app.d.auth.dependencies` 本身缺失才是 503，传递依赖损坏为 500，不导致整个应用导入失败。若 G2 改为额外 Depends/异步签名，只修改 `identity.py` 适配，不散落到页面。
2. 接入 G2 的真实会话实现及现有应用装配，保留 `campus_session` 的服务端验证；参考提交的认证路由挂在 `/m2/auth/login`、`/m2/auth/logout`、`/m2/auth/me`，页面为 `/m2/login`。M3 不复制密码、Cookie 或登录代码，也不从自定义用户 ID 请求头取身份。
3. 在同一个配置数据库应用正式迁移和授权初始化。`require_permission` 的认证时权限快照不能替代写事务内复核；当前 `service._require_reporter` 只读 `app_user`、`user_role`、`role_permission`、`permission`，未来共享层提供同连接校验能力时可集中替换。
4. 移除测试边界替换后，用真实会话进行 401/403/201、撤权/禁用和事务验收。当前测试 `dependency_overrides` 仅在 `tests/m3/` 中装配，不是应用配置开关，不能部署为正常写入兜底。

## 外部依赖与固定测试快照

当前 main 无正式共享业务迁移，采用用户指定仓库 `lyjlyjlyjly/campus-seat-reservation`、提交 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042` 的原始 [database/migrations/V1__init.sql](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/database/migrations/V1__init.sql)，逐字节保存为 [tests/m3/fixtures/V1__init.sql](../../tests/m3/fixtures/V1__init.sql)。**只供测试，不是第二份正式 V1**；未复制 M2 业务实现，也未手写假用户/房间表。

- 源 schema 版本：1；大小：3588 字节；Git blob：`9e811019bda02bb8a2fefac2712ec1fe6fb96a61`。
- SHA-256：`a23f6dbaed498d2bfda0d5942306a6d3535b8bf8f724ed0401474ac57259d319`。测试组装前实际校验，根 `.gitattributes` 保持 SQL 为 LF；更新依赖须重新记录来源及校验，不能静默改快照。
- 依赖字段：`app_user(id, status)` 及既有授权表；`room(id, name, capacity, is_active)`。工单的 reporter/assignee/assigner 引用真实 app_user，room_id 引用真实 room；ON DELETE RESTRICT 保留历史。角色/ACTIVE 校验不是外键保证的能力。
- 认证参考同提交的 [app/d/auth/dependencies.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/dependencies.py)：`current_user`、`require_permission(code)`；[app/d/auth/users.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/users.py)：`SessionUser(id, username, display_name, roles, permissions)`，会话 Cookie 为 campus_session。此代码尚未作为本批真实集成依赖运行。
- 当前只读适配已集中在 `identity.authenticated_reporter`、`service._require_reporter` 与 `service.reportable_rooms`。不修改共享身份、授权或空间数据；只有测试临时库补入 `repair:report` 权限，正式初始化仍由整合人员执行。

## 暂定规则与可调整位置

- 首阶段仅房间报修。**is_active=0 暂按“停借但资产仍存在”处理，允许报修**；列表和创建均调用 `service.reportable_rooms`，前端显示停借标记；改变含义时只在该入口调整并补测试。capacity 不限制报修，不写 room/M1 表；座位仍未实现。
- 分类为 ELECTRICAL（电气故障）、WATER（给排水故障）、FURNITURE（家具故障）、OTHER（其他故障）。`models.ReportCreate` 严格类型、禁止额外字段，strip 后检查分类和描述；SQL 同时兜底。PR #2 未合入，必要规范化暂集中在模型，整合时在其 validator 内复用 PR #2 的宽松函数，再保留当前分类/长度限制，不修改通用函数的原约定。
- 描述保存 strip 后的 1–1000 个 Unicode 码点，中文/非 BMP 字符按字符而非 UTF-8 字节计数；保留正文内部空白，不截断、不做额外 Unicode 合并。SQL 显式列出与 Python 3.10 strip 一致的空白字符，直接写入未规范化文本也拒绝。升级 Python 时须复核该集合。
- **本批技术边界：拒绝描述中的 U+0000（NUL）**。SQLite length(TEXT) 在它之前停止计数，会与 Python len 产生偏差，因此 SQL 用 instr 排除；这会拒绝含 NUL 的输入，PR #2 本身仍可接受该字符串，限制只在存储/后续创建业务层生效。
- 005 进一步拒绝 JSON 中不能编码为 UTF-8 的孤立代理码点，返回 422 而非把编码错误带入数据库。前端同样按 Python 空白集合规范化并用 `Array.from` 计码点，未设置按 UTF-16 计数的 maxlength，也不截断正文。结果不明不自动重发 POST，并阻止再次提交，提示先核实已有工单。
- REPORTED：assigned_to、assigned_by、assigned_at、started_at 全部 IS NULL；ASSIGNED：前三项 IS NOT NULL、started_at IS NULL；IN_REPAIR：四项全 IS NOT NULL。status 自身 NOT NULL 且限三值。数据库约束只保证字段组合，不代表实现了合法状态转换或操作者权限；后续派单/开始维修仍需 PR #1、事务内重查与条件更新。
- created_at/updated_at 由 repository 生成 UTC `YYYY-MM-DDTHH:MM:SSZ`，初始相同。数据库外键不代替真实认证、ACTIVE/角色检查、对象授权或后续并发更新检查。

沿用五权限提案，初始化及最终授权由整合人员与 G2 处理：

| 权限 | 暂定授权 |
|---|---|
| repair:report、repair:read_own | student、teacher、org_leader、approver、repairer、admin；本人报修/本人查询 |
| repair:assign | admin；管理派单 |
| repair:read_assigned、repair:start | repairer；仅本人受理工单，开始时须 ASSIGNED |

维修资格仍为 ACTIVE + repairer + repair:start，普通 admin 不自动获得维修能力。详情暂定未登录 401、缺功能权限 403、具体工单不可见/不存在均同一 404；详情接口尚未实现或验证，不能与本批创建响应混淆。

## 正式接入步骤与责任

1. 整合人员核对最新 main 的完整迁移历史、用户/角色/房间实际字段及共享认证入口。已有正式迁移时优先使用它们验证，不把测试快照拷回公共目录，不修改已提交 V1；与当前快照不同的部分显式适配并补测试。
2. 分配真实新迁移编号和编写人，将已经验证的 M3 SQL **迁入公共迁移目录**。同一接入变更删除 `app/m3/sql/repair_order.sql` 的副本并更新本文件、测试 SQL 引用，明确公共版本迁移是唯一维护位置，避免双份 SQL 分叉。之后 schema 变化新增版本，不重写已提交迁移。
3. 测试改为组合正式完整迁移历史，移除对旧快照的运行依赖；核验空库、旧库升级、重复执行、真实数据保留和所有约束，不能仅改预期版本号使测试通过。
4. 权限初始化由迁移/整合负责人按 G2 确认的五权限映射写入正式后续版本，保留原 room 授权；不由 M3 请求写授权表。共享测试由其负责人调整 `tests/d/test_auth_schema.py` 等“版本固定为 1、权限数 2、全表映射四行、student 完全无权限”的假设，保留原 M2 授权断言；M3 只维护本模块测试。
5. 005 已交模块创建服务、接口与表单，正式接入时完成上述 G2 装配和真实会话验收。核对 M3Route 在共享错误处理器存在时仍保持 M3 响应约定；未来如要统一处理，由整合人员显式替换局部适配，避免双层响应包装。

## 可复现验证与接入后清单

在项目根目录 PowerShell 执行（仅写 pytest 临时库，不初始化默认开发库）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/m3/test_schema.py tests/m3/test_repository.py -q
.\.venv\Scripts\python.exe -m pytest tests/m3 -q
.\.venv\Scripts\python.exe scripts/ci.py
node --test tests/m3/report_page.test.cjs
```

004 的历史结果为 99 项模块 / 187 项完整检查通过，详见其 spec。005 的模块验证为 159 项 Python、6 项 JS 行为检查通过；本地 `scripts/ci.py` 的 Note/编译检查和 247 项测试通过（main 88 + 004 99 + 005 60），详细结果见当前 spec。JS 检查使用本机现有 Node 标准库，无 npm 依赖；现有 CI 仍按 Python 脚本执行，没有改 CI 或假称已在 CI 运行 JS。

本轮正常服务实测：`/m3/report` 200、`/m3/rooms` 503（auth_unavailable）、`/health` 200；临时测试身份服务页面/房间/健康均 200。这是实际 HTTP 启动检查，不是浏览器验收。内置浏览器和 Windows Computer Use 均报本机通信管道缺失，且现有 Playwright 不可用；浏览器交互待人工验收，HTML/JS 测试不代替该项。真实共享登录、公共正式迁移的联合验收仍未执行。

本机查看页面：在项目根目录运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`，打开 `http://127.0.0.1:8000/m3/report`。当前正常基线必须显示登录未接入并禁止提交，不提供演示身份开关。正向业务可先复现 `python -m pytest tests/m3/test_report_create.py -q`（项目虚拟环境）；真实浏览器成功提交需整合上述登录、授权和正式迁移后再验收。

测试使用真实 SQL/初始化器/连接，不 mock 数据库；fixture 的虚构用户没有登录用途，既有 M2 申请记录只存在于临时库中，用于证明升级未破坏业务数据。临时故障触发器仅用于证明 repository 事务回滚，不进入应用 SQL。

整合后的验收清单（目前未完成）：

- [ ] 正式迁移空库/旧库/重复执行均通过，旧用户、房间和 M2 业务记录保留；SQL 只有一处维护来源。
- [ ] 五权限初始化和共享测试按真实基线通过；未知用户/房间及非法 NULL 组合仍被数据库拒绝。
- [ ] 真实登录用户选真实房间提交，201 与数据库本人名下 REPORTED 一致；非法输入、未知房间、未登录及无权限不留工单。
- [ ] 停借房间规则、对象访问响应、服务端身份/时间和失败回滚通过真实接口验收；没有默认登录或测试适配器进入正常路径。
- [ ] 派单/开始维修另批接入事务内资格检查、状态规则及条件更新；当前表结构不等于这些功能交付。
