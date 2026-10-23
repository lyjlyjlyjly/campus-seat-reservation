# 校园资源服务平台

课程实践项目，包含 M1 自习座位预约、M2 整教室申请与审批、M3 物业报修及公共层 D。使用一个 FastAPI 应用、SQLite 和 HTML/CSS，由三组协作开发。

当前交付为仓库基础结构：应用入口、首页、健康与版本检查、数据库初始化入口、CI、项目规则和协作模板。业务路由、登录、演示用户及业务表尚待各组实现。第一次 Review 范围以 [2026-10-20 至 2026-10-21 的 Review 1 计划](docs/Review1计划.md) 为准，完整需求与延期项见 [需求基线](docs/requirements.md)。

## 快速开始

在仓库根目录操作，使用 Python 3.10 或更高版本。CI 固定使用 Python 3.10；以下命令直接调用虚拟环境，不依赖终端激活策略。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.bootstrap
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Linux / macOS：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m app.bootstrap
.venv/bin/python -m uvicorn app.main:app --reload
```

浏览器访问 `http://127.0.0.1:8000/`；`/health` 检查已初始化的 SQLite，`/version` 返回运行版本。数据库缺失或不可用时健康检查返回 503，应先初始化；健康检查不会自动造库。

默认数据库为仓库内 `var/campus.sqlite3`。当前没有业务迁移，初始化后的 schema 版本为 0；真实 `V1__init.sql` 和演示种子由 G3 在公共字段冻结后汇总。不要将空库、包占位或首页当成三条业务链已经完成。详细约定见 [数据库说明](database/README.md)。

## 配置与检查

| 环境变量 | 默认值 | 用途 |
|---|---|---|
| `CAMPUS_DATABASE_PATH` | `var/campus.sqlite3` | SQLite 文件；相对路径以仓库根解析 |
| `CAMPUS_VERSION` | `dev` | `/version` 中的 tag 或 commit，便于后续追溯 |

应用读取进程环境变量，不自动加载 `.env`。Windows 可用 `$env:CAMPUS_DATABASE_PATH = 'var/demo.sqlite3'` 设置；切换数据库后应使用相同配置重新初始化和启动。演示种子通过 `python -m app.bootstrap --seed` 显式执行；目前种子脚本为空，不含演示账号。

在已激活的虚拟环境中执行：

```bash
python scripts/ci.py
python scripts/check_notes.py
python -m pytest tests/test_app.py tests/test_bootstrap.py
```

未激活时，将 `python` 换成上文的虚拟环境完整路径。统一 CI 入口依次检查 Note、编译 Python、运行 pytest；本地按改动选择必要检查，具体见 [CI 规范](docs/ci.md)。

## 目录

```text
AGENTS.md                  Agent 执行规则入口
.agents/notes/             ADR 理由、提案和生命周期规范
.github/                   CI、CODEOWNERS、Issue/PR 模板
app/main.py                单个 FastAPI 应用入口
app/common/                配置与 SQLite 连接
app/m1/                    G1：座位搜索与预约
app/m2/                    G2：整教室申请与审批
app/m3/                    G3：报修工单
app/d/                     公共子域：auth、audit、spaces
web/templates/             HTML 页面
web/assets/                CSS 与必要的原生 JavaScript
database/                  迁移和独立种子脚本
scripts/                   本地与 CI 共用检查入口
tests/                     基础设施及各模块行为测试
docs/                      需求、架构、任务规格和协作材料
```

三组路由和公共依赖见 [可交互项目逻辑图](docs/diagrams/project-logic.html)，可下载或直接用本地浏览器打开；[图源及验收说明](docs/diagrams/README.md) 随仓库保存。

## 参与开发

先读 [AGENTS.md](AGENTS.md) 和 [架构及分工](docs/architecture.md)。用 Issue 模板定义任务，在 [specs](docs/specs/README.md) 比较方案，经已有授权或人工确认后实现；提交前由组员审查 diff 和实际验收结果。持久决策使用 [Agent Note 规范](.agents/notes/README.md)，人类入口为 [决策索引](docs/decisions/README.md)。

安装本地的模块 push 检查（每个 clone 一次）：

```powershell
.\.venv\Scripts\python.exe scripts/install_git_hooks.py
```

Mac/Linux 在虚拟环境中执行 `python scripts/install_git_hooks.py`。若仓库已有 `core.hooksPath` 或已启用的 Git hook，安装器会停止并保留原配置；由维护者把现有 hook 与 `.githooks/pre-push` 合并后再调整。Windows 维护者新增或修改 hook 时，用 `git add --chmod=+x .githooks/pre-push` 保留 `100755` 可执行模式，确保 Linux/macOS clone 能运行。使用 `git fetch origin` 更新目标分支后，可先手动检查当前改动：

```powershell
.\.venv\Scripts\python.exe scripts/check_git_policy.py --base origin/main --head HEAD
```

每次 push 只推一个模块组的分支，每个 PR 也最多包含一个模块组。全局 `infra` 变更可独立推送，或随一个模块组配合；共享 D 根目录单独按 `d` 范围推送。分支、提交标题和 PR 标题均要遵守 [单模块推送规则与 Conventional Commit 格式](docs/specs/001-module-scoped-git.md)。共享契约和跨模块功能先拆分为单独的组内 PR；不要在同一次 push 中合并多个模块的实现。

[AI 协作说明](docs/ai-collaboration.md) 规定职责和证据；[工程伦理记录](docs/ethics-log.md) 只记录真实发生的事项；[发布流程](docs/release-process.md) 列出后续交付条件。

仓库内的 CI 文件需提交并推送到 GitHub 才会触发；分支保护、真实组员 CODEOWNERS 映射和服务器环境仍需负责人配置。本轮不部署生产环境，长期任务不会从需求清单中删除。
