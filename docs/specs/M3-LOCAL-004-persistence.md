# M3-LOCAL-004：模块工单持久化

2026-11-27 整合说明：以下范围、确认与验证属于原任务；本次合入情况见 [LOCAL-010](LOCAL-010-branch-integration.md)。原 Review1 计划已删除，现行范围由需求基线维护；模块 SQL 仍未作为正式迁移安装。

## 范围与授权

- 基准：2026-11-12 fetch 后的 `origin/main`，`d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b`；独立分支 `m3/local-004-persistence`，创建前未发现同名分支、任务文件或 PR。
- 需求：M3-R01 的持久化基础，以及 M3-R02/M3-R03 的三状态数据约束；不代表真实登录报修已交付。
- 用户已明确授权本批方案、实现、真实数据库测试及必要技术选择，直接实施，无需再确认同一范围。新的协作方式允许模块按明确、可替换的暂定契约独立开发；**不再以 P/G/S/D 未回复、依赖未合入 main 或正式迁移编号未分配阻塞本批**。这一授权优先于旧提案的等待安排，公共契约仍未获团队批准。
- 仅修改 M3 实现/测试、本 spec 和唯一交接入口 [docs/m3/INTEGRATION.md](../m3/INTEGRATION.md)。共享接入由整合人员完成，不修改公共初始化器、默认开发库、公共迁移、认证、其他组业务或现有 PR。
- 本批不增加 HTTP/页面、派单/维修操作、真实认证/授权、座位报修、并发派单、验收评价、升级或 M3→M1 联动。
- 发布授权（2026-11-18）：用户明确授权只提交本批 8 个文件，推送 `m3/local-004-persistence`，创建目标为 main 的独立 PR，并向 `lyjlyjlyjly` 请求评审；不合并 PR、不开始下一批。此授权替代实施阶段的“不 commit、不 push”限制，**不等于人工验收通过或公共契约获批**。实际提交、推送和评审状态以 Git / PR 记录为准。

依据：[需求基线](../requirements.md)、[架构](../architecture.md)、[AGENTS.md](../../AGENTS.md)，以及 [PR #3 固定版本契约](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/f1e18209e2f327e0ed7e331d9ec4051f71c91ba1/docs/specs/M3-LOCAL-001-contract-spec.md)。本次独立开发授权不改写 PR #1/#2/#3。

## 方案比较与选择

| 方案 | 优点 | 代价 / 决定 |
|---|---|---|
| 等待共享迁移、认证和全部契约合入后再写数据层 | 直接使用统一版本 | 持久化工作继续被他组进度阻塞，不符合本次授权；本批不采用 |
| 模块 SQL 源 + 固定原始 V1 测试快照 + 真实初始化器（采用） | 可独立验证真实外键、升级和事务，正式编号由整合时决定 | 不等于公共基线接入，需明确依赖来源和最终 SQL 唯一维护位置 |

main 尚无共享业务迁移，故测试读取指定固定提交的原始 V1，保留字节内容并核验 SHA-256。测试把它和模块 SQL 放入临时 migrations_dir，临时连续编号不预占正式编号。生产 repository 只连接已存在且已初始化的数据库，不建库、不建表。

repository 采用两个简单函数：创建 REPORTED 返回 ID、按 ID 读取完整记录或 None。复用 `connect_database` 的独立连接、外键和事务管理；身份由上层提供，时间由服务端生成，SQL 参数绑定。PR #2 不在本分支中，不复制其实现；本批在写入边界做必要的字符串类型检查和 strip，最终创建业务层接入现有规范化函数及真实认证。可调整规则、错误行为、依赖快照校验信息统一维护在交接文件。

## 预计文件

- `app/m3/sql/repair_order.sql`：未编号的 M3 SQL 源。
- `app/m3/repository.py`：创建和按 ID 读取。
- `tests/m3/fixtures/V1__init.sql`：固定提交原始测试依赖快照。
- `tests/m3/conftest.py`、`test_schema.py`、`test_repository.py`：真实临时迁移/数据库夹具及行为测试。
- `docs/m3/INTEGRATION.md`：持续维护的唯一整合交接入口。
- 本 spec：仅记录本批范围、选择、验收及实际结果。

## Given–When–Then 验收

| Given | When | Then |
|---|---|---|
| 空库及真实 V1/M3 SQL | 用 initialize_database 的 migrations_dir 初始化 | 共享表和工单表存在，外键可用，连续版本应用成功 |
| 已有 V1 用户、房间和 M2 业务记录 | 升级并重复初始化 | 原数据保留，迁移不重复执行，不丢已有工单 |
| 合法身份/房间引用及报修文本 | 创建、关闭连接，再以新连接读取 | ID、规范化正文、服务器 UTC 时间正确，REPORTED 且四个派单/维修字段均 NULL |
| 无效用户/房间、分类、描述边界或状态 | 真实写入 | 外键/CHECK/NOT NULL 拒绝，已有记录及行数不变 |
| 三种状态与四字段 NULL/非 NULL 组合 | 分别执行 INSERT 和 UPDATE | 仅各状态对应组合通过；未知/NULL 状态拒绝 |
| 事务中已有一次合法写入，随后出现约束错误 | 异常离开真实连接事务 | 整个事务回滚，未留下部分记录或更新 |
| 未初始化或不存在的数据库 | 调用 repository | 明确失败，不暗中初始化或建立认证替身 |

实际验证顺序：先运行本批 `test_schema.py` 和 `test_repository.py`，再运行全部 `tests/m3`，最后运行一次 `scripts/ci.py`，均使用项目 `.venv` Python。不 mock 数据库、不跳过共享断言；结果完成后记录于本节。

## 实际结果与交付状态

2026-11-12 使用项目 `.venv` Python 3.10.20 实际执行：

| 命令 | 结果 |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests/m3/test_schema.py tests/m3/test_repository.py -q` | 99 passed，1 warning，11.13s |
| `.\.venv\Scripts\python.exe -m pytest tests/m3 -q` | 99 passed，1 warning，11.66s |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note 与编译检查通过；187 passed，1 warning，16.16s；All checks passed |

99 项为本批 73 项 schema/事务测试和 26 项 repository 测试，其中三状态的 48 种 NULL 组合逐项实际执行 INSERT/UPDATE。全套 187 项为 main 基准 88 项加本批 99 项；没有引入 PR #1/#2 的测试。各次唯一警告均为已有 Starlette TestClient/httpx 弃用提示，未屏蔽、未升级依赖；无测试失败、跳过或删除共享断言。

2026-11-18 提交前复核未修改实现、SQL 或测试，沿用上述实际结果，不为上传重复运行行为测试；仅更新本 spec 与交接文件的发布授权及状态说明。V1 快照与固定提交原件逐字节一致（3588 字节，SHA-256 见交接文件）；12 个本地链接和 4 个固定提交文件链接有效，8 个文件无行尾空白，`python scripts/check_notes.py` 通过（使用项目 `.venv`）。

**模块持久化已验证，公共基线接入待整合。** 尚未真实接入登录、权限、HTTP 创建和表单，不声明 M3-R01/R02/R03 全部完成。用户已授权本批提交、推送和请求评审；人工验收与团队代码评审仍待进行，没有已有的通过记录。后续接入步骤、暂定 NUL 边界与未验证范围统一见交接文件。
