# DeepSeek Harness 的人机协作开发：工程管理拆解

> 对象：本地克隆的 `F:\gitlab\deepseek-harness`（master @ 46a7f68，2026-06-10 到 2026-09-23，共 19,676 个提交，22 个 tag）。
> 下面每条结论都附了仓库里的出处，可以对照着读。

## 0. 先看结论

这个仓库的代码基本是编码 Agent 写的（Codex、Claude Code 之类）。Agent Note 原文写着：*"This codebase is developed primarily by coding agents. Agents follow enforced gates far more reliably than prose conventions"*（`.agents/notes/implemented/process/2026-06-11-quality-gates.md`）。

整套工程管理可以压成四句话：

1. **人定规则、做裁决；Agent 干活、交证据。** 人负责写 AGENTS.md、Agent Note 和 review，以及最后决定合不合并。Agent 负责实现、测试、写文档、写 PR。
2. **能机器检查的规则，一律变成会让 exit code 非零的脚本。** 只写成文字的约定，Agent 很容易忘掉。`scripts/` 下光 `verify-*` 就有 69 个。
3. **决策的"为什么"单独留档（Agent Note），并且有生命周期。** 这样换一个 Agent 会话、换一个人，前面定下的事不会被反复推翻。
4. **Git/GitHub 流程全部显式化：** worktree 隔离、原生 stacked PR、lease 保护的改写、标签分类、加权审批、分序列发版。

规模数据可以感受一下：约 15 名主要提交者，三个半月提交近两万次，平均每人每天几十次，人手一个 Agent 是常态。分支名里大量出现 `worktree/*`、`codex/*`，就是 Agent 在独立 worktree 里干活留下的痕迹。

---

## 1. 给 Agent 的"操作系统"：分层的 AGENTS.md

### 1.1 入口

- 根目录 `AGENTS.md`（约 18KB）是总规则。`CLAUDE.md` 只有一行 `AGENTS.md`，是指过去的符号链接。这样 Claude Code、Codex 等不同 Agent 读到的是同一份规则，不会各维护一份。
- `.claude/skills` 同样链接到 `../.agents/skills`，技能也只存一份。
- 全仓库有 21 个 `AGENTS.md`，就近生效：`packages/AGENTS.md` 管包的编写，`docs/AGENTS.md` 管文档，`.github/AGENTS.md` 管 CI，`snapshots/AGENTS.md` 管快照归属，等等。Agent 改到哪个目录，就读到那里的局部规则。

### 1.2 根 AGENTS.md 写了什么（值得学的结构）

| 段落 | 作用 |
|---|---|
| 仓库布局 | 一行一个包、一句话职责，Agent 不用自己去摸 |
| Commands | 每条命令都标了"什么时候用、要不要 API key" |
| Run relevant checks locally | **不准默认跑全量测试**，要按改动面挑最小证据；全量交给 CI |
| Conventions | 几十条硬规则，大部分都有对应的 gate 或链接到决策记录 |
| Editing these instructions | 规则本身怎么改：编辑真实文件、每条规则自包含、字数超预算就去调 `verify-doc-budgets` |

重点在于：几乎每条规则后面都挂着 `[rule](...)` 或 `[why](...)`，链接到 Agent Note。**AGENTS.md 只放"做什么"，"为什么"放在 Agent Note 里**，这样 AGENTS.md 能保持精简，Agent 的上下文不会被撑爆。

### 1.3 Skills：把多步流程打包成按需加载的说明书

`.agents/skills/` 下有 14 个技能，每个都是一个 `SKILL.md`，frontmatter 的 `description` 写明触发条件：

| 技能 | 什么时候触发 |
|---|---|
| `dsh-pre-push-checks` | push、标记 ready 或声称"检查通过"之前，用来挑最小必要检查 |
| `dsh-code-review` | review PR 时，先给出本仓库的阻断项清单 |
| `dsh-merging-stacked-prs` | 合并一串依赖 PR 时 |
| `dsh-ci-test-reliability` | 改动涉及异步、持有资源的测试时 |
| `dsh-prose-standard` | 写注释、文档、提示词时 |
| `dsh-archive-agent-notes` | 归档旧决策记录时 |
| `dsh-translate-docs` | **只能由人显式调用** |
| `agent-experience` | 设计给 Agent 用的工具和技能本身时 |

`agent-experience` 这个技能值得单独一读，它是"怎么给 Agent 设计上下文"的元原则：先暴露最少信息，细节按需加载；关键约束（权限、破坏性操作）要出现在动作之前；输出要有界，给 ID 或路径让 Agent 自己再去取。

**责任划分的体现：** 大部分技能 Agent 可以自己触发，但"翻译文档"这类成本高、需要人判断质量的流程，写死了只能由人发起。

---

## 2. 决策留档：Agent Note 机制

这是这个仓库最有特色的设计，也最适合学。

### 2.1 为什么需要它

Agent 没有长期记忆。每次新开会话，它看到的是现成的代码，却不知道"为什么不用 X"。如果不留档，它就会一次次提出已经被否掉的方案，人也得一次次解释。Agent Note 专门记录**代码和文档表达不了的部分：为什么这么做、放弃了什么**。

### 2.2 目录 = 状态 × 分类

```
.agents/notes/{lifecycle}/{class}/yyyy-mm-dd-topic.md
lifecycle: proposed / implemented / rejected / archived
class:     feature / bug-fix / simplification / architecture / process / testing
```

- `proposed/`：提案，还没实现。人和 Agent 可以先在这里对齐方案，再动手。
- `implemented/`：已上线的决策。**代码变了，Note 里的路径、名字、默认值要在同一个 PR 里同步更新**；但决策本身不能改，推翻决策要写一篇新 Note 并互相链接。
- `rejected/`：被否的提案。只有在它能"阻止一个诱人的错误"时才保留，否则删掉。
- `archived/`：冻结的历史，永远不再编辑，也不再作为当前依据。

### 2.3 固定格式，由 gate 强制

- 头三行固定：`# Agent Note: 标题`、空行、`Status: proposed|implemented|rejected — 原因`。
- 正文必须以 `## Problem` 开头。
- `proposed` 要有：Proposal / Alternatives considered / Acceptance criteria / Risks。
- `implemented` 要有：Decision / Alternatives considered / Consequences，**并且禁止出现** `## Plan`、`## Acceptance criteria` 这类规划用语（已上线就写现状）。
- **`## Alternatives considered` 必须有。** 原文的理由是：*"A decision recorded without what it beat invites re-litigation"*（没写清赢过了谁的决策，迟早被重新争论）。

这些规则由 `scripts/verify-agent-note-format.ts`、`verify-agent-note-classification.ts`、`verify-archived-agent-notes.ts` 检查，归档文件还要用 hash 校验，保证没人改过。

### 2.4 什么时候写、什么时候不写

> 只在"代码、测试、现有文档都解释不了的持久决策理由"时写；机械性或局部改动（包括局部 UI 调整）不写。

这条很关键。否则 Agent 会给每个 PR 都写一篇 Note，最后变成噪音。

### 2.5 一个完整例子

`implemented/process/2026-08-02-native-github-stacks-and-optional-rebases.md`：

- Problem：只用 base 分支表示的 PR 链，GitHub 不知道它是一个整体，合并时要手动逐个 retarget。
- Decision：两个以上相互依赖的 PR 必须用 GitHub 原生 stack；merge-forward 和 rebase 都允许，但改写历史必须带 lease。
- Alternatives：列了 4 个被否方案和各自的理由。
- Consequences：写清得到了什么、付出了什么。

---

## 3. 质量门禁：把规则变成会失败的命令

### 3.1 核心理念

> Every mechanically checkable AGENTS.md promise gets a command that exits non-zero.
> （AGENTS.md 里每一条能机器检查的承诺，都配一条会以非零码退出的命令。）

还有一句很实在：*"'a lot of work' is not a cost argument when agents do the labor"*。干活的是 Agent，"工作量大"不再是放松标准的理由。所以这里的标准高得离谱：

- TypeScript 开到最严（`noUncheckedIndexedAccess`、`exactOptionalPropertyTypes`）
- `packages/*/*/src` **逐文件 100% 覆盖率**（真不可达的分支用 `/* v8 ignore */` 并写明原因）
- oxlint 类型感知规则 + jscpd 跨文件重复检测
- 每个导出都必须有 JSDoc（`verify-export-jsdoc`）
- 禁止新增 `as unknown` 强转（`verify-no-unknown-casts`，只允许存量减少）
- 客户端 UI 文案禁止硬编码（`verify-client-ui-i18n`）
- 甚至检查用词：`verify-concrete-terms` 会拦下 "boundary/shape" 这类含糊词

### 3.2 三层门禁，按成本分工

| 层 | 跑什么 | 原则 |
|---|---|---|
| pre-commit（`lefthook.yml`） | 暂存文件 lint 并自动修复、空白字符、vendor 清单、翻译配对 | **必须快**，只抓便宜的错误 |
| pre-push | 增量 typecheck | 只做这一件 |
| 本地手动（Agent 自选） | 按 `dsh-pre-push-checks` 挑跟改动面对应的最小测试 | **不准默认全量** |
| CI（`ci.yml` / `ci-master.yml`） | 全量矩阵：Node 22/24/26、Windows 原生、覆盖率、构建冒烟 | CI 负责穷尽 |

这里有个很实用的经验：**Agent 天生喜欢"保险起见跑一遍全量测试"**，既浪费时间，也挤占上下文。这个仓库明确禁止这样做，并要求 Agent 在 PR 里**"只报告实际跑过的命令"**，不许声称跑过没跑的东西。

### 3.3 改动范围先算清楚

`pnpm run change-scope --base <已核实的 base>` 输出一份 JSON，列出已提交、暂存、未暂存、未跟踪的文件。Agent 先看清"我改了什么"，再挑检查项。注意，这个命令**故意不猜 base**：base 必须由 Agent 去远端核实后传进来，避免拿过期的 base 算错范围。

### 3.4 快照测试：锁住"模型看到了什么"

AGENTS.md 有一条：**"Model-visible ⟺ logged"**（模型能看到的东西，都必须能从 session 日志里重建出来）。配套的做法是：任何模型或用户可见的行为变化，都要更新 `snapshots/` 下"无需 API key 的录制会话回放"快照。这对 Agent 产品特别重要，提示词、工具输出的格式悄悄变了，单测发现不了，快照能发现。

---

## 4. 版本控制与迭代

### 4.1 分支：一个任务一个 worktree

- 合并记录里的分支前缀：`worktree/*`（最多）、`fix/*`、`feat/*`、`codex/*`、个人名前缀、`rel/*`（发版）。
- 规则：**"One worktree per PR branch."** 并行修复绝不共用同一个 checkout。多个 Agent 同时干活时，各自在自己的 worktree 里，互不踩脚。
- 为此他们还专门解决了一个坑：所有 worktree 默认共用同一套 git hooks，一个 worktree 里 `pnpm install` 就会覆盖其他 worktree 的 hook。解法是给每个 worktree 设置独立的 `core.hooksPath`（`2026-07-27-worktree-local-lefthook.md`）。**多 Agent 并行开发一定会撞上这个问题。**

### 4.2 提交信息

Conventional Commits，按近 3000 条统计：`fix` 约 850、`test` 约 400、`feat` 约 260、`docs` 约 235、`refactor` 约 140、`perf`、`release`。scope 是包名，比如 `fix(plugins): ...`、`feat(chat): ...`。

### 4.3 历史策略：允许 rebase，禁止裸 force

AGENTS.md 里的原话是 "Choose PR history deliberately"：

- 相互独立的改动拆成不同的 PR；bug 修在**引入它的那个 PR** 上，再往上传播。
- merge-forward 和 rebase 都允许，review 之后也可以。
- 改写远端历史只能用 `--force-with-lease`，远端有变动就中止；**禁止裸 `--force`**。
- 如果正在 merge-forward 时 base 又前进了，要先保住当前的 merge 检查点，再去合新的 tip。

这些规则是写给 Agent 的。Agent 在冲突时很容易"一把 force push 解决"，把别人的提交冲掉。

### 4.4 Stacked PR（依赖链）

大功能会拆成 `A ← B ← C` 一串 PR，每个都基于下面那个。规则如下（`dsh-merging-stacked-prs` + `docs/cookbook/responding-to-pr-review-on-a-stack.md`）：

1. 必须用 GitHub 原生 stack 对象（`gh stack link`），以 `PullRequest.stack` 字段为准，不靠分支名推断。
2. 链上作者都是同一个人，Agent 可以自动 link；**作者不同，必须先问人**。
3. 不准自动解散或重建已有的 stack，冲突时交给人决定。
4. 合并用 `gh stack merge`，**不准**降级成逐个 `gh pr merge` 再手动 retarget。
5. review 修复要修在引入问题的那一层，然后逐层向上传播；每个 review 修复保持独立 commit，不 amend 掉。
6. `gh stack sync` 会先推送再验证，这是唯一允许"先推后测"的例外，推完必须马上验证每一层，验证通过前不准合并。

这里体现的责任划分是：**可逆、只影响自己的操作，Agent 自己做；会影响别人或不可逆的操作（动别人的 PR、解散 stack），停下来问人。**

### 4.5 CI 节奏

- `ci.yml` 只服务 PR；`ci-master.yml` 只在 master push 时跑平台全矩阵（macOS、ARM 等），这样 PR 不会被慢平台拖住。
- 同一 ref 的新提交会取消旧的 CI 运行（`cancel-in-progress`），Agent 高频 push 时省下大量 runner。
- 一个排障经验写进了技能：PR 显示 "no checks reported" 时，先看 `mergeStateStatus`。处于冲突状态的 PR，GitHub 根本不会触发 workflow；这时空提交、切换 draft/ready 都没用，只能解决冲突。这条是 Agent 踩坑之后总结出来的。

### 4.6 发版：三条独立序列 + alpha/rc

`2026-08-10-npm-release-sequences.md`：

| 序列 | 内容 | tag |
|---|---|---|
| dsh | 产品主体，所有包统一版本号 | `dsh-v0.1.7-rc.1` |
| vendor | 9 个 vendored 的 Cordis 包，各自独立版本 | `vendor-<pkg>-v<ver>` |
| native | 原生插件 | `node-addon-system-v<ver>` |

三条序列互不触发、互不等待。发版本身也走 PR：开 `rel/dsh-0.1.7-rc.1` 分支，一个 `release(dsh): 0.1.7-rc.1` 提交改全部 package.json 的版本号，合并后由 `release.yml` 打包、`release-publish.yml` 发布。节奏是 `alpha.1 → alpha.2 → rc.1 → rc.2 → …`。

---

## 5. 人怎么把关：Review 与审批

### 5.1 PR 模板要求"证据"

`.github/pull_request_template.md` 只有三节：

- **Motivation**：一句话说明问题，并写上 `Fixes #NN` / `Related #NN`
- **Changes**：接口变化、可观察行为变化（没有就写 None）
- **Testing**：每种测试方法一条，**证据（输出、截图、录屏）放进折叠的 Proof 块**

Agent 写的 PR，人最怕"它说测过了"。这个模板逼 Agent 把可复核的证据贴出来。仓库里还有 `record-browser-gif` 技能，专门让 Agent 给 Web 改动录 GIF 当证据。

### 5.2 Issue 与标签

- Issue 模板只有三种：Bug / Feature / Task。
- 每个 PR 必须有**恰好一个** `kind/*`（feature、bug-fix、doc、testing、cleanup、dependency 六选一），**至少一个** `area/*`，最多一个优先级 `p0–p3`，并且至少引用一个同仓库的 Issue。
- 这些规则由 `issue-policy.yml` workflow 强制检查，不合规的 PR 过不了。
- Issue 状态自动流转：开 PR 时变成 In progress，请求 review 时变成 In review，被要求修改时回到 In progress。

### 5.3 加权审批：谁的 approve 更有分量

这里没有用"需要 N 个 approve"，而是用分数（`.github/review-ownership/`，由 `weighted-approval.yml` 执行）：

- 合并需要 **2 分**。
- 普通 reviewer 1 分；`approval-policy.json` 里指定的几位核心维护者 2 分。
- **按代码归属加权：** 系数为 `min(2, 1 + 4 × 该 reviewer 写过的被改旧行数 / 被改旧行总数)`，用 git blame 在 merge base 上计算。也就是说，你改了谁的代码，谁的 approve 就更值钱，归属超过 25% 就直接算满 2 分。
- **作者经验分：** 每合并过一个 PR 加 0.011 分，上限 1.1 分。老作者加上一位普通 reviewer 就能过线，但作者分单独永远不够。
- `/delegate @someone`：在单个 PR 里把自己的票权委托给别人，防止重复计分。
- 有任何阻断性 review（request changes），状态一直保持 pending。

对人机协作的意义：Agent 产出量极大，人的 review 带宽是瓶颈。用代码归属自动找到"最懂这块代码的人"，让他一票就够，可以把有限的人力用在最该用的地方。

### 5.4 Review 看什么

`dsh-code-review` 技能明确：**"a short review with one substantiated blocker is better than a list of nits"**（一条有根据的阻断意见，胜过一堆鸡毛蒜皮）。优先看正确性、生命周期、安全；还会专门审"新写的文字"（注释、文档、提示词），因为 Agent 写的注释最容易变成啰嗦的推理过程记录。

### 5.5 对 Agent 产出的态度：信任，但要验证

`responding-to-pr-review-on-a-stack.md` 里有一段可以直接抄：

> 把委派出去的修复当作"信任但验证"：子 Agent 的报告描述的是意图，不一定是实际落地的东西。要自己在真实代码树上重跑 gate；对回归测试，要证明它在未修复的代码上会**失败**（引入回归 → 看到红 → 还原）。一个两种情况都通过的守卫，什么也守不住。子 Agent 如果把问题重新表述成"已经处理过了"，这就是你该亲自深挖的信号。

---

## 6. 从事故中学习：Postmortem

`docs/postmortem/` 有 4 篇，格式包括：Executive summary / Summary / Impact / Timeline（引用 session 日志的事件序号作为证据）/ 修复。

0003 号很典型。一个 Web Agent 改了 GUI，却不知道自己跑在哪个 URL 上：它先把验收甩给用户，然后把 HTTP 200 当成成功（实际页面是白屏），最后去验证了另一个端口上的新服务器。修复方案不是"提醒 Agent 小心点"，而是**把当前 URL 和运行模式变成模型可见、shell 可查的信息，并在启动前拒绝错误的运行方式**。

套路就是：**Agent 犯了错，不去加一句提示词恳求它，而是改环境，让错误不可能发生，或者能被机器发现。**

---

## 7. 文档纪律（Agent 写文档时的防"水"规则）

`docs/AGENTS.md` 里的"slop checklist"，适合原样搬到任何 Agent 项目：

- 文档只写**当前状态**，历史放 commit、PR、Agent Note。
- **一个事实只有一个出处**，其他地方链接过去。
- 不写"implemented!"、"future: …"这类状态标注，因为状态会过期。
- 删掉推理过程记录：逐步实现的叙述、对显而易见分支的论证、测试流程复述。
- 不滥用强调：到处加粗等于没有重点。
- 每份文档有字数预算（`verify-doc-budgets`），一段一行（`verify-md-wrap`），文档里的 ts 代码块必须能编译（`doc-typecheck`）。
- 中英双语：每篇有 `.md`、`.zh.md`，外加一个 `.i18n.yaml` 记录配对 hash。改了英文不改中文，pre-commit 就会拦下来。

---

## 8. 责任划分总表

| 事项 | 人 | Agent | 机器（gate/CI） |
|---|---|---|---|
| 写规则（AGENTS.md、skills） | 定方向、审批 | 起草、维护 | 字数预算、链接有效性 |
| 架构决策 | 拍板 | 写 proposed Note、列备选方案 | 格式、分类校验 |
| 实现 + 测试 + 文档 | — | 全包 | 类型、lint、100% 覆盖、JSDoc、i18n |
| 选择本地检查 | — | 按改动面挑最小集合，只报实际跑过的命令 | pre-commit/pre-push 兜底 |
| 全量验证 | — | — | CI 多平台矩阵 |
| PR 元数据 | — | 写模板、加 kind/area 标签、关联 Issue | issue-policy 强制检查 |
| Review | 裁决，按归属加权 | 辅助 review、修 review 意见 | 加权审批打分 |
| 动别人的 PR、解散 stack、跨作者 link | **必须确认** | 停下来问 | — |
| 改写历史 | — | 只用 lease 改写 | 禁止裸 force |
| 高成本流程（如全量翻译） | **只能由人发起** | — | — |
| 发版 | 发起 rel 分支、合并 | 改版本号 | 打包、发布 workflow |
| 事故复盘 | 确认根因 | 写 postmortem、改环境 | 新增 gate |

---

## 9. 搬到自己项目里：从小到大的落地清单

不用一次照搬（他们的 gate 多到夸张）。按投入产出比排个序：

**第一步（半天）：**
1. 根目录写 `AGENTS.md`，`CLAUDE.md` 链接到它（Windows 下没有软链就写一行 `@AGENTS.md`）。内容包括：目录职责、命令表、"本地只跑相关测试"、几条硬约定。
2. PR 模板：Motivation / Changes / Testing + Proof。
3. 提交规范：Conventional Commits，scope 用模块名。

**第二步（一两天）：**
4. 建 `.agents/notes/{proposed,implemented,rejected}/`，规定**必须写 Alternatives considered**；只为持久决策写，机械改动不写。
5. pre-commit 只放快检查（lint --fix、空白）；pre-push 放 typecheck；其余交给 CI。
6. 一个任务一个 git worktree，分支名前缀统一（比如 `wt/<topic>`）。

**第三步（逐步加）：**
7. AGENTS.md 里每写一条"必须……"，就问一句：能写成脚本吗？能，就加一个 `verify-*`，挂到 CI 上。
8. 把多步流程（push 前检查、review、合并 stack）写成 skill，description 里写清触发条件。
9. 给面向模型的输出做快照测试。
10. Agent 犯错时写 postmortem，修复手段优先改环境或加 gate，最后才考虑改提示词。

**最小 AGENTS.md 骨架：**

```markdown
# AGENTS.md

一句话说明项目。改 src/ 前先读 docs/architecture.md。

## Layout
src/api/    HTTP 接口
src/core/   业务逻辑
tests/      测试

## Commands
pnpm test -- <file>   # 只跑相关文件
pnpm typecheck
pnpm lint

## Run relevant checks locally
- 按改动面选最小测试；不要默认跑全量，CI 负责全量。
- PR 里只报告实际运行过的命令及其结果。

## Git
- 一个任务一个 worktree / 分支；bug 修在引入它的 PR 上。
- 改写远端历史只用 --force-with-lease；禁止 --force。
- 动别人的 PR / 分支前先问人。

## Conventions
- （每条规则一行；能机器检查的标注对应的检查命令）
- 决策理由写到 .agents/notes/，这里只链接。
```

---

## 10. 几个值得记住的原句

- *"Agents follow enforced gates far more reliably than prose conventions."*：写在文档里的规则会被忘掉，写成 gate 的规则不会。
- *"A decision recorded without what it beat invites re-litigation."*：不写备选方案，决策迟早被推翻重议。
- *"Never default to the full suite or repeat a passing check."*：别让 Agent 用全量测试来求心安。
- *"A guard that passes both ways guards nothing."*：回归测试要先证明它会红。
- *"Tests describe behavior, not correctness."*：行为变了就连同测试一起改，并在 PR 里说明原因。
