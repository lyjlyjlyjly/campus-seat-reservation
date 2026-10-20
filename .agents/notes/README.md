# Agent Note 编写规范

本目录保存会影响后续工作的决策及其理由。根 [AGENTS.md](../../AGENTS.md) 是执行规则入口；[决策索引](../../docs/decisions/README.md) 面向组员和老师。ADR 正文只在这里维护，spec、README 和会议记录通过链接引用。

## 何时写

下列问题通常值得记录：公共层归属、认证方式、模块边界、跨模块契约、schema 演进策略、CI/测试策略，以及值得防止反复重议的否决方案。

局部重命名、机械修复、普通页面调整和执行日志写在 spec/PR，不新建 ADR。新建前搜索已有 Note 和决策索引；同一问题的补充事实通常更新原 Note，改变已采纳的结论才创建替代 Note。

## 路径、编号和状态

```text
.agents/notes/{status}/{topic}/yyyy-mm-dd-adr-NNN-short-topic.md
status = proposed | implemented | rejected
topic  = feature | bug-fix | simplification | architecture | process | testing
```

- 日期用记录创建日，必须是真实日历日期；slug 使用小写英文、数字和连字符。例：`2026-10-20-adr-001-public-layer-ownership.md`。
- `ADR-NNN` 至少三位数字，全仓库唯一且不复用。新增前搜索现有最大编号；并行任务先认领编号，出现冲突由负责人协调。
- 一个决策始终只有一个文件。改变状态时移动原文件，保留日期、编号和 slug；同步标题之外的状态、必要章节以及所有入站链接。
- 主题按“这个决定主要影响什么”选择，每篇只属于一个主题；不为同一 ADR 在多个目录复制正文。
- 空的状态目录可以保留 `.gitkeep`，主题目录在需要时创建。本项目不使用 `archived/` 或 `superseded/` 状态目录。

| 状态 | 含义 | 谁提供依据 | 退出方式 |
|---|---|---|---|
| `proposed` | 尚待评审的建议；可在授权的试验中验证 | Agent/组员起草，明确待确认项 | 明确采纳后移至 implemented；有价值的否决移至 rejected |
| `implemented` | 已明确采纳的决策，包括约定的工作方式 | 人的确认、PR 或会议记录 | 被新决策取代时仍留在原目录并标记关系 |
| `rejected` | 明确否决且值得保留理由的方案 | 人的否决依据 | 条件改变后用新 Note 重新提案，保留旧理由 |

`implemented` 只代表决策被采纳，不等于业务功能、部署或人工验收已完成。用户对具体任务的明确授权可作该范围的依据，但不能推断三组已开会、投票或批准未来范围。

## 固定格式

前三行必须为标题、空行、状态行；状态说明非空，使用下例中的长破折号 `—`。文件中的状态必须与所在目录相同。

```markdown
# Agent Note: ADR-004 简短且具体的决策标题

Status: proposed — 等待受影响组评审

Date: 2026-10-20
Owner: 负责协调的组或已确认的负责人
References: [相关任务](../../../../docs/specs/000-repository-bootstrap.md)

## Problem
```

`Date` 与文件名日期一致，`Owner` 写真实责任归属；尚未分配个人时写组名或“待分配”。外部链接可用完整 URL，仓库文件使用相对链接。不得把本机绝对路径写进 Note。

正文第一个二级标题必须是 `Problem`。下表各节必须有实质内容，英文标题保持精确拼写，正文以中文为主。

| 状态 | 必需章节 |
|---|---|
| 全部 | `Problem`、`Alternatives considered` |
| proposed | `Proposal`、`Acceptance criteria`、`Risks` |
| implemented | `Decision`、`Consequences` |
| rejected | `Why rejected`、`Reconsider only if` |

已采纳的 Note 不保留 `Proposal`、`Plan`、`Acceptance criteria` 等待实施章节：将决策结果写进 `Decision`，后续任务链接到 spec/Issue。采纳时增加 `Decision record:`；否决时增加 `Rejection record:`，指向真实确认依据。没有依据就继续保持 proposed。

## 内容如何写

- **Problem**：谁遇到什么问题、已有约束、当前证据；把事实、假设和待确认项分清。
- **Alternatives considered**：至少比较两种可行方案，说明收益、代价以及采用或放弃的理由。记录 AI 初始建议、人的最终选择或“尚待确认”；不能把未发生的讨论写成历史。
- **Proposal / Decision**：写具体职责、边界或行为，链接相应文件。不要粘贴聊天推理、整份方案或大段代码。
- **Acceptance criteria**：写可核对的结果，尽量用 Given–When–Then；尚未运行的检查写“待验证”。
- **Risks / Consequences**：写真实代价、限制和受影响方；不要只写“无风险”或宣传性结论。
- **Why rejected / Reconsider only if**：说明何种约束导致否决，哪些事实改变后才值得重议。

优先解释代码和测试无法直接表达的取舍。短段落，一个段落一个意思；表格只用于并列方案。只记录实际运行的验证、实际发生的确认和可追溯的链接，不代填评审人、票数、测试通过或发布日期。

## 状态变化与替代

普通补充可在同一 PR 修正文件路径、名称和事实，并保留原结论及历史理由。推翻已采纳的结论时：

1. 新建 proposed Note，在 `References` 关联旧 Note；提案阶段尚未取代旧规则。
2. 人明确采纳后，把新 Note 移到 implemented，写入实际 `Decision record`。
3. 在新 Note 加入 `Supersedes: ADR-001 ([原决策](相对路径.md))`，在旧 Note 加入 `Superseded by: ADR-004 ([替代决策](相对路径.md))`。
4. 两边必须互指正确编号和文件，禁止自指或循环；旧 Note 留在原目录，不重写旧理由。
5. 同一 PR 更新根规则、索引和受影响 spec；阅读当前依据时沿 `Superseded by` 找到最后一篇已采纳 Note。

本轮采用一对一替代关系。需要合并多个决策时，先拆成能独立说明影响的 Note，不引入复杂的决策图。

## 提案模板

复制模板到相应主题目录，替换编号、日期、路径及所有占位内容；模板本身不算决策。

```markdown
# Agent Note: ADR-004 决策标题

Status: proposed — 等待相关组确认

Date: 2026-10-20
Owner: 待分配
References: [任务规格](../../../../docs/specs/000-repository-bootstrap.md)

## Problem
问题、约束和证据。

## Proposal
拟议选择、影响范围、尚待确认的事项。

## Alternatives considered
至少两种可行方案及取舍；AI 初始建议；人的选择尚待确认。

## Acceptance criteria
可观察、可核对的通过条件。

## Risks
代价、限制与后续验证。
```

采纳后保留 `Problem` 和 `Alternatives considered`，用以下章节替换提案章节，并在元数据中写 `Decision record:`：

```markdown
## Decision
实际采纳内容、适用范围和确认依据。

## Consequences
收益、承担的代价、实现与后续任务链接。
```

否决时保留问题与候选方案，写 `Rejection record:` 并使用：

```markdown
## Why rejected
真实否决理由和依据。

## Reconsider only if
明确、可判断的重新考虑条件。
```

## 检查与评审

在仓库根执行 `python scripts/check_notes.py`，或统一执行 `python scripts/ci.py`。格式检查验证路径、日期/编号/状态一致性、必需章节、相对链接、确认字段和替代互链；失败返回非零并给出文件位置。

工具不能证明方案有道理、确认真实发生或验收确实通过。人仍需审查：至少两个方案是否可行、理由是否源自本项目、权限和跨组影响是否明确、确认和测试记录是否可信、是否与现有规则矛盾。检查实现与边界见 [CI 规范](../../docs/ci.md)。
