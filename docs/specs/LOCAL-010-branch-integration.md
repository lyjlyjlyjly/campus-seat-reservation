# LOCAL-010：按责任组合入现有分支成果

日期：2026-11-27。范围：现有 infra、G2 和 G3 分支的主分支整合。状态：实施中，结果以各批 PR 与检查记录为准。

## 范围与约束

- 保留来源分支及原提交，按 [Git 规则](../../AGENTS.md#git-与交付) 分批建立 PR；每次提交、推送及 PR 最多涉及一个业务责任组。
- 先接入规则门禁，再按依赖整合数据库、认证、教室申请与 M3 各批成果。每批进入 main 后重新核对下一批的基线与实际差异。
- 保留 `docs/Review1计划.md` 的删除；角色事实维护在 [需求基线](../requirements.md) 和相关规格中。
- 保留已提交 V1 的原始内容；本任务不新定共享业务字段、角色权限或新的依赖。
- 认证提案继续保持 proposed。修正 ADR/SPEC 编号重叠及活动链接，不把代码合入当作团队批准或人工验收。
- M3 的正式工单迁移、正式 `repair:*` 权限初始化和跨模块写回不在来源分支中，继续作为待接入事项记录。已有独立规则模块也不因合入而自动代表被所有业务入口复用。
- 原分支记录的测试与故意破坏实验保留原日期；本次未执行的项目不能沿用历史结果宣称通过。

## 候选方案

| 方案 | 收益 | 代价与结论 |
|---|---|---|
| A：将全部来源分支直接合入一个整合分支，再统一提交 PR | 保留所有旧提交，操作少 | G2 历史 scope 不符合现门禁，累计改动横跨 G2/G3/D，且文档存在删除与编号冲突；不采用 |
| B：infra 与合规 M3 批次保持小批历史，G2 按责任组导入内容并记录来源 | 保留来源证据，每个 PR 的范围与提交可独立审查 | 需要整理 G2 路径、文档链接及现有模块共存假设；采用 |

不强推、不改写来源分支，也不通过跳过门禁或删除拒绝路径取得检查通过。发生实际 Git 冲突时按仓库规则处理，不盲目合并。

## 来源与批次

远端分支于 2026-11-27 经 `ls-remote` 与 fetch 核对；当时 main 为 `d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b`。

| 批次 | 来源 | 责任与安排 |
|---|---|---|
| 规则基线 | `infra/spec-001-module-scoped-git`，`bc1f135` | infra；门禁、协作规则和 Review1 删除 |
| 公共数据库基线 | `m2/g2-login-and-room-application`，`dd74749` 的 `database/` | G3；原样导入 V1、种子及其说明 |
| 登录会话 | 同上，`app/d/auth/` 及装配、已有认证测试 | G2；认证测试归入 `tests/d/auth/` |
| 教室申请与审批 | 同上，`app/m2/`、已有页面与 M2 测试 | G2；与认证分开形成小批提交 |
| 文档整理 | G2 需求、架构、两份 spec 与会话 ADR | infra；认证 ADR 改为 ADR-005，spec 使用 G2-LOCAL 前缀，保留原理由与状态 |
| M3 契约提案 | `infra/m3-contract-proposal`，`f1e1820` | infra；仅纳入提案，不宣称公共契约获批 |
| M3 状态规则 | `m3/local-002-state-transitions`，`5dd7cd5` | G3；独立于 004–009 链 |
| M3 文本校验 | `m3/local-003-report-validation`，`8011cfe` | G3；独立于 004–009 链 |
| M3 持久化至开始维修 | `fa5a35b` → `49892f7` → `e1fbd94` → `094f12d` → `c3369bf` | G3；按 004→005→006→007→008 的依赖顺序逐批 |
| M3 交接文档 | `m3/local-009-integration-review`，`5af01c2` | G3；更新整合事实，保留未完成依赖 |

## 预计文件

- infra：本规格、`docs/requirements.md`、`docs/architecture.md`、`docs/decisions/README.md`、相关 `docs/specs/` 和会话提案。
- G3 数据库批次：`database/README.md`、`database/migrations/README.md`、`database/migrations/V1__init.sql`、`database/seed.sql`。
- G2：`app/d/auth/`、`app/m2/`、`app/main.py`、`tests/conftest.py`、`tests/d/auth/`、`tests/m2/` 及现有 M2 页面资源。
- G3 业务：`app/m3/`、`tests/m3/`、`web/templates/m3/`、`web/assets/m3/`、`docs/m3/` 及对应规格。

## Given–When–Then 验收

- Given 全部来源分支及各自固定提交，When 整合完成，Then main 包含各批预期文件，独立的 M3 002/003/契约提案均有可追溯的合入记录。
- Given G2 原历史包含旧 scope 和跨组路径，When 发布新的整合批次，Then 来源历史保持不变，新提交及 PR 按实际文件归属通过门禁。
- Given 已删除 Review1 计划以及重复的 ADR/SPEC 编号，When 阅读当前入口，Then 删除保持、编号唯一、链接有效，角色与权限事实没有丢失。
- Given G2 身份接口与 M3 身份适配同时存在，When 复核模块行为和既有检查，Then 区分未登录与认证模块缺失，不以关闭鉴权或跳过断言解决差异。
- Given M3 正式迁移和权限初始化尚未落地，When 汇报交付，Then 明确区分源码合入、可运行范围、CI 结果和人工验收。
- Given 每一批可合入 PR，When 更新 main，Then 保留小批提交证据，不直接推送 main，不将多个责任组装进一次 push 或 PR。

## 检查与交付记录

- 2026-11-27：核对来源 refs、工作区与分支祖先关系；原工作区及用户的新 clone 保持其现有分支与文件。
- 规则基线：`python scripts/install_git_hooks.py` 已为整合使用的 clone 安装 hook；`python scripts/check_git_policy.py --base origin/main --head HEAD`、`python scripts/check_notes.py`、`git diff --check` 通过。
- 本次行为测试尚未运行；原分支历史结果不作为本次整合证据。后续 PR 检查与人工审阅按实际结果追加。
- 公共层/schema 的跨组人工评审尚未记录；不得填写未实际参与的审阅人。
