# AGENTS.md

校园资源服务平台：一个 FastAPI 应用，M1/M2/M3 三个业务模块及公共层 D，共用 SQLite。说明和提交信息默认中文；标识符、需求 ID 和 API 路径保持原样。

## 开始任务

1. 先读本文件、[需求基线](docs/requirements.md)、[架构](docs/architecture.md) 和相关 `docs/specs/`；检查 `git status`，保留已有改动。
2. 当前需求范围与状态以 [需求基线](docs/requirements.md) 为准；[PJ 计划书](docs/PJ-计划书.md) 提供长期要求。任务书硬性要求不会因本轮延期而消失。
3. 将任务范围、约束、至少两个候选方案、预计文件和 Given–When–Then 验收写入 `docs/specs/<issue>.md`。没有 Issue 时使用明确的本地任务编号，不编造 Issue 链接。
4. 人确认方案后实施；会话中已有的明确实施授权可作为该任务授权并记入 spec，不为同一范围重复请求确认。遇到范围扩张、新增依赖或公共业务契约变化，先说明影响并取得相关负责人同意。

## 目录与边界

| 目录 | 职责 / 归属 |
|---|---|
| `app/main.py`、`app/common/` | 应用装配、配置、数据库连接；项目负责人协调 |
| `app/m1/` | G1：自习座位搜索、预约及预约状态 |
| `app/m2/`、`app/d/auth/`、`app/d/audit/` | G2：教室申请与审批、认证/RBAC、审计 |
| `app/m3/`、`app/d/spaces/` | G3：报修、空间和座位主数据 |
| `database/`、`app/bootstrap.py` | G3 汇总；共享 schema 由三组先定契约 |
| `web/` | 三组按页面协作；登录与公共布局由 G2 协调，即时反馈约定由 G3 协调 |
| `tests/` | 与模块对应的行为测试；共享基础设施测试 |
| `scripts/`、`.github/` | CI 与仓库检查；项目负责人 / 基础设施负责人 |
| `docs/` | 面向人的需求、任务、使用与协作说明 |
| `.agents/notes/` | 持久决策理由，格式与状态见其 [README](.agents/notes/README.md) |

- M1 管预约时段和可预约状态，D 管座位身份、位置、插座等主数据。业务模块不得直接写其他模块的数据表。
- 登录、角色、状态名、公共字段和共享接口的变更先协调受影响组；字段冻结前不得擅自为其他组定义契约。公共层或 schema PR 需要另一组成员评审。
- 当前只有三个业务路由挂载点；实现接口时同步 spec、文档和测试。后续跨模块 HTTP 调用须先有契约；本轮不实现写回。

## 命令

以下 `python` 指项目虚拟环境中的 Python；Windows 和 Linux 的完整准备命令见 [README](README.md)。

| 目的 | 命令 |
|---|---|
| 安装依赖 | `python -m pip install -r requirements.txt` |
| 初始化 SQLite | `python -m app.bootstrap` |
| 显式执行演示种子 | `python -m app.bootstrap --seed` |
| 本地启动 | `python -m uvicorn app.main:app --reload` |
| 与 CI 相同的检查 | `python scripts/ci.py` |
| Note 格式和引用 | `python scripts/check_notes.py` |
| 单个模块测试 | `python -m pytest tests/m1`（对应模块有测试后使用） |

## 实现与验证

- 保持 Python 单体、标准库 `sqlite3`、HTML/CSS；仅按需求添加少量原生 JavaScript。不自行引入 ORM、前端构建、服务拆分或通知系统。
- SQL 参数使用绑定；每次连接启用外键，不共享全局连接。初始化仅由版本迁移和独立种子入口完成。
- 业务迁移使用 `database/migrations/Vn__*.sql`，按 `PRAGMA user_version` 顺序执行。已提交迁移不改写；后续 schema 变化新增版本。禁止手工改库或将业务订单当种子。
- 配置使用进程环境变量；不提交真实个人数据、凭据、会话令牌、数据库文件或日志。会话凭据的具体实现遵守 D-R01。
- 测试调用真实被测逻辑并断言可观察结果；业务测试尽量在名称中带需求 ID，覆盖成功和拒绝路径。不得用断言常量或 mock 被测业务替代验证。
- 本地按改动运行必要检查；CI 执行全套。禁止用跳过测试、吞异常、`continue-on-error` 等手段制造通过。未运行就写“未运行”和原因。
- 每个业务模块后续至少记录一次“故意破坏实现 → 测试失败 → 恢复后通过”实验；不在主分支直接破坏功能，不伪造实验记录。

## 文档与决策

- 一个事实一个维护入口：规则在此，需求状态在 `docs/requirements.md`，任务验收在 spec/PR，决策理由在 Note。其他文档链接，不复制 ADR 正文。
- 只为影响后续工作的持久取舍新增 Note；局部修复、操作日志和聊天记录不写成 ADR。先查已有编号和取舍，再按 [Note 规范](.agents/notes/README.md) 写入。
- 提案默认 `proposed`。没有实际确认依据，不得标成 `implemented`、伪造表决或填写他人的 `Reviewed-by`。`implemented` 表示决策采纳，不代表关联功能交付。
- 变更行为时同步受影响的文档、命令、相对链接和测试；保留历史决策理由，替代关系通过新旧 Note 互链。

## Git 与交付

- **强制按模块组推送**：一次 push 只能更新一个分支/ref，业务路径最多涉及一个责任组；全局 `infra` 文件可单独推送或随该组配合。一个 PR 也最多包含一个业务责任组，不能把两个模块分别写成多条提交后塞进一次 push 或一个 PR。G1 对应 M1，G2 对应 M2 和 `app/d/auth/`、`app/d/audit/`，G3 对应 M3 和 `app/d/spaces/`、`database/`、`app/bootstrap.py`。共享 D 根目录是独立范围；全局规则、应用装配和 CI 属于 `infra`。这些目录映射由 [ADR-004](.agents/notes/implemented/process/2026-10-23-adr-004-module-scoped-pushes.md) 维护。
- 跨组功能先确认接口和依赖，再拆成组内分支、提交、push 和 PR，按依赖顺序推进。一次只推一个组；共享契约或基础设施单独用 `infra` / `d` scope。公共文件可随一个模块组修改，但不能借此同推另一组业务代码。
- 分支名按责任组使用 `m1/<Issue号>-简述`、`m2/...`、`m3/...`、`d/...` 或 `infra/...`。没有 Issue 时使用本地任务编号，不能编造 Issue。代码通过 PR 合入 `main`，不直接 push 主分支。
- **提交必须遵循带 scope 的 Conventional Commits**：`<type>(<scope>): <中文描述>`；破坏性变更写 `<type>(<scope>)!: <中文描述>`。type 限定为 `feat`、`fix`、`docs`、`style`、`refactor`、`perf`、`test`、`build`、`ci`、`chore`、`revert`；scope 必须是 `m1`、`m2`、`m3`、`d` 或 `infra`，且与文件归属一致。例如 `feat(m1): 增加座位时段搜索`、`fix(m2): 拒绝无审批权限的请求`、`docs(infra): 说明本地启动方法`。
- 提交同时修改一个业务组与全局 `infra` 文件时使用业务组 scope；只修改全局基础设施时使用 `infra`，只修改公共 D 根目录时使用 `d`。
- 每个 clone 执行 `python scripts/install_git_hooks.py` 安装本仓库的 push 前门禁。hook 检查本次新增提交、模块边界、分支名及 Conventional Commit；另有已安装的 hook 配置时先协调，不覆盖。GitHub CI 按每个 push ref 和 PR 检查范围与 Conventional Commit；GitHub 为同一条 `git push` 中的多个 ref 分别触发事件，完整 ref 数量由本地 hook 检查。负责人还须为 `main` 配置 PR 和必需检查，才能阻止失败的 PR 合入。
- 提交应对应具体任务或需求，说明改动和原因。默认由人验收后提交；Agent 只在用户明确授权时执行 commit、push、创建远端 Issue 或发布。
- 冲突由人处理；Agent 不执行 merge/rebase 解决冲突，不强推、不改写他人历史、不撤销未知改动。
- PR 写清改动、实际测试、待办和人工审阅人；保护 `main`、要求 CI 通过及评审属于 GitHub 设置，不能声称写入 YAML 就已开启。
- 交付说明完成内容、实际验证结果和剩余依赖；AI 的自查不能替代人工验收。完整流程见 [AI 协作说明](docs/ai-collaboration.md)。
