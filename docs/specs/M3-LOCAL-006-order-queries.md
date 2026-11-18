# M3-LOCAL-006：本人工单列表与详情

## 范围、依赖与授权

2026-11-18 fetch 后，main 仍为 `d8918bbc`；[PR #4](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/4) 与 [PR #5](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/5) 均未合并。本批从 `origin/m3/local-005-report-create` 的 `49892f7e075f5b10ce4d2a2d9bae55b60ea74621` 建立 `m3/local-006-order-queries`；创建前无同编号任务、分支或 PR，工作区干净。依赖分支不修改，不引入 M2/infra 历史。

用户先授权完成本批方案、实现、测试与交接，实施阶段未执行 Git 发布。2026-11-18 随后明确授权基于实际自动验证提交、推送、创建依赖 PR，并向 `lyjlyjlyjly` 请求评审；发布授权不等于人工验收通过。继续模块独立开发，不等待公共依赖或 P/G/S/D 回复，暂定契约不等于团队批准。本批 PR 暂以 `m3/local-005-report-create` 为目标，仅展示本批差异；按 #4 → #5 → 本批的顺序整合，再调整目标、复核差异和 CI。不合并 PR，不开始下一批。

需求关联：M3-R01 报修后的本人查询，以及 M3-R02/R03 工单状态信息的读取；不代表派单、维修或整个需求完成。新增列表/详情 API 与页面，补创建页导航；不实现搜索、分页、导出、派单、维修、验收评价、超时、座位或 M1 联动。

## 方案比较

| 方案 | 取舍 |
|---|---|
| 路由内直接用同一只读连接完成授权及 SQL 查询 | 入口集中、文件较少，但列表/详情的身份和权限逻辑会重复，路由也承担数据查询职责 |
| service 在同一只读事务授权，repository 用绑定参数及 SQL 范围过滤（采用） | 列表只查询本人，详情按权限/对象范围过滤；查询不持有写锁，响应字段显式限定 |

保留 `identity.authenticated_reporter` 接入名；仅将 service 的 ACTIVE 检查与权限加载/具体权限要求分开。创建仍要求 repair:report；列表要求 repair:read_own，管理员也只看本人。详情先检查 ACTIVE，再要求 read_own/read_assigned/assign 至少一个，然后按管理/本人/本人受理范围过滤；不可见和不存在同为 `404 {"error":"not_found","message":"工单不存在或不可访问"}`。

读取采用 `connect_database(..., read_only=True)` + `BEGIN`，不使用 BEGIN IMMEDIATE；SQL 按 `created_at DESC, id DESC` 排序，返回 items/total，不分页。列表拒绝查询参数，不能用 reporter_id 切换身份。路径 ID 只接受 ASCII 十进制正整数（允许前导零）；非法值 422，超出 SQLite 整数范围按不存在处理，避免整数转换/绑定溢出。详情功能权限先于目标查询，未授权者不会探测工单。

两张查询页面复用公共 CSS，M3 原生 JS 使用 textContent，描述保留换行，UTC 固定转换为 Asia/Shanghai。创建明确成功才显示本次详情链接；结果不明时仅提供本人列表入口，不自动重发或认领最新记录。

## 文件范围与交接

- `app/m3/service.py`、`repository.py`、`router.py`、`models.py`：权限拆分、连接内查询、路由及路径校验。
- `web/templates/m3/` 与 `web/assets/m3/`：列表/详情页面脚本样式；现有 report 页导航与成功链接。
- `tests/m3/`：真实 SQLite 查询/权限/只读测试、Node 页面测试及原创建回归。
- 本 spec 与唯一交接入口 [docs/m3/INTEGRATION.md](../m3/INTEGRATION.md)。不修改公共迁移、V1 快照、公共入口、其他模块或默认开发库。

## Given–When–Then 验收

| Given | When | Then |
|---|---|---|
| 两名有 read_own 的 ACTIVE 用户，各有报修 | 查询列表 | 只显示本人，稳定倒序，total 与 items 一致；空列表正常 |
| 管理员有 read_own / assign | 查询列表与他人工单详情 | 列表仅本人；详情按 assign 允许；没有 read_own 时列表仍 403 |
| 本人/受理人/管理权限及不同对象关系 | 查看详情 | 只允许规定组合；不可见/不存在返回完全相同 404 |
| 无功能权限、被禁用/删除或读取权限撤销 | 查询 | 403 / 401，无正文泄漏；仅 report 不放行读取，仅读取不要求 report |
| 非法或超大路径 ID | 查询 | 422 / 404，不产生 500 |
| 另一个连接持有写事务但尚未提交 | 查询 | 只读事务可读取既有快照，不争用写锁、不改变数据库 |
| 房间名/描述含 HTML、中文、换行及 UTC 时间 | 页面渲染 | 安全文本、换行保留、北京时间明确；加载/空/错误/503 状态清楚 |
| 创建成功或结果不明 | 页面反馈 | 成功链接只指向返回 ID；结果不明只引导人工核对列表，不自动重发 |

验证使用既有临时库、真实 V1/M3 SQL 和初始化器；测试仅替换外部身份边界，权限和对象判断不 mock。临时库用合法字段组合构造 ASSIGNED/IN_REPAIR，不实现派单接口。权限前置测试临时重命名正文列，验证无功能权限时先返回 403、不会提前 SELECT 目标正文；只影响测试库。

## 实际验证与验收边界

本轮在既有 Python 3.10.20 虚拟环境执行，无依赖安装或升级：

| 命令 | 实际结果 |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests/m3/test_order_queries.py -q` | 42 passed |
| `.\.venv\Scripts\python.exe -m pytest tests/m3 -q` | 201 passed，含创建及持久化回归 |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note、编译通过；289 passed |
| `node --test tests/m3/report_page.test.cjs tests/m3/order_pages.test.cjs` | 14 passed，含原报修页 6 项与新增查询页 8 项 |

Python 检查均有既有 Starlette/httpx 弃用提示 1 条，未跳过或删除测试，也未为此升级依赖。以上是当前依赖链上的本地检查，不是其他未合并分支的联合验证；Node 是独立本地验证，未加入远端 CI。发布前逐文件 SHA-256 与本地验证记录一致，仅补充本 spec 与交接文件的发布说明，沿用上述结果，不重复运行未改变的业务测试。远端 CI 状态以本次最终提交的 Actions 记录为准，本地结果不代替远端结果；依赖 PR 不匹配现有 main 自动触发条件时，使用已有 workflow_dispatch，不修改共享 CI。

按 AGENTS.md 执行一次真实破坏实验：在本功能分支临时将 `list_owned_orders` 的 `WHERE o.reporter_id = ?` 改为不限定本人的 `WHERE (? IS NOT NULL)`；运行 `test_m3_r01_each_user_gets_only_own_orders_in_stable_order` 得到 **1 failed**（第一名用户得到 7 条而非本人 4 条）。随后逐字节恢复 repository，同一测试 **1 passed**；恢复后 SHA-256 与实验前相同，未保留破坏代码。此实验仅操作当前实现和临时测试库，没有修改默认数据库或依赖分支。

真实 HTTP 启动检查：项目虚拟环境运行 `uvicorn app.main:app --host 127.0.0.1 --port 8767`；首页、health、version、三张 M3 页面和新增 JS/CSS 均为 200。未安装 G2 的正常应用下，GET rooms、GET work-orders、GET work-orders/1 及 POST work-orders 均为 503 / auth_unavailable；正常应用没有测试身份兜底。检查结束停止本轮服务，不改默认开发数据库。

浏览器控制工具本轮重试报 `Computer Use native pipe is unavailable`（系统找不到指定的文件，os error 2）。因此**实际浏览器交互仍待人工验收**；Node 的 DOM/fetch 替身和 HTTP 检查不能代替浏览器操作。真实共享登录、正式迁移及公共权限初始化尚未接通，不能称为真实登录联调通过。

人工验收：按交接文件启动，先在当前基线检查 `/m3/report` → “我的工单” → `/m3/orders/1`，应清楚显示认证依赖不可用，不自动跳转登录或发送写请求。整合真实登录/迁移/权限后，用两名用户验证本人列表、管理员仍只列本人、本人/受理人/管理详情范围、越权与不存在同一 404；检查空列表、换行/HTML 安全文本、北京时间、创建成功详情链接，以及失败后保留输入、结果不明不重发。

交付状态：**模块本人查询接口与页面已实现并通过自动验证，浏览器人工验收和真实公共集成待完成**。本次仅发布本批 15 个文件；团队代码评审待进行，不填写已通过记录，不合并 PR 或继续下一批。实际提交、推送与 PR 状态以 Git / GitHub 为准，实际推送时间另记本地 Git 元数据，不混入提交。
