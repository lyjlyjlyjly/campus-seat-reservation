# M3-LOCAL-008：本人受理列表与开始维修

## 范围、基线与授权

对应 M3-R03 首阶段 ASSIGNED → IN_REPAIR，含本人受理列表与页面。用户明确授权本批方案、实现、测试和统一交接，继续模块独立开发；无需等待公共依赖合入或 P/G/S/D 全部确认，暂定契约不表示团队批准。实现阶段未提交或发布；随后用户明确授权依据模块自动验证结果提交、推送、创建独立依赖 PR，并请求 lyjlyjlyjly 评审。发布授权不是人工浏览器验收或公共契约批准，不授权合并 PR 或扩展下一批。

2026-11-18 fetch 后 main 为 `d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b`，PR #4–#7 均未合并，PR #1 也未合并。工作区原本干净，无同编号分支/spec/PR；从 [PR #7](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/7) 的 `094f12dfff4f2f827f876ba4afe6f0bf06a16e77` 创建 `m3/local-008-start-repair`。依赖原分支不变，后续发布暂以 007 为目标；正式整合顺序与公共契约只在 [docs/m3/INTEGRATION.md](../m3/INTEGRATION.md) 维护。

## 方案与选择

| 方案 | 取舍 |
|---|---|
| 复用详情读取或派单候选资格后执行更新 | 代码较少，但会额外要求读取权限/repairer 角色，且容易把完整详情隐式授予只有开始权限的用户，不采用 |
| 独立的连接内最小目标查询 + 事务内对象授权 + 条件更新（采用） | 复用现有身份、权限和连接工具；明确分开功能权限、本人受理与状态判断，提交后只返回四字段摘要 |

列表在只读 BEGIN 内检查 ACTIVE、read_assigned，SQL 固定 assigned_to=当前用户；默认全部，仅可筛选 ASSIGNED/IN_REPAIR。拒绝其他查询参数及重复 status，can_start 仅为本次读取的权限/状态快照，不能代替写入时授权。静态 assigned 路由在动态 ID 之前。

开始请求必须显式发送空 JSON 对象 `{}`。在同一 BEGIN IMMEDIATE 事务内按 ACTIVE → repair:start → 存在性 → 本人受理 → ASSIGNED 顺序检查，再执行 id/status/assigned_to 条件 UPDATE、核对 rowcount。只改 status、started_at、updated_at；两个时间使用同一服务端 UTC 秒值，允许相邻操作同秒。提交成功后仅返回 id/status/started_at/updated_at。

开始操作不要求 read_assigned、read_own、report、assign 或 repairer 角色；不复用派单候选资格，不按 admin 放行。REPORTED 因无受理人按对象授权拒绝。PR #1 未进入基线，不复制代码或历史；通用规则未来只辅助状态检查，不代替事务和条件更新。

## 文件与验收

预计修改 `app/m3/{models,errors,repository,service,router}.py`；新增 `web/templates/m3/assigned.html`、`web/assets/m3/assigned.js`，复用 orders.css/time.js，更新四张既有 M3 页面导航；新增 `tests/m3/test_start_repair.py`、`tests/m3/assigned_page.test.cjs`，以及本 spec/统一交接。无需新表、迁移、依赖或公共配置；不修改 V1 快照、默认库及其他模块。

| Given | When | Then |
|---|---|---|
| 两名受理人及管理员各有工单 | 查询默认/筛选列表 | SQL 只返回本人受理、稳定排序、空列表正常；读取权限不隐含开始权限 |
| ACTIVE + start 的实际受理人，没有读取权限或 repairer 角色 | 发送空对象开始 | 200 最小摘要，新连接读到 IN_REPAIR、同一开始/更新时间，其余字段不变；详情仍按读取权限拒绝 |
| 身份失效、缺 start、未知工单、他人工单、已开始 | 开始 | 分别 401/403/404/403/409，不因 admin 或角色名放行，不泄漏正文 |
| REPORTED、伪造/缺失请求体、非法/超大 ID | 开始 | 对象授权或输入/不存在拒绝，原字段不变，无整数溢出 |
| 撤权/禁用发生在身份边界后，或两连接同时开始 | 提交 | 事务内复核；最多一次成功，失败方不能覆盖首次时间 |
| UPDATE、COMMIT 真实失败或锁冲突 | 开始 | 全部回滚，未知错误 500、锁 503，不返回假成功 |
| 页面只读/可开始、冲突、鉴权失败、网络不明 | 操作 | 安全文本/北京时间、禁止重复、刷新冲突、清除私有内容、不自动重发 |
| 真实临时库与测试外部身份边界 | 报修 → 派单 → 开始 → 报修人详情/管理员队列 | 全部经过实际 M3 API、权限、SQL 和事务；称为模块流程测试，不等于真实共享登录 |

## 验证与交付记录

使用项目既有 Python 3.10.20 虚拟环境及本机 Node，没有安装/升级依赖。实际执行：

| 命令 | 结果 |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests/m3/test_start_repair.py -q` | 44 passed |
| `.\.venv\Scripts\python.exe -m pytest tests/m3 -q` | 302 passed，原创建、查询、详情、派单与持久化回归均通过 |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note、编译通过；390 passed |
| `node --test tests/m3/assigned_page.test.cjs` | 9 passed |
| `node --test tests/m3/report_page.test.cjs tests/m3/order_pages.test.cjs tests/m3/dispatch_page.test.cjs tests/m3/assigned_page.test.cjs` | 34 passed，含原页面 25 项回归 |

Python 有 1 条既有 Starlette/httpx 弃用提示，没有屏蔽、跳过或降低断言。四张既有导航模板在实现阶段最终检查时统一为仓库 LF，内容不变；其余最终变更仅补文档验证记录。发布前源码、页面和测试 SHA-256 与上述验证记录一致，仅修订本 spec 与交接文件的发布说明，沿用已有结果，不重复运行全套检查。Node 是本地独立验证，未纳入共享 CI；远端 CI 以最终提交对应的实际状态为准，依赖 PR 未自动触发时使用已有 workflow_dispatch，不预先宣称通过。006 的隔离破坏实验原记录保留，未重复。

真实数据库验证覆盖：仅 read_assigned 与仅 start 的权限分离、没有 repairer 角色也能按 start + 本人受理操作、管理员不能代他人开始、事务内撤权/禁用/删除、并发最多一次成功、重复请求不改首次时间、真实 UPDATE 错误/忽略更新/延迟外键 COMMIT 失败回滚，以及独立连接在 BEGIN/COMMIT 制造锁超时后全部字段不变。

`test_m3_r03_module_flow_report_assign_start_query` 已实际通过：在真实初始化器与固定 V1/M3 SQL 的临时库中，通过实际 API 完成报修人创建 → 管理员派单 → 受理人开始 → 报修人详情和管理员队列；身份只在测试装配边界替换。**这是模块流程测试，不是共享登录联调。** 未要求秒级时间严格递增或伪造时间。

实际 Uvicorn HTTP 启动检查：

- 正常应用 `127.0.0.1:8770`：首页、health/version、新页面与资源、原四张 M3 页面均 200；assigned API 和 start POST 在缺少共享认证时均为 503 auth_unavailable。
- 仅测试身份装配 `127.0.0.1:8771`：真实临时库的本人受理列表 200，非法非空请求 422 且记录不变，空对象开始 200，独立连接验证状态/时间与原字段，重复 409，他人工单 403，IN_REPAIR 筛选列表 200 且 can_start=false。
- 两项服务均已按本次记录的进程与子进程身份停止，8770/8771 不再监听；系统临时 HTTP 库保留，不递归清理，不修改默认库。
- Computer Use 初始化后列窗口及浏览器工具打开临时页面均报 `Computer Use native pipe is unavailable`（os error 2），未执行真实点击操作。**真实浏览器交互仍待人工验收**，DOM 模拟、HTML/HTTP 检查不代替浏览器验收。

实现阶段最终复核 15 个本批文件、暂存区为空、HEAD 与 007 基准一致；默认库和 V1 快照 SHA-256 未变。发布前再次核对完整差异、精确暂存范围、Note、差异空白及本地文档链接；提交和 PR 应仅含本批 15 个文件、1 个新增提交，继承历史不重新提交。

## 人工查看与交付状态

在项目根运行 `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`，打开 `http://127.0.0.1:8000/m3/assigned`。当前正常基线应提示共享认证未接入，不显示可操作的私人数据，不跳转到缺失登录页。模块流程可独立复现：`.\.venv\Scripts\python.exe -m pytest tests/m3/test_start_repair.py -k module_flow -q`。

正式接入后，用真实受理人查看列表/筛选和北京时间，开始本人 ASSIGNED 工单后核对状态与时间；以另一名受理人和管理员验证不能代操作，以仅读取账号验证无开始按钮。验证重复开始 409、撤权后清除数据、网络结果不明只重新查询；再由报修人和管理员核对详情/队列。完整整合验收清单见唯一交接文件。

交付状态：**M3-R03 首阶段“本人受理列表与开始维修”模块能力已实现并验证；模块内报修→派单→维修中流程验证通过，真实公共集成待完成。** 不标记 M3-R03 全部完成。待验收、完成、退回、评价、超时、座位及 M1 联动仍在后续范围。真实共享登录、正式迁移、权限初始化及浏览器验收仍待整合；本批已获单独发布授权，实际提交、推送、PR 与 CI 状态以 Git/GitHub 记录为准，团队评审待完成，不自动进入下一批。
