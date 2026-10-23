# SPEC-001：按模块分批推送与提交规范门禁

日期：2026-10-23。状态：按用户明确指令实施。范围负责人：项目负责人。

## 背景与授权

用户要求后续 Git 推送一个模块一个模块进行，提交遵循 Conventional Commits，不允许先改写多个模块再一次性推送。当前仓库已规定中文提交、模块分支名与 PR review，但没有定义“一次推送最多触及哪些模块”，也没有可执行检查。

本规格把模块按已确认的分工责任组定义：G1/M1；G2/M2 与 auth/audit；G3/M3 与 spaces、迁移和种子。共享基础设施及全局文档使用 `infra` scope，可与一个模块组的工作同一推送，但不能把两个业务组的源码、测试或模块目录放进一次推送。此定义来自现有 AGENTS 目录分工；具体业务字段和跨组协议仍由组员确认。
同一提交包含单一业务组和全局基础设施文件时使用业务组 scope；纯基础设施提交使用 `infra`，公共 D 根目录使用 `d`。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A：只补写 AGENTS 和 PR 模板 | 改动少、容易阅读 | 开发者容易漏看，CI 无法拒绝跨模块变更，个人 clone 的 push 也没有拦截 | 不采用 |
| B：规则文档、Conventional Commit 校验、本地 pre-push hook 与 GitHub CI 检查一致 | push 前拦截已安装 hook 的跨组推送；CI 能拦截漏装 hook 的变更和无法合并的 PR | 初次 clone 需启用项目 hook；GitHub 分支保护仍需仓库负责人配置 | 按用户授权采用 |

AI 初始实现建议：采用 B，用标准库 Python 提供统一路径与提交检查，避免额外依赖。规则的来源是用户对模块分批推送与 Conventional Commits 的明确要求，不代表已取得其他组成员的独立表决。

## 范围

- 项目规则说明模块与共享职责如何映射到一次 push。
- 本地 pre-push hook 检查一次 push 涉及的全部 incoming commit、文件和 ref，拒绝多个非删除 ref；GitHub push workflow 按事件检查对应 ref。
- GitHub PR 检查分支累计范围、分支名前缀、PR 标题和 Conventional Commit scope。GitHub 为一次 push 中更新的多个 ref 分别触发事件，完整 ref 数量由本地 hook 检查。
- 给出安装与本地手动执行命令；保留现有测试依赖，不加入包管理器。

本变更只实现门禁。GitHub 分支保护需仓库负责人配置；门禁不实现或发布业务跨模块功能。

## 预计改动

`AGENTS.md`、`README.md`、`docs/ci.md`、`docs/ai-collaboration.md`、`docs/decisions/README.md`、`.github/pull_request_template.md`、`.github/workflows/ci.yml`、`.githooks/`、`scripts/check_git_policy.py`、`scripts/install_git_hooks.py`、检查器测试和关联 ADR。

## 验收标准

- Given 一个分支 push 或 PR 同时含 M1 与 M2 文件，When pre-push hook 或对应的 CI 检查执行，Then 返回非零并指出责任组 G1 和 G2。
- Given 一次 push 只改 G2 的 M2 与 auth/audit，When 使用合法范围和 Conventional Commit，Then 检查通过。
- Given 一次 push 只改 G3 的 M3、spaces 或初始化脚本，When 使用合法范围和 Conventional Commit，Then 检查通过。
- Given 单模块路径却使用错误 scope、没有 scope 的提交信息或拼错 type，When 检查执行，Then 返回非零并说明允许格式。
- Given 一个 Git push 同时更新多个 ref，When hook 检查执行，Then 拒绝该 push 并建议一次只推一个模块分支。
- Given push 尝试删除 `main` 或 `master`，When pre-push hook 检查执行，Then 拒绝该 push。
- Given push 尝试直接更新 `main` 或 `master`，When pre-push hook 检查执行，Then 拒绝该 push。
- Given 单个模块 PR、匹配的分支名/PR 标题和合法提交，When CI 执行，Then 策略检查通过；改成多个组或错误 Conventional Commit 时，Then CI 失败。
- Given 全局 `core.hooksPath` 已由他人或其他工具配置，When 安装项目 hook，Then 不覆盖现有配置并告知如何处理。

## 实际验证

- `python -m pytest tests/test_git_policy.py -q`：23 项通过；有一条现有 Starlette/httpx 弃用警告。测试覆盖合法单组、跨组、scope 错误、Conventional Commit 错误、跨组重命名、多 ref push、纯基础设施提交、main/master 更新与删除拒绝，以及安装器保留既有 hook。
- `python scripts/ci.py`：通过；本地策略检查使用 `origin/main..HEAD`，Note 格式与链接检查、Python 编译通过，完整测试 111 项通过，有一条 Starlette/httpx 弃用警告。
- `git diff --check` 和 `git diff --cached --check`：通过。
- 当前 clone 已将 `core.hooksPath` 配置为 `.githooks`；临时本地 bare remote 验证 Git for Windows 会调用 pre-push hook。Git index 中 hook mode 为 `100755`。
- 未执行远端 push 或 PR；GitHub `main` 分支保护与必需检查仍需仓库负责人配置和验证。
