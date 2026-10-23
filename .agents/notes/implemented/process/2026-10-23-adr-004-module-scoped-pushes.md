# Agent Note: ADR-004 每次推送只包含一个模块组

Status: implemented — 依据用户明确指令设为项目协作规则

Date: 2026-10-23
Owner: 项目负责人
References: [任务规格](../../../../docs/specs/001-module-scoped-git.md)、[Review 1 计划](../../../../docs/Review1计划.md)、[现有分工](../../../../docs/architecture.md)
Decision record: 用户于 2026-10-23 明确要求按模块逐次 git push，并遵守 Conventional Commits。

## Problem

G1、G2、G3 并行开发，各自维护不同业务与公共子域。把几组功能一次性放进一个推送，增加评审范围，也让一个组无法独立检查、追踪或回滚其改动。原有规则要求模块分支和 PR，却没有一次 push/PR 的模块边界或提交信息门禁。

本决策中的“一个模块”指负责组：G1 的 M1；G2 的 M2、认证与审计；G3 的 M3、空间主数据及其维护的 schema/种子。公共 D 根目录及应用共享基础设施是独立范围。文件归属取自当前 AGENTS 目录表，发生职责调整时通过新决策修改映射。

## Alternatives considered

| 方案 | 取舍 |
|---|---|
| 只在任务说明或 PR 模板写“请分开提交” | 操作简单，但遗漏时没有机器反馈，PR 仍可能同时修改多组目录 |
| 每个 push 检查一个负责组、本地 push 前运行 hook，并在 GitHub 对 push/PR 重查 | 能在启用 hook 时提前拒绝违规推送，PR CI 能补查漏装 hook 的情况；采用 |

AI 建议是给现有检查增加标准库 Python 门禁。本决策的约束由用户明确设定；ADR 记录不表示其他组召开或通过了投票。

## Decision

- 单次 `git push` 只推一个分支/ref；新增业务路径最多属于一个负责组。全局 `infra` 文件可单独推送或随一个负责组配合；同一 PR 也最多包含一个业务负责组，不能以多条提交规避这个边界。
- G1 对应 `m1`，G2 对应 `m2` 或其 D 子域 `d`，G3 对应 `m3` 或其 D 子域 `d`；独立共享 D 决策用 `d`，全局规则、CI、公共基础设施用 `infra`。M1/M2/M3 跨组功能先分开确认共享契约，再按依赖分成不同分支与 PR，每次依次推送一个组。
- 每条提交必须使用带 scope 的 Conventional Commit：`<type>(<scope>): <中文描述>`；破坏性变更用 `<type>(<scope>)!: <中文描述>`。允许 type：`feat`、`fix`、`docs`、`style`、`refactor`、`perf`、`test`、`build`、`ci`、`chore`、`revert`。scope 使用 `m1`、`m2`、`m3`、`d`、`infra`。提交同时修改一个业务组与全局 `infra` 文件时用业务组 scope；纯全局基础设施提交用 `infra`。
- 业务模块代码、对应测试和文档放进同一负责组的改动；G2/G3 的 `app/d/auth/`、`app/d/audit/`、`app/d/spaces/` 按上表归组；唯一数据库迁移入口及种子由 G3 管理。共享规则、入口文件和 CI 归 `infra`。全局文档可以配合一个模块 push，不能用它掩盖另一组的代码改动。
- 每个仓库 clone 执行 `python scripts/install_git_hooks.py`，安装 `.githooks/pre-push` 到该仓库。本地 hook 在 push 前检查 incoming 提交、路径归属、分支名称和提交信息；安装器遇到已有其他 `core.hooksPath` 时停止，不覆盖用户或其他工具的 hook。
- GitHub Actions 按每个分支 push event 检查对应 ref，并对 PR 检查分支累计范围、PR 标题和提交信息。一次本地 push 若更新多个 ref，会产生独立的 push event；ref 数量由本地 pre-push hook 检查。CI 能使 PR 的必需检查失败；禁止未经 PR 合并还须仓库负责人启用 main 分支保护和必需的 CI 检查。
- 违反范围时，以不同负责人分支和 PR 拆开。公共契约采用一个单独的 `infra` 变更或由相关组分别修改各自目录；仍需遵守人类评审流程。

本 ADR 决定的是代码推送的分组方式和消息格式，不记录功能完成、三组字段会议、组员评审、分支保护开启或部署完成。

## Consequences

多组协作工作需要拆分和安排依赖，相关 PR 可能串行合入；对应的接口和契约可单独审阅。本地 hook 只在 clone 已启用时提供 push 前检查，并可通过 `git push --no-verify` 跳过；GitHub Actions 会把对应 ref 或 PR 的违规检查标为失败，但 push event 不能拒绝分支 ref 更新，也看不到一次本地 push 同时更新的其他 ref。必须给 main 配置 PR 限制和必需检查来约束合并。责任路径和 Conventional Commit 规则由 [AGENTS.md](../../../../AGENTS.md)、[CI 规范](../../../../docs/ci.md) 与同目录门禁代码维护。
