# 校园资源服务平台 PJ 计划书

> 依据：`Pj-任务书.md`（2026-10-08）。参考：`deepseek-harness-人机协作工程笔记.md`。
> 目标：在满足任务书每一条硬性要求的前提下，尽量少写功能代码、少做自研基础设施。

## 0. 总体策略：先满足任务书，再压低实现成本

任务书有几项不能直接删掉的验收要求。其余基础设施尽量不自建，业务需求中工作量大的部分先标记，交组内讨论。

| 需要保留（任务书明确要求） | 可以删去或压到最小 |
|---|---|
| AGENTS.md、需求基线、决策记录（ADR）、可审查的提交历史 | Docker、多服务拆分、复杂前端构建 |
| GitHub 上自动构建和测试、测试环境自动部署、生产发布人工审批与回滚演示 | 复杂流水线、多镜像构建、独立前端构建 |
| SQLite 版本化迁移、幂等种子数据、从空库重放 | Alembic/Flyway 等迁移框架、Testcontainers、PIT |
| 至少一条跨模块网络调用、行为测试、需求追踪和验收标准 | 邮件、短信、后台推送、消息中心、附加项"自然语言业务代理"（**不做**） |
| — | 定时提醒等较难的需求先标记，交组内讨论后决定 |

三条原则：

1. **先做一个 FastAPI 应用。** M1、M2、M3、D 按 Python 包分开，共用一个 SQLite 数据库；不拆成四个服务。
2. **只保留任务书要求的基础设施。** 本地用 Python 虚拟环境；迁移保留一个简单的 SQLite SQL 版本脚本，不引入迁移框架。
3. **GitHub Actions 只做必要步骤。** 一个工作流负责 Python 检查、pytest 和测试环境部署；生产发布用人工触发，能按 tag 回滚。

任务书明确要求版本化迁移、测试、部署与至少一条跨模块网络调用，因此不能在计划中直接删掉；这里采用最小实现。D-R04 缩为当前操作后的站内弹窗，不建设后台通知服务。

---

## 1. 技术选型（ADR-002 提案摘要）

| 层 | 选择 | 理由 |
|---|---|---|
| 后端 | Python 3.10+、FastAPI、Uvicorn | 一个应用提供页面和 API；M1/M2/M3/D 按目录分模块 |
| 数据库 | SQLite、Python 标准库 `sqlite3` | 单个文件即可运行，不用安装数据库服务器 |
| 页面 | HTML、CSS；确有需要时再加少量原生 JavaScript | 不使用 Vue、Node.js 或前端打包 |
| 登录 | D-R01：服务端会话 + HttpOnly Cookie | 单体应用使用浏览器会话即可；数据库仅保存会话令牌哈希，不实现 JWT/JWK |
| 数据演进 | 保留 `database/migrations/Vn__*.sql` 和 `PRAGMA user_version` | 任务书要求版本化迁移，脚本由项目初始化代码顺序执行 |
| 页面提示 | D-R04 仅反馈当前操作结果 | 页面内弹窗/提示框；不做后台通知、消息中心、邮件或短信 |
| 测试 | pytest + FastAPI TestClient + 临时 SQLite 文件 | 满足自动测试和行为验证；不引入 Testcontainers/PIT |
| CI | GitHub Actions | PR 和 main 更新时运行 Python 检查与 pytest |
| 部署 | 单台课程服务器；Python 虚拟环境 + Uvicorn/systemd | 任务书要求自动部署测试环境和人工发布生产环境；不引入 Docker |

本表供组内阅读。ADR-002 的状态、方案比较和决策理由以 `.agents/notes/` 中的 ADR Note 为准；采纳后由人类文档链接到该 Note，不复制决策理由。

测试、版本化迁移和部署是任务书要求，不能直接删除；各自采用一个 pytest 工作流、一组 SQLite 版本脚本和一台服务器来实现。跨模块网络调用只保留一条最小链路，方案见 §5。

---

## 2. 分工与公共层归属（ADR-001，项目启动节点必交）

ADR-001 的权衡和结论写为 Agent Note，放在 `.agents/notes/proposed/architecture/`，组内确认后移至 `implemented/architecture/`。会议日期、参会人、投票情况等面向人的材料放在 `docs/decisions/`；该目录只做索引和会议记录，不另存一份 ADR 正文。

6 人分 3 个模块组，每组 2 人。公共层 D **按子域拆分**，分给负担较轻的 M2、M3 组：

| 模块组 | 成员 | 业务模块 | 公共层子域 | 兼任角色 |
|---|---|---|---|---|
| G1 | A、B | M1 自习座位预约（最重，含跨模块写回的接收端） | — | A：需求基线负责人 |
| G2 | C、D | M2 整教室预约与审批 | 身份认证 / RBAC / 审计记录 / 登录页面与公共布局 | C：发布负责人（打 tag、批准生产发布） |
| G3 | E、F | M3 物业报修工单 | 空间与座位主数据 / 数据库种子与初始化 / D-R04 弹窗 | E：CI 与基础设施负责人 |

ADR-001 里要写的"考虑了什么"：

- **工作量均衡：** M1 需求最多（附件 1 有 7 大项），而且是至少一条写回链路的接收方，所以不再背公共层。
- **公共层治理：** D 的职责和跨模块接口写进 ADR/spec；涉及公共层的 Pull Request 请另一组同学评审。
- **故障归属：** 子域和代码目录一一对应，用 `CODEOWNERS` 标明。线上问题能按目录找到负责人。
- **备选方案：** ① D 整体交给一个组：工作量严重失衡；② 每组各写一份：重复实现，权限模型不一致；③ 单设一个 D 组：6 个人凑不出第 4 组。写清楚这三个为什么没选。
- **如何达成一致：** 写明开会日期、参会人、各方案得票情况、最终结论。会议纪要或截图放在 `docs/decisions/`，并从该目录索引链接到 ADR Note。

**座位主数据和座位状态分开管理：** D 管"座位存在吗、在哪个房间、有没有插座"；M1 管"这个时段能不能约、被谁占了"。这条写进 ADR-003 Agent Note。

---

## 3. 仓库结构

沿用本项目的 Python 单体结构；不照搬参考项目中与本项目无关的训练、临时文件目录。代码、规则、文档、决策 Note、流水线和迁移脚本都随项目提交。根目录 `AGENTS.md` 是 Agent 的规则入口；`.agents/notes/README.md` 规定决策 Note 格式；`docs/` 放给组员、老师和使用者阅读的项目材料。

```
campus-platform/
├─ AGENTS.md
├─ .agents/
│  └─ notes/
│     ├─ README.md            # Agent Note 生命周期与 ADR 格式
│     ├─ proposed/            # 待评审的提案，按主题分类
│     ├─ implemented/         # 当前或曾经采纳的决策，按主题分类
│     └─ rejected/            # 仅保留值得防止重议的否决方案
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ .github/
│  ├─ workflows/ci.yml       # GitHub Actions：Python 检查、pytest、测试环境部署
│  ├─ CODEOWNERS             # 目录负责人，供 PR 评审参考
│  └─ ISSUE_TEMPLATE/        # 任务卡模板
├─ app/
│  ├─ main.py                # 单个 FastAPI 应用入口
│  ├─ common/                # SQLite 连接、登录、共用依赖
│  ├─ m1/                    # 自习座位预约
│  ├─ m2/                    # 整教室预约与审批
│  ├─ m3/                    # 报修工单
│  └─ d/                     # 公共层功能
├─ web/
│  ├─ templates/             # HTML 页面
│  └─ assets/                # CSS；确有需要时再放少量 JavaScript
├─ database/
│  ├─ migrations/Vn__*.sql   # SQLite 轻量版本化 SQL
│  └─ seed.sql               # 独立、幂等的演示数据
├─ tests/                    # pytest 单元、API 和少量集成测试
├─ scripts/
│  ├─ bootstrap.sh           # 首次准备服务器环境（如课程服务器需要）
│  └─ deploy.sh              # 测试/生产部署与健康检查
└─ docs/
   ├─ requirements.md
   ├─ architecture.md
   ├─ decisions/README.md     # 人类可读索引、会议记录；链接到 ADR Note
   ├─ specs/
   ├─ ai-collaboration.md
   ├─ ethics-log.md
   └─ release-process.md
```

Agent Note 按 `.agents/notes/{proposed|implemented|rejected}/{feature|bug-fix|simplification|architecture|process|testing}/yyyy-mm-dd-topic.md` 存放，并在标题中带 ADR 编号；`docs/` 是人类阅读入口。两处不重复 ADR 正文：Note 是决策理由的权威来源，`docs/decisions/README.md` 只提供索引和会议记录。

---

## 4. 需求范围（需求基线的骨架）

需求 ID 格式为 `M1-R01`。每条需求都要有验收标准，写成 Given-When-Then 一行即可。没做的需求**留在表里**，状态标成"不做 / 延后"，并写上原因。

### M1 自习座位预约（来自附件 1，照做）

| ID | 需求 | 最小实现 |
|---|---|---|
| M1-R01 | 管理员维护自习室及开放时间、院系归属 | 自习室本身的数据在 D，M1 读取；开放时间和院系限制在 M1 校验 |
| M1-R02 | 角色权限可配置（教室管理员、运营管理员） | 用 D 的 RBAC，M1 只声明自己的权限码 |
| M1-R03 | 按整点小时预约，单次最多 4 小时（参数可调） | 写成配置项 `seat.max-hours`，校验整点 |
| M1-R04 | 签到：每个教室每天一个动态编码，Web 端录入 | 每日动态码；管理端有一个"教室屏幕"页面显示编码 |
| M1-R05 | 开始前 15 分钟提醒、开始后 10 分钟未签到再提醒 | 定时提醒 |
| M1-R06 | 开始后 15 分钟未签到：自动取消、释放座位、记一次违约、通知学生 | 自动取消与定时任务先讨论是否保留；不做后台或定时通知 |
| M1-R07 | 按条件搜索座位（教室、时段、是否有插座） | 一个查询接口 + 一个页面 |
| M1-R08 | 查看历史预约，一键再约同一座位 | 历史列表 + "再约"按钮（带入座位，选新时段） |
| M1-R09 | 运营统计：按教室、按日的预约数、签到率、违约数 | 仅在签到/违约数据需求确定后再做 SQL 聚合表格，**不做图表** |
| M1-R10 | 座位状态记录写入来源（M1/M2/M3），可追溯 | 先实现 M1/M3 来源和查询；M2 来源随链路 B 是否保留再决定 |

### M2 整教室预约与审批（用 AI 细化，但保持最小）

| ID | 需求 | 最小实现 |
|---|---|---|
| M2-R01 | 权限门槛：只有教师、学生组织负责人这类角色可以申请 | 用 RBAC 权限码 `room:apply` 控制 |
| M2-R02 | 提交申请：教室、时段、用途、人数 | 校验人数不超过容量、时段在开放时间内 |
| M2-R03 | 两级审批（院系 → 空间管理处），每级可通过或驳回 | 审批链写成配置列表，不做可视化流程设计器 |
| M2-R04 | 超时自动撤销：某级 N 小时未处理，或已过开始时间 | 定时任务处理；N 可配置 |
| M2-R05 | 申请人可撤销、可查看状态 | 状态机：`PENDING_L1 → PENDING_L2 → APPROVED / REJECTED / REVOKED / CANCELLED` |
| M2-R06 | 审批通过后占用 M1 的全部座位；驳回、撤销后回滚 | 先讨论是否实现；首条网络链路优先选较简单的 M3→M1 |

### M3 物业报修工单

| ID | 需求 | 最小实现 |
|---|---|---|
| M3-R01 | 上报故障：位置（教室/座位）、类型、描述、可选图片 | 图片**不做**，先只收文字 |
| M3-R02 | 派单给维修人员 | 管理员手动指派，不做自动派单算法 |
| M3-R03 | 状态流转 | `REPORTED → ASSIGNED → IN_REPAIR → PENDING_ACCEPT → DONE`，验收不通过就退回 `IN_REPAIR` |
| M3-R04 | 超时升级：派单超时、维修超时 | 定时任务和自动升级先讨论是否保留；不做通知主管的后台消息 |
| M3-R05 | 完工验收与评价（1–5 星 + 文字） | 只有报修人能验收 |
| M3-R06 | 自习室有工单处于"维修中"时下架座位，验收通过后恢复 | 见 §5 链路 A |

### D 公共层

| ID | 需求 | 最小实现 |
|---|---|---|
| D-R01 | 登录与服务端会话 Cookie | 账号密码登录后设置 HttpOnly 会话 Cookie；数据库仅保存会话令牌哈希，退出时使会话失效 |
| D-R02 | RBAC：用户、角色、权限，管理员可配置 | 先讨论最小角色范围和是否需要运行时配置权限 |
| D-R03 | 空间主数据：楼宇、房间（类型、院系、容量）、座位（编号、插座） | 增删改查 + 种子数据 |
| D-R04〔简化实现〕 | 站内即时提示：当前操作完成后弹窗显示结果 | 只反馈本次操作结果；不做后台推送、消息中心、邮件或短信 |
| D-R05 | 操作审计：谁、什么时候、对什么、做了什么 | 先覆盖关键管理操作，避免一开始实现复杂审计框架 |

**附加项（第五节，自然语言代理）：不做。** 在需求基线里列一行 `EXT-01`，状态写"不做"，原因写"附加项，优先保证主线要求"。

---

## 5. 跨模块集成（ADR-003）

任务书要求至少一条跨模块网络调用。本计划只保留最容易演示的一条：M3 报修进入“维修中”时，通过 HTTP 调用 M1 下架座位；完成验收后再调用 M1 恢复座位。M1、M2、M3、D 仍在同一个 FastAPI 应用中，不拆服务。ADR-003 的取舍和决策状态记录为 `.agents/notes/` 下的 ADR Note；本节保留供人阅读的接口摘要。

M3 使用 `httpx` 向本机 FastAPI 地址发请求，M1 提供内部路由：

```
POST   /internal/seat-blocks      {roomId, source: "M3", refId}
DELETE /internal/seat-blocks/M3/{refId}
GET    /seats/{id}/status-history
```

M1 在 SQLite 的 `seat_block` 表保存来源和引用 ID，重复的 POST/DELETE 要能安全重试。内部路由不放进前端页面，并用一个简单的环境变量令牌保护。组内需确认课程所说的“网络调用”接受同一应用内经 localhost 发起的 HTTP 请求；若要求独立进程，再讨论是否增加服务，不先预设拆分。

| 链路 | 本轮建议 | 行为 |
|---|---|---|
| A：M3 → M1 | 保留，作为跨模块网络调用演示 | 工单进入 `IN_REPAIR` 时 POST；验收进入 `DONE` 时 DELETE；座位状态记录 `M3` 来源 |
| B：M2 → M1 | 难度较高，先列为待讨论 | 仅在组内确认 M2-R06 且链路 A 完成后再做 |

调用失败时，不完成本次状态变更并返回可重试错误；暂不做 outbox、异步重试或补偿框架。若将来做 M2 占用座位，取消冲突预约时不记违约；学生可在预约页面看到取消原因，本轮不发送通知。

**集成验证**：CI 临时启动一个 Uvicorn 进程，pytest 通过本机 HTTP 调用 M3，再验证 M1 座位不可约、验收后恢复，并在状态记录中看到来源 M3。不额外搭建容器或独立测试平台。

---

## 6. 版本管理与流水线

### 6.1 分支与合并

- GitHub 仓库使用 `main` 作为主分支；所有改动通过 Pull Request 合并。
- 分支名采用 `m1/12-reserve-max-hours`（模块/Issue 号-简述）。
- 为 `main` 开启 PR 和通过 CI 后才能合并的规则；跨组目录由 `CODEOWNERS` 提醒对应同学评审，不编写自定义 GitHub API 门禁。
- 提交说明用 Conventional Commits，例如 `feat(m1): 预约时长上限改为可配置 (#12)`；说明改动原因，并保留人工审阅记录。暂不增加提交信息 lint。
- PR 控制在容易审阅的范围内，附任务卡和验收结果；冲突由人处理，不让 AI 自动 merge/rebase。

### 6.2 GitHub Actions

一个 `.github/workflows/ci.yml`，只保留这些步骤：

| Job | 何时运行 | 做什么 | 对应要求 |
|---|---|---|---|
| `check` | Pull Request、push 到 `main` | 安装 `requirements.txt`，运行 `python -m compileall app` 和 `python -m pytest` | 自动构建/测试；失败后停止 |
| `deploy-test` | `main` 的检查通过后 | 通过 SSH 调用 `scripts/deploy.sh test <commit>`，重启单体应用并检查 `/health` | 测试环境自动部署 |
| `deploy-prod` | 发布负责人手动触发 | 部署指定 tag；执行前由负责人确认 | 生产环境人工审批 |

服务器 SSH 凭据放在 GitHub Actions Secrets，不写入仓库。GitHub 分支保护要求 CI 通过后才能合并；跨组评审由 PR 审批和 CODEOWNERS 完成。流水线不构建镜像、不跑前端构建，也不增加独立的发布/质量门禁服务。

### 6.3 版本、发布与回滚

- 使用一个项目版本 tag：`v0.1.0` 对应 Review1，`v0.2.0` 对应 Review2，`v1.0.0` 对应期末版本；GitHub Release 记录每次发布的变更。
- 页面页脚或简单的 `/version` 路由显示当前 tag/commit，方便说明服务器运行版本。
- 发布顺序只有一个 FastAPI 应用：更新代码、应用 SQLite 迁移、重启进程、检查 `/health`。发布窗口写入 `release-process.md`。
- 回滚时由负责人选择上一个已知可用 tag 重新部署。部署前备份 SQLite 文件；如新版本改变 schema，则按 ADR 约定保持向后兼容，必要时恢复部署前的数据库备份。

### 6.4 环境

| 环境 | 位置 | 部署方式 |
|---|---|---|
| 开发 | 每人本机 Python 虚拟环境和临时 SQLite 文件 | 手动启动 Uvicorn |
| 测试 | 一台课程服务器 | `main` 检查通过后由 GitHub Actions 自动更新 |
| 生产 | 有条件时用另一台服务器；资源有限时与测试共机，使用不同目录、进程、端口和 SQLite 文件 | 发布负责人手动触发 |

`bootstrap.sh` 只负责课程服务器首次准备所需的 Python、目录和 systemd 服务；`deploy.sh` 更新代码、备份数据库、应用迁移、重启服务并检查健康状态。两者不安装 Docker 或 Runner。

---

## 7. 数据演进

- 整个项目共用一个 `database/migrations/` 目录。任务书要求版本化迁移，因此不能完全省略；只保留简单 SQL 文件和 Python 初始化逻辑，不用 Flyway/Alembic。
- 文件按 `V1__init.sql`、`V2__...sql` 命名。初始化代码读取 `PRAGMA user_version`，按顺序应用尚未执行的脚本；已提交的迁移不修改，避免新旧环境结果不一致。
- 种子数据单独放在 `database/seed.sql`，用 SQLite 的 `INSERT OR IGNORE` 保证可重复执行；预约、工单等业务记录不放进种子。
- CI 使用临时 SQLite 文件，从空库执行迁移和种子脚本，再跑 pytest；不启动 Testcontainers 或额外数据库服务。
- 期末展示安排一次简单的真实 schema 变化，例如增加座位属性，并展示 `user_version` 从旧值升到新值，满足任务书的数据演进演示。

---
## 8. 人机协作方式（考核重点一）

### 8.1 规则固化：AGENTS.md

参考 PubMedQA 的做法：根目录 `AGENTS.md` 是 Agent 的规则入口；它说明做什么以及去哪里找详细规则。`.agents/notes/README.md` 约束决策 Note；`docs/` 提供人类可读的需求、架构、任务和协作说明。规则不要在多个文件重复维护。根文件至少包含：

```markdown
# AGENTS.md
校园资源服务平台。架构见 docs/architecture.md，需求见 docs/requirements.md。

## Layout / Commands
（目录职责表；python -m app.bootstrap 初始化；python -m uvicorn app.main:app --reload 启动）

## 必须
- 动手前先在 docs/specs/<issue>.md 写方案（范围、改动点、验收标准、备选方案），等人确认后再实现。
- 只改任务卡范围内的目录；需要改其他模块组的代码或公共接口时，停下来说明。
- schema 变更新增 Vn__*.sql 文件，由 PRAGMA user_version 控制顺序；禁止修改已提交的迁移文件或手工改库。
- 做到的需求要有对应行为测试，测试名尽量带需求 ID；优先验证关键预约规则和跨模块链路。
- 测试断言实际行为，不 mock 被测逻辑；每个模块至少做一次故意破坏实现的实验。
- 必要配置用环境变量或简单 Python 配置文件，不为此引入 YAML 配置框架。
- 跨模块 HTTP 路由与请求字段写入 ADR/spec；业务模块不直接改其他模块的数据表。
- 持久决策用带 ADR 编号的 Agent Note 写入 `.agents/notes/`；新增前先读 `.agents/notes/README.md`，正文按状态使用对应章节。
- 人类文档不复制 Agent Note 的决策理由；`docs/decisions/README.md` 只索引 Note 并保存会议记录。

## 禁止
- 执行 git merge / rebase 来解决冲突；执行 git push --force；自行 commit（由人审查后提交）。
- 把密钥、密码写进代码或日志。
```

`CLAUDE.md` 和其他工具的规则文件只写一句"见 AGENTS.md"，不重复内容。

Agent Note 生命周期按 PubMedQA 的轻量规则执行：`proposed` 表示待组员评审，采纳后移入 `implemented`；明确否决且值得防止重议的提案才放入 `rejected`。Note 使用 ADR 结构：`Problem`、`Alternatives considered` 为必需章节；`proposed` 写 `Proposal`、`Acceptance criteria`、`Risks`，`implemented` 写 `Decision`、`Consequences`，`rejected` 写 `Why rejected`、`Reconsider only if`。被新决策取代时不改写旧 Note 的理由；新 Note 写 `Supersedes: ADR-xxx`，旧 Note 增加 `Superseded by: ADR-yyy` 并链接新 Note。`superseded` 是取代关系，不单独建状态目录；旧 Note 保留原状态目录和历史理由。

Note 文件名使用日期和主题，例如 `yyyy-mm-dd-adr-001-public-layer-ownership.md`，固定开头与提案示例：

```markdown
# Agent Note: ADR-001 公共层归属

Status: proposed — 等待组内评审

## Problem
问题与背景。

## Proposal
拟议决策。

## Alternatives considered
备选方案及取舍。

## Acceptance criteria
通过标准。

## Risks
风险。
```

### 8.2 任务委派：任务卡 → 方案 → 实现 → 验收

GitHub Issue 模板就是任务卡：

```markdown
## 背景 / 需求 ID
## 范围（做什么）
## 不做什么
## 约束（目录、接口、性能、安全）
## 验收标准（Given-When-Then，可测试）
```

流程如下，每一步都会在提交历史里留下证据：

1. 人写任务卡，并挂到对应的 Milestone（Review1 / Review2 / Final）。
2. AI 读任务卡，写出供人审阅的 `docs/specs/<issue>.md`，里面**列出至少 2 个候选方案并比较**。如涉及持久的架构或工程决策，同时在 `.agents/notes/proposed/` 写带 ADR 编号的 Note；人审阅后，采纳的 Note 移到 `implemented/`，重要的否决方案按规范移到 `rejected/`。
3. AI 按选定方案分小步实现；人每一步都看 diff、本地跑测试，**确认后由人提交**。
4. 提 Pull Request，由同组成员 review；涉及跨组改动时，由另一组的人 approve。
5. 合并后自动部署到测试环境，在 Issue 里贴上测试环境的验证结果，然后关闭 Issue。

"理解和评估 AI 的候选方案"的证据，就是人类任务规格中的方案比较和 Agent Note 的 `Alternatives considered`。每篇 ADR Note 都要说明 AI 首个方案、组内最终选择以及取舍理由。

### 8.3 质量保证：AI 代码的隐患与对策（写进 `docs/ai-collaboration.md`）

| 隐患 | 对策 | 证据 |
|---|---|---|
| 假测试（断言常量、mock 掉被测逻辑、只覆盖空分支） | 不上 PIT；PR 检查测试是否验证可观察行为 | PR 审查记录 |
| 测试其实不验证行为 | **故意破坏实现**：每个模块至少做一次，在分支上改坏一条规则（例如把 4 小时上限改成 5 小时），推上去看流水线变红，再把截图和链接贴进文档 | 红色流水线 + PR 记录 |
| 越界修改其他模块 | 任务卡写清范围；CODEOWNERS 标出负责人并由跨组同学人工评审 | PR 记录 |
| 编造不存在的 API 或依赖 | Python 检查和 CI 通过；新增依赖先由组员确认 | `requirements.txt` 的变更 |
| 安全问题（SQL 拼接、越权、硬编码密钥） | SQLite 查询使用参数绑定；接口检查登录/权限；凭据只放服务器环境或 GitHub Secrets | PR 审查记录 |
| 一次生成大批量代码，无法审查 | 小步提交、PR 控制改动范围 | 提交历史 |
| 过度设计 | 方案阶段先由人删减 | specs 文件 |

---

## 9. 进度安排

任务书不规定统一时间，下面的日期是建议，以老师公布的 Review 时间为准，前后平移即可。进度通过 GitHub Issues 和 Milestones 跟踪。

### 迭代 0：启动 + 打通骨架（10-19 ～ 10-25）→ 项目启动节点

| 任务 | 负责人 |
|---|---|
| 分组、认领模块，开会讨论并写出 ADR-001 Agent Note（公共层归属）；会议记录放在 `docs/decisions/` | 全员 |
| 建 GitHub 仓库，提交 AGENTS.md、目录结构、PR/Issue 模板、CODEOWNERS | C |
| 准备课程服务器，写 `bootstrap.sh` 和 `deploy.sh`，将 SSH 凭据放入 GitHub Actions Secrets | E |
| **一个 FastAPI hello-world 应用 + HTML/CSS 页面 + SQLite，经 GitHub Actions 自动部署到测试环境**（同时准备最小的 `V1__init.sql`） | E 主导，各组提供自己的路由 |
| 写 ADR-002 Agent Note（状态为 proposed，记录技术栈方案）；组内确认后移入 implemented | C |

完成标准：往 `main` 合并一个改动，几分钟后测试环境的页脚版本号随之变化。

### 迭代 1（10-26 ～ 11-15）→ 第一次 Review

| 交付物 | 负责人 |
|---|---|
| `requirements.md` 需求基线（§4 各表补上验收标准），每条需求建一个 Issue，标明依赖关系（D-R01/R02/R03 → 其余） | A 汇总，各组写自己的部分 |
| D：基础登录（服务端会话 Cookie）、最小 RBAC、空间主数据和种子数据 | G2、G3 |
| M1：搜索 + 预约 + 时长校验 + 我的预约 | G1 |
| M2：提交申请 + 一级审批 | G2 |
| M3：上报 + 派单 + 状态流转 | G3 |
| `ai-collaboration.md` 第一版、风险识别（§12）、`ethics-log.md` 第一批记录 | 各组 |
| 打 tag `v0.1.0`，首次发布到生产 | C |

### 迭代 2（11-16 ～ 12-13）→ 第二次 Review

| 交付物 | 负责人 |
|---|---|
| 链路 A：M3 通过 HTTP 调 M1 + `seat_block` 来源追溯（ADR-003）；链路 B 先讨论 | G1 接收端，G3 调用端 |
| 定时任务：只实现组内讨论后选定的项目；其余需求留在表中并注明延期原因 | 各组 |
| 确认 D-R04 的站内即时提示是否满足课程对通知服务的最低要求；不建设后台通知服务 | G3、G2 |
| 组内讨论后决定是否做 M1 动态签到、M2 二级审批等难项；M3 验收与评价可优先实现 | 各组 |
| 用 pytest 验证跨模块链路并接入 GitHub Actions；不另建测试平台或质量门禁脚本 | E、各组 |
| 每个模块做一次"故意破坏"实验并留档 | 各组 |
| 演练一次生产发布 + 回滚，写出 `release-process.md` | C |
| 打 tag `v0.2.0` | C |

### 迭代 3（12-14 ～ 期末）→ 期末展示

| 交付物 | 负责人 |
|---|---|
| 优先完成历史一键再约和插座筛选；运营统计、管理端扩展按讨论结果决定 | G1 |
| 有意安排一次 schema 演进（例如 `V2__seat_window_flag.sql`） | G1 |
| 补齐 `requirements.md` 的"实现 / 测试 / 状态"列，未完成的需求标明原因 | A |
| 按 §11 的清单完整彩排 2 次 | 全员 |
| 打 tag `v1.0.0` | C |
| 个人课程论文（使用 ethics-log 里的素材） | 每人 |

---

## 10. 工程伦理：在开发过程中持续记录

维护一个文件 `docs/ethics-log.md`，每条记录包括：日期、阶段、问题、本组的做法、仍然存疑的地方。各阶段都**真实发生过**的话题，至少可以记下面这些（个人论文直接从这里取材）：

| 阶段 | 话题 | 本组的处理（示例） |
|---|---|---|
| 需求 | 违约记录与惩罚的公平性：生病、课程拖堂等不可抗力 | 只记录违约、不自动封禁；学生可以申诉（列为"延后"需求） |
| 需求 | M2 整教室占用会挤掉已经预约的学生 | 取消预约时不记违约，并在页面显示取消原因；通知需求另行讨论（ADR-003） |
| 设计 | 隐私：签到记录、违约记录、位置轨迹 | 数据最小化；运营统计只用聚合数据，不展示个人明细；明确保留期限 |
| 设计 | 审计日志本身也是监控 | 只记录管理操作和状态变更，不记录学生的浏览行为 |
| 开发 | 使用 AI：不把真实学生数据或密钥发给 AI；AI 生成代码的许可证和来源 | 种子数据全部虚构；写进 AGENTS.md |
| 开发 | 责任归属：AI 写的 bug 由谁负责 | "提交人即责任人"，`Reviewed-by` 必须写上 |
| 测试 | 假测试带来的虚假安全感 | 人工检查测试行为 + 故意破坏实验 |
| 发布 | 生产故障对学生的影响 | 人工审批、可回滚、固定发布窗口 |
| 可访问性 | 视障学生能否使用 | HTML 表单提供 label 和必要的 aria 属性（只做基础，标为存疑） |

---

## 11. 期末演示清单（任务书第七节，必须现场演示，不能放截图）

| # | 演示项 | 准备方式 | 用时 |
|---|---|---|---|
| 1 | 从全新环境开始，通过流水线部署 | 一台新 VM → `bootstrap.sh` 准备 Python 和服务目录 → GitHub Actions 部署到测试环境 | 约 8 分钟，提前开始，穿插讲解 |
| 2 | 提交变更，自动触发构建和测试 | 提前准备一个改动文案的分支，现场推送并开 Pull Request，展示 Actions 检查结果 | 约 3 分钟 |
| 3 | 包含 schema 变更的部署 | 展示 `V2__seat_window_flag.sql`、迁移日志和 SQLite `PRAGMA user_version` 变化 | 约 2 分钟 |
| 4 | 生产发布与回退 | 发布负责人手动部署 tag `v1.0.1` → 查看页脚版本 → 重新部署 `v1.0.0` 并恢复对应数据库备份 | 约 4 分钟 |
| 5 | 跨模块链路 | 浏览器里报修并置为维修中 → 座位从搜索结果消失 → 验收 → 座位恢复 → 展示状态记录中的 M3 来源 | 约 4 分钟 |

另外再讲 5 分钟人机协作过程，按"规则文件 → 一个任务卡从 spec 到 Pull Request 的完整链路 → 一次故意破坏实验 → 一个 ADR 里否掉了 AI 首个方案"的顺序展示。

---

## 12. 风险识别（第一次 Review 要交）

| 风险 | 可能性 | 影响 | 应对 |
|---|---|---|---|
| 课程服务器或 SSH 配置迟迟不到位，测试部署无法演示 | 中 | 高 | 尽早确认服务器；先完成本地 Actions 检查，再准备最小部署脚本和密钥 |
| 测试环境与生产环境同机，数据或端口混用 | 中 | 中 | 用不同目录、端口和 SQLite 文件隔离；种子账号只用于测试 |
| M3→M1 内部 HTTP 接口理解不一致 | 中 | 高 | 先在 ADR 写清一个路由、请求字段和错误处理，再实现并用 pytest 验证 |
| AI 生成看似可用但未验证行为的测试 | 高 | 中 | PR 人工审查 + 故意破坏实验；不引入 PIT |
| 合并冲突集中爆发 | 中 | 中 | 小 PR、勤合并；每个模块只改自己的目录；冲突由人解决 |
| 组员进度不均 | 中 | 中 | 每周在看板上过一次 Milestone 进度；按 §4 的"最小实现"控制范围 |
| 定时任务难以演示（15 分钟、N 小时） | 高 | 低 | 先讨论是否实现定时需求；若保留，将时长做成可配置并在测试环境缩短 |

---

## 13. 自查表：任务书条目对照本计划

| 任务书要求 | 本计划的落点 |
|---|---|
| 规则以机器可读形式固化 | §8.1 AGENTS.md |
| 任务有范围、约束、验收标准；先出方案再实现 | §8.2 任务卡 + specs |
| 说明 AI 代码质量隐患与对策 | §8.3 |
| 产物全部入库，持续提交 | §3 仓库结构，§9 从第一周开始 |
| 提交说明对应任务，人工验收后提交 | §6.1 提交规范 + `Reviewed-by` |
| 分支策略，PR 评审，冲突由人处理 | §6.1 |
| tag 可追溯，Release 说明 | §6.3 |
| 自动构建、测试失败即停止 | §6.2 `check` |
| 测试不过不能合并；跨模块 / 公共层 / schema 变更须评审 | GitHub 分支保护 + PR 审批和 CODEOWNERS |
| 测试环境自动部署，覆盖全部模块 | `deploy-test` |
| 生产环境人工审批、可回滚、能说明当前版本 | §6.3 |
| 发布协调、部署窗口 | §6.3 单体应用发布窗口 |
| 版本化迁移，从空库一次重放；种子数据幂等且与业务数据分离 | §7 |
| 需求可追踪，未完成项明确记录，有验收标准 | §4 + `requirements.md` |
| 测试真实验证行为（故意破坏实现） | §8.3 |
| 基础设施脚本化 | `bootstrap.sh`、`deploy.sh` |
| 评估 AI 候选方案 | `docs/specs/` 人类任务规格 + `.agents/notes/` ADR Note |
| 公共层归属决策记录 | §2 ADR-001 Agent Note；人类索引与会议记录在 `docs/decisions/` |
| 讨论补充集成点 | §5 |
| 伦理融入各个阶段 | §10 `ethics-log.md` |
| 附加项 | 不做，在需求基线里记为 `EXT-01` |
