# SPEC-000：仓库骨架与协作规则

日期：2026-10-20。状态：按用户本次指令实施，交付后待人工验收。

## 背景与授权

用户要求依据 [PJ 计划书](../PJ-计划书.md) 和 [Review 1 计划](../Review1计划.md) 建立仓库结构、项目规则、AI 协作方式、CI 及 Agent Note 规范，随后追加使用 archify 按三组分工绘制项目逻辑图。两天计划限定本轮范围；长期计划中的部署、定时任务和跨模块写回继续保留为后续工作。

本任务使用上述计划已经选定的 FastAPI、SQLite、HTML/CSS、pytest，不改变业务契约；用户的实施指令是本次骨架工作的授权，不代表三组已经完成公共字段会议或 ADR 表决。

## 范围

- 根目录规则、使用说明、忽略规则、依赖清单。
- 可启动的 FastAPI 入口、三组模块包、D 公共子域目录、SQLite 连接与初始化入口。
- 统一的本地/CI 检查脚本、单个 GitHub Actions 检查 job、基础设施行为测试。
- 需求追踪、架构、协作、CI 文档，Issue/PR 模板和负责人映射。
- `.agents/notes` 生命周期、写作规范、格式检查，以及 ADR-001/002/003 提案。
- `docs/diagrams/` 下的三组路由架构图和可编辑源文件。

不在本任务实现预约、登录、审批、报修等业务功能；演示账号、公共业务表和真实种子数据由两天计划的任务 1 冻结后交任务 2。首个业务迁移仍使用 `V1__init.sql`，骨架阶段版本为 0，避免提前占用版本或虚构字段。生产部署、服务器配置和 GitHub 远端设置不属于本次本地变更。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A：只建空目录和文档 | 文件最少 | 启动命令和 CI 无法验证实际程序；三组仍需各自补入口 | 不采用 |
| B：可运行骨架与最小行为检查 | 三组共享入口、连接方式和可执行规则；可独立核对基础设施 | 增加少量基础代码和测试 | 按本任务授权采用 |

图按 G1/M1、G2/M2＋认证、G3/M3＋主数据组织，三个业务路由共用一个进程和数据库。图中待开发能力按计划标识，不将路由占位包装成已完成的业务接口。

## 预计改动

`AGENTS.md`、`README.md`、`.agents/notes/`、`.github/`、`app/`、`web/`、`database/`、`scripts/`、`tests/`，以及本任务新增的 `docs/` 文档。原始任务书和两份计划保留为输入依据。

## 验收标准

- Given 安装依赖并执行初始化，When 启动应用，Then 首页、健康检查和版本接口可访问；没有业务表时如实报告基础版本。
- Given 临时数据库和合法迁移，When 重放迁移及幂等种子两次，Then 数据不重复；失败迁移回滚且不提升版本。
- Given 合法 Note，When 执行格式检查，Then 返回 0；状态、章节或引用错误时返回非零。
- Given PR 或 main 更新，When GitHub Actions 执行，Then 同一个检查入口先校验规则、编译，再运行 pytest，任一步失败使 job 失败。
- Given 新组员或新 Agent 会话，When 阅读入口文件，Then 能找到任务范围、运行命令、边界、评审流程和提案规范。
- Given 三组分工，When 打开项目逻辑图，Then 能区分三组路由、公共层归属与共享 SQLite；附实际 archify 验收结果。

## 验证记录

2026-10-20 在 Windows PowerShell、项目 `.venv`、Python 3.10.0 上实际执行：

| 命令 / 检查 | 实际结果 |
|---|---|
| `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` | 四个直接依赖及所需间接依赖安装成功 |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note 检查、Python 编译通过；pytest 共 88 项通过，1 条依赖弃用提示 |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found |
| 临时数据库上两次 `python -m app.bootstrap --seed` | 两次退出 0，schema_version=0；当前空种子不产生业务数据 |
| 实际启动 `python -m uvicorn app.main:app`，使用本机 HTTP 请求 | 首页、CSS、健康检查和版本正确；三个未实现的业务前缀返回 404；结束后关闭进程并清理临时库 |
| 一次性 Python 相对链接核对 | 28 份 Markdown 文档无失效本地链接 |
| `git diff --check` | 退出 0；该命令只覆盖已跟踪文件的 diff |
| Archify 校验、交付和浏览器检查 | showcase 9/9、0 错误/警告，四种桌面尺寸无溢出；图及源文件摘要与交付回执一致 |

88 项测试包括 14 项应用、19 项 SQLite 初始化/事务和 55 项 Note 校验行为测试，不作为 M1/M2/M3/D 业务验收。唯一警告为 Starlette TestClient 提示现有 httpx 适配将弃用；依赖未更换，警告未屏蔽。

首次一次性 HTTP 冒烟脚本的中文页面断言受 PowerShell 管道编码影响失败；改为 Unicode 转义后完整通过，未为此修改应用行为。图的独立证据和检查范围见 [图说明](../diagrams/README.md) 与 [交付回执](../diagrams/project-logic.delivery.json)。

首次本地交付时尚未执行或未获确认：GitHub 远端 Actions、分支保护配置、成员账号映射、三组公共字段/角色会议、业务功能验收与服务器部署；当时未执行 Git 提交、推送或生产发布。人工验收与业务需求状态由对应责任人确认。

## 提交授权

2026-10-20，用户在审阅交付说明后明确要求执行 `git push`，授权提交并推送本次仓库骨架、项目图和随附文档。计划文档已由用户改名为 `Review1计划.md`，提交前同步相关链接。该授权不代表三组 ADR 表决、业务验收或生产发布已完成。
