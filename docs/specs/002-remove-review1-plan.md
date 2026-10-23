# SPEC-002：移除 Review 1 计划并修复文档引用

日期：2026-10-23。状态：按用户明确的删除与推送要求实施。

## 背景与授权

用户已删除 `docs/Review1计划.md` 并要求再次推送。仓库规则、需求基线、CI 说明、图示说明和历史任务记录仍引用该文件；保留这些链接会导致文档入口失效。

本任务只处理该文件的删除、当前维护入口的引用修复和历史记录说明。需求细节以 `docs/requirements.md` 为准，分组及依赖关系以 `docs/architecture.md`、`docs/PJ-计划书.md` 为准；不重建已删除计划中的独立任务表。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A：只提交计划文件删除 | 改动最少 | `AGENTS.md`、需求和图示文档继续指向不存在的文件 | 不采用 |
| B：提交删除并把有效入口指向现有基线/架构文档 | 保留需求、范围和依赖的可达入口，清理失效链接 | 需同步少量规则、说明和历史记录 | 采用 |

## 范围与约束

- 保留 `docs/Review1计划.md` 的删除，不恢复文件。
- 将当前使用中的范围链接改指 `docs/requirements.md`，将集成依赖链接改指 `docs/architecture.md`。
- 在 SPEC-000 中保留该计划曾作为原始依据的历史事实，并说明当前仓库已删除该文件。
- 所有变更均属于 `infra`；提交使用带 `infra` scope 的 Conventional Commit，一次只推当前分支。
- 不重写 PJ 计划书，不改业务模块代码，不改变需求验收口径。

## 预计文件

`docs/Review1计划.md`、`AGENTS.md`、`README.md`、`docs/ci.md`、`docs/requirements.md`、`docs/diagrams/README.md`、`docs/specs/000-repository-bootstrap.md`、本规格，以及 ADR-001 和 ADR-004 的引用行。

## 验收标准

- Given 计划文件已由用户删除，When 查看当前规则和文档入口，Then 不再有链接指向 `docs/Review1计划.md`，需求范围可从 `docs/requirements.md` 进入，架构依赖可从 `docs/architecture.md` 进入。
- Given 原始骨架任务记录需保留历史，When 阅读 SPEC-000，Then 可知道 Review 1 计划曾是输入依据且该文件现已从仓库删除。
- Given 本任务全部变更均属 `infra`，When 创建提交并推送，Then 提交格式符合 `docs/specs/001-module-scoped-git.md`，pre-push 门禁通过，且仅更新 `infra/spec-001-module-scoped-git` 一个分支。

## 验证计划

- 检查仓库 Markdown 链接与 Note 引用，不残留指向已删除计划的活动链接。
- 运行 `python scripts/check_notes.py` 和 `git diff --check`。
- 推送前运行现有 pre-push 门禁；不重跑与本次文档删除无关的业务测试。
