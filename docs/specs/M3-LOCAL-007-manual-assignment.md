# M3-LOCAL-007：管理员手动派单

## 2026-11-27 整合补充

本批按 [LOCAL-010](LOCAL-010-branch-integration.md) 从 `094f12dfff4f2f827f876ba4afe6f0bf06a16e77` 单独引入；前置本人查询已由 PR #19 合入 main。既有缺认证和无登录页用例显式隔离外部依赖，保留原有 401／503、数据库不变和页面断言，生产代码与来源一致。

本次本地行为测试未运行，自动 CI 结果以整合 PR 和 LOCAL-010 记录为准。以下来源批次的验证、实验和授权记录保留原日期语境，不作为本次重跑或人工验收证据。

## 范围、基线与授权

需求为 M3-R02 的模块手动派单。2026-11-18 fetch 后 main 仍为 `d8918bbc`，[PR #4](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/4)、[PR #5](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/5)、[PR #6](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/6) 均未合并。创建前工作区干净，无同编号分支/spec/PR。本批从 006 的 `e1fbd945251cdcc2cdc0a7d4226caa42f70ad8f0` 建立 `m3/local-007-manual-assignment`，不修改依赖分支。

用户明确授权方案、实现、测试和统一交接，继续模块独立开发，不以公共依赖/P/G/S/D 未确认停工；公共契约仍为暂定，真实接入由整合人员负责。实现阶段未提交或发布；随后用户明确授权按实际模块自动验证结果提交、推送本批并创建依赖 PR、请求 lyjlyjlyjly 评审。发布授权不代表人工浏览器验收通过，不授权合并或开始下一批。本批发布以 006 为目标，按 #4 → #5 → #6 → 本批整合，每次调整目标须复核差异与 CI。

实现管理队列、合法维修人员候选、REPORTED → ASSIGNED 接口和页面。复用现有认证适配、错误处理与真实 SQLite。没有开始维修、重新派单、验收评价、超时、座位或 M1 联动；不改公共迁移、V1 快照、默认开发数据库及共享种子。

## 方案比较与选择

| 方案 | 取舍 |
|---|---|
| 使用带完整授权/资格子查询的一条条件 UPDATE，再查询失败原因 | 写入原子，但失败原因判定和可读性较复杂，资格查询在队列与写入之间容易重复维护 |
| service 的 BEGIN IMMEDIATE 内复核，repository 共用资格查询 + 条件 UPDATE（采用） | 与现有事务边界一致，错误优先级清楚；仍要求 id/status 条件和 rowcount 检查，提交成功后才返回 |

操作者 ACTIVE + repair:assign，不附加 report/read_own/start 或硬编码 admin 放行。维修资格为 ACTIVE + repairer 角色 + repair:start，角色与权限分别用 EXISTS 查询，权限可来自多角色组合，按 display_name、id 稳定排序且不重复。role 表加入派单依赖检查。队列/候选使用只读连接 + BEGIN。

队列默认 REPORTED，status 仅接受三种现有状态，按 created_at DESC、id DESC；静态 dispatch 路由置于动态 ID 路由之前。派单请求只收严格正整数 assigned_to；路径复用既有解析，超大目标/工单 ID 安全拒绝。事务内先操作者权限，再工单存在性/状态，再目标资格，最后执行 `WHERE id=? AND status='REPORTED'` 更新并核对 rowcount。冲突 409，非法目标 422，未知工单 404；锁竞争 503，未知错误 500，全字段回滚。

assigned_by、assigned_at/updated_at 均来自服务端，两个时间取同一 UTC 值；started_at 保持 NULL，其他原字段不变。PR #1 的 state_rules.py 不在基线内，直接实现本批必要检查；未来接入通用状态函数的位置见交接文件，函数不能替代事务或条件更新。

页面公开壳、API 鉴权，原生 JS 安全文本及北京时间。提交时禁止重复操作；成功刷新队列，409 刷新记录，422 刷新候选；结果不明不自动重发，保留详情核对入口并阻止再次派单直到人工刷新核对。重新加载鉴权失败清除旧私有数据。

## 预计文件与验收

- `app/m3/{models,errors,repository,service,router}.py`：严格输入、错误说明、真实查询/更新、事务及路由。
- `web/templates/m3/dispatch.html`、`web/assets/m3/dispatch.js` / `dispatch.css`，现有三张 M3 页面导航；复用北京时间格式函数时仅作必要模块内调整。
- `tests/m3/test_assignment.py`、`tests/m3/dispatch_page.test.cjs`；原创建及查询测试保持回归。
- 本 spec 与唯一 [docs/m3/INTEGRATION.md](../m3/INTEGRATION.md)。006 的破坏实验保留，不重复制造记录。

| Given | When | Then |
|---|---|---|
| ACTIVE + assign 的操作者，各状态真实工单 | 默认/筛选队列 | 仅对应状态、稳定排序、items/total，空队列正常，原本人列表范围不变 |
| ACTIVE、角色及权限不同的人员，多角色组合 | 加载候选及提交 | 仅三个资格条件同时成立者可派单，列表去重，提交重新复核 |
| REPORTED 工单与合法目标 | 派单并用新连接读取 | 200 / ASSIGNED，服务端操作者/时间正确，仅派单字段及 updated_at 改变 |
| 无权限、失效操作者或不存在工单 | 请求 | 403/401 优先于对象查询，合法操作者未知工单 404 |
| 候选加载后资格被撤销、请求伪造或输入非法 | 提交 | 422/401/403，原工单全部字段不变、不泄漏输入 |
| 两个独立连接同时争抢，或重复派单/维修中工单 | 提交 | 最多一次成功；其余 409 或真实锁超时 503，不覆盖获胜者 |
| UPDATE 触发真实错误、rowcount 为 0、提交被锁阻止 | 提交 | 回滚，无部分更新；未知错误 500，锁 503 |
| 页面加载/空/无候选/403/503/409/422/网络不明 | 交互 | 安全文本、清晰状态、正确刷新、不重发、不虚报成功 |

## 实际验证

使用既有项目 Python 3.10.20 虚拟环境和本机 Node，无依赖升级。只替换外部身份边界，真实初始化器/SQL/授权与状态更新不 mock；浏览器人工验收、真实共享登录、正式公共迁移单独记录。

| 实际命令 | 结果 |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests/m3/test_assignment.py -q` | 57 passed |
| `.\.venv\Scripts\python.exe -m pytest tests/m3 -q` | 258 passed，含原创建/本人查询/持久化回归 |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note、编译通过；346 passed |
| `node --test tests/m3/report_page.test.cjs tests/m3/order_pages.test.cjs tests/m3/dispatch_page.test.cjs` | 25 passed：原创建 6、查询 8、派单 11 项 |

Python 均有既有 Starlette/httpx 弃用提示 1 条，未屏蔽或升级依赖；未跳过测试或降低断言。发布前核对源码、页面及测试的 SHA-256，与上述验证记录一致；仅修订本 spec 和交接文件中的发布授权说明，沿用已有测试结果并重新执行 Note、文档链接、空白及差异范围检查。Node 是本地独立验证，未改共享 CI。远端 CI 以最终提交对应的实际运行状态为准；依赖 PR 未自动触发时使用已有 workflow_dispatch，不预先记为通过。006 的破坏实验文档与实现原样保留，不重复实验。

真实数据库验证包括：两个并发 HTTP 测试请求各自打开独立连接，恰好一次成功，其余冲突不覆盖；真实 BEFORE UPDATE IGNORE 的 rowcount=0 返回 409；AFTER UPDATE 触发器失败、延迟外键在 COMMIT 失败均整体回滚；独立连接在 BEGIN 或 COMMIT 制造锁超时均返回 503、所有原字段不变。这些临时触发器/表只用于测试，不进入业务 SQL。

实际 Uvicorn HTTP 检查：

- 正常装配运行在 127.0.0.1:8768：首页、health、version、派单页及新资源、原三张 M3 页面均 200；管理队列、维修候选、派单 POST 均 503 auth_unavailable。
- 仅本地测试装配运行在 127.0.0.1:8769：复用本批 pytest 夹具及临时库，仅替换身份入口。候选/队列 200，非法目标 422，成功派单 200，重复派单 409，默认队列由 3 条变为 2 条；另一连接读到正确受理人、服务端操作者及相同 assigned_at/updated_at。此装配不进入项目业务文件，不等于真实共享登录联调。
- 检查脚本首次使用 Request.method 记录日志时失败，改用 get_method 后重新执行上述 HTTP 检查通过；没有修改业务代码来解决。检查后已停止本轮两项服务，默认库未修改。系统临时目录中的本轮 HTTP 测试库保留，不在提交范围内。

浏览器工具本轮尝试打开临时派单页，报 `Computer Use native pipe is unavailable`（系统找不到指定的文件，os error 2），无法进行真实点击验收。**浏览器交互、真实共享登录、正式迁移及权限初始化仍待验收**；HTML/DOM 替身/HTTP 检查不替代这些验收。

## 人工查看与交付状态

在项目根目录运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`，打开 `http://127.0.0.1:8000/m3/dispatch`。当前正常基线应提示共享认证不可用，禁用派单；原报修、本人列表和详情可导航到派单页。正式接入后依照交接文件，验证有 assign 的用户加载真实候选、筛选队列、选择 REPORTED 工单派单、详情字段和北京时间、重复操作 409、资格变化 422、撤权后清除私有数据及结果不明只人工核对。

交付状态：**M3-R02 模块实现已验证，真实共享登录及公共基线接入待整合，浏览器人工验收待完成。** 不表示团队契约已批准或整个 M3 已完成。本批已获单独发布授权，提交、推送、PR 与 CI 的实际结果以 Git/GitHub 及本地 Git 元数据记录为准；团队评审仍待完成。
