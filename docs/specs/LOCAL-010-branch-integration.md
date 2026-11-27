# LOCAL-010：按责任组合入现有分支成果

日期：2026-11-27。范围：现有 infra、G2 和 G3 分支的主分支整合。状态：infra 与 M3 源码、交接文档已分批合入；共享数据库和认证公共层待跨组人工评审，G2 后续批次尚未合入。

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

### 实际顺序与范围

2026-11-27 核对来源 refs、工作区与祖先关系后，先合入仓库门禁。公共数据库和认证公共层的跨组人工评审尚未记录，因此先接收可以独立保存源码、保持拒绝未认证请求的 M3 批次。M3 仍使用原临时库测试边界，未把测试迁移或身份装配作为正式运行环境。

每个批次从当时最新的 `origin/main` 建立独立分支；M3 使用带来源标记的单个原提交，再为规格入口或已有用例的依赖条件做小提交。G2 数据库、口令工具及文档按目录导入，避免把原分支的跨组历史或旧 scope 混入新的 PR。只对无冲突、检查通过的 PR 执行合入；保留原来源分支及提交。

### 已接收与待评审批次

以下 head 是对应整合 PR 的最终提交，合入 SHA 是该批更新 main 后的提交；均为短 SHA，可从 PR 查到完整值。CI 一栏记录新整合提交的自动 push／PR 检查，不引用旧来源的测试结果。

| 批次 | PR | head | 合入 SHA / 状态 | 自动 CI |
|---|---|---|---|---|
| infra 规则、门禁和 Review1 删除 | [#10](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/10) | `b1b5bd2` | `8597d2e`，已合入 | push／PR 均成功 |
| G3 共享数据库 V1、种子与说明 | [#11](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/11) | `271ba2e` | 待跨组人工评审，未合入 | push／PR 均成功 |
| M3 独立状态规则 | [#12](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/12) | `de08821` | `2a27963`，已合入 | push／PR 均成功 |
| M3 独立文本规范化 | [#13](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/13) | `fe25617` | `3483f57`，已合入 | push／PR 均成功 |
| M3 契约提案文档 | [#14](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/14) | `c5c35d7` | `bc2385a`，已合入；仍是提案 | push／PR 均成功 |
| M3 持久化 | [#15](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/15) | `3c4799c` | `b3c0523`，已合入 | push／PR 均成功 |
| G2 spec 与 ADR 编号整理 | [#16](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/16) | `63504f8` | `170ae3c`，已合入 | push／PR 均成功 |
| G2 口令公共工具与原有用例 | [#17](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/17) | `bfa6826` | 待跨组人工评审，未合入 | push／PR 均成功 |
| M3 创建接口与表单 | [#18](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/18) | `3215bae` | `f1875fc`，已合入 | push／PR 均成功 |
| M3 本人工单查询 | [#19](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/19) | `a16f1be` | `812ff1f`，已合入 | push／PR 均成功 |
| M3 手动派单 | [#20](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/20) | `8ca0188` | `b9a9b62`，已合入 | push／PR 均成功 |
| M3 本人受理及开始维修 | [#21](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/21) | `c922f3a` | `a6d1b74`，已合入 | push／PR 均成功 |
| M3 交接与历史状态修订 | [#22](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/22) | `11051d2` | `bd73a23`，已合入 | push／PR 均成功 |

原 #1–#9 的内容已通过上述新 PR 接收，对应旧 PR 均已关闭，原分支保留。公共入口说明随独立 infra 文档批次维护，其检查以所在 PR 为准。

### 实际检查与差异

- 整合使用的 clone 已安装 `.githooks`；每批执行 `python scripts/check_git_policy.py --base origin/main --head HEAD`，实际 push 也通过本地门禁。每次只更新一个分支/ref、最多一个业务责任组，提交标题使用对应 Conventional Commit scope。
- `python scripts/check_notes.py`、Python 编译及 `git diff --check` 已按改动执行；文档批次另做普通 Markdown 相对文件链接检查。没有跳过门禁、删除拒绝断言或关闭错误处理。
- 本地行为测试未运行；远端既有 CI 自动执行 Git 规则、Note、编译和 pytest。Node 页面测试本次未运行，远端 CI 也未包含 Node。原 spec 的实验与数量保留原日期，不作为本次重跑证据。
- M3 005–008 只修改既有用例的外部依赖前置条件：缺认证时显式模拟 `app.d.auth.dependencies` 缺失，缺登录页时显式隔离 `/m2/login` 路由。原测试函数、成功／拒绝断言、真实 service、SQL 与事务保留；未额外编写新测试或按实际响应生成预期结果。
- 比对确认，M3 业务源码及页面与 `c3369bf` 一致，另纳入独立的 `state_rules.py` 和 `report_validation.py`。这两个函数尚未由现有 service/model 统一复用，不能把文件合入视为调用整合完成。
- G2 原 V1 与 M3 固定测试快照的 Git blob 均为 `9e811019bda02bb8a2fefac2712ec1fe6fb96a61`；#11 原样保留 V1，未新增正式 M3 迁移或 repair 权限。
- 通过远端 `ls-remote` 再次核对 11 个原来源分支，均仍指向本任务记录的原始提交；没有删除分支、强推或改写来源历史。
- ADR-004 继续作为已采纳的单模块推送规则；会话提案改为 ADR-005，仍为 proposed。G2 spec 使用 G2-LOCAL-001/002，活动入口不再引用已删除的 Review1 文件。

### 剩余依赖与验收边界

1. [AGENTS.md](../../AGENTS.md#目录与边界) 要求公共层/schema PR 由另一组成员实际评审。#11、#17 尚无记录，不能将 Agent 自查或 CI 成功当作人工批准。其余 G2 会话／认证装配及 M2 申请审批源码已核对来源，仍需在前置评审和合入后按 G2 范围分批接收。
2. main 默认初始化仍为版本 0，种子未安装演示账号。M3 正式工单迁移、五项 repair 权限映射、真实共享登录联调及浏览器人工验收尚未接入；这些缺口不在本任务中新增公共契约或依赖来填补。
3. 需求状态以 [需求基线](../requirements.md) 为准；M3 调用、迁移及验收前置只在 [M3 交接](../m3/INTEGRATION.md) 维护。源码、自动 CI、完整业务交付和人工验收分别记录。
4. 本轮未修改 GitHub 分支保护设置。PR、必需检查和跨组评审的远端强制策略仍须由负责人配置，不能仅凭 YAML 宣称开启。
