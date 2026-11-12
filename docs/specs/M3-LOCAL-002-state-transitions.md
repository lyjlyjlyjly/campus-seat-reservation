# M3-LOCAL-002：工单基础状态转换校验

日期：2026-11-12（北京时间）。需求：M3-R02、M3-R03 的基础状态规则。Issue：未创建。状态：基础状态规则完成并通过本地测试，尚未接入接口与持久化；用户已在本次会话明确人工验收通过，并授权提交、推送本批三个文件及创建 PR。团队代码评审仍待进行，提交、推送和合并状态以实际 Git/PR 记录为准。

## 背景、授权与基线

用户本次明确调整顺序：先实现不依赖认证和数据库的独立状态规则函数，暂不开发迁移或持久化。该指令覆盖本批实施，不需要重复确认。本任务的范围、方案、函数约定、验收和结果均完整记录于本文，不依赖此前尚未提交的契约提案。旧准备文档保留原样且不纳入本批提交，公共契约提案也不因此获批。

2026-11-12 执行 `git fetch origin`（使用上轮已核实的系统代理，仅命令级配置）成功，远端无更新：main 为 `d8918bbc6cdb59fdf5f7450b3c71b7950cf8fb5b`，M2 为 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042`，infra 为 `bc1f1354c4b21eefdc718ffbd05912c734366070`。M2/infra 仍未合并。本批从 origin/main 创建 `m3/local-002-state-transitions`，没有引入其他分支代码。

依据：[AGENTS.md](../../AGENTS.md)、[docs/requirements.md](../requirements.md)、[docs/architecture.md](../architecture.md)、[docs/Review1计划.md](../Review1计划.md)。本批只实现用户确认的现有状态顺序，不新增公共状态名、权限或接口契约。

## 范围与方案

| 方案 | 收益 | 代价与结论 |
|---|---|---|
| 直接嵌入接口判断 | 在接口已存在时可就地校验 | 当前没有派单或维修接口，会迫使本批引入未获准依赖，也容易重复判断；不采用 |
| 独立状态规则函数 | 无认证/数据库依赖，可直接测试并供后续业务调用 | 后续业务必须显式调用，并在其事务中重新核实实际状态；按用户明确选择采用 |

仅新增：

- `app/m3/state_rules.py`：状态转换校验及明确异常。
- `tests/m3/test_state_rules.py`：调用真实规则函数的成功及拒绝测试。
- 本文件：授权、边界、方案、验收与实际验证。

不修改原契约 spec、需求基线、迁移、用户/权限表、公共认证、M1/M2、CI、AGENTS.md、路由或页面。不实现真实派单、操作者权限、数据库更新、并发控制、超时升级、验收评价、M3→M1 联动，不增加依赖或临时 HTTP 接口。后续范围继续保留在需求基线，真实集成条件见本文末尾。

## 函数约定

`app.m3.state_rules.validate_transition(current_state: str, target_state: str) -> None`：

- 仅允许 `REPORTED → ASSIGNED`、`ASSIGNED → IN_REPAIR`；合法时返回 None，表示校验通过，不表示工单已更新。
- 跳级、逆向、重复以及任一端的未知状态均抛出 `InvalidStateTransition`（ValueError 子类）；异常带中文原因以及 `current_state`、`target_state` 属性，调用方无需解析消息即可取得输入。
- 严格接受现有大写状态字符串，不自动去空白或转换大小写；非字符串也作为未知状态拒绝。PENDING_ACCEPT、DONE 尚不属于本批可接受状态。
- 函数没有用户、工单对象、连接、时间或 HTTP 参数，不修改输入/数据库/全局状态；不决定 HTTP 状态码。

后续派单/开始维修逻辑须先接入真实认证与权限，再在实际写事务内读取工单状态、调用此函数并执行条件更新。纯规则函数不能防止检查后的竞争，不替代操作者授权、合法维修人员校验或持久化约束。

## Given–When–Then 验收与测试范围

| Given | When | Then |
|---|---|---|
| REPORTED，目标 ASSIGNED | 调用实际校验函数 | 正常返回 None |
| ASSIGNED，目标 IN_REPAIR | 调用实际校验函数 | 正常返回 None |
| REPORTED，目标 IN_REPAIR | 尝试跳级 | 抛 InvalidStateTransition，携带原始状态对 |
| ASSIGNED→REPORTED、IN_REPAIR→ASSIGNED 或 IN_REPAIR→REPORTED | 尝试逆向转换 | 均拒绝 |
| 三种已知状态各自作为起点和终点 | 重复进入当前状态 | 三种情况均拒绝 |
| 当前、目标或两端未知，含空串、拼写错误、大小写/空白变体、后续阶段状态 | 调用校验函数 | 明确报告未知状态，不隐式接受或修正 |
| 任一端非字符串 | 调用校验函数 | 同样抛 InvalidStateTransition，而非意外的容器/hash 错误 |

测试显式覆盖三种已知状态的全部九种组合，另覆盖未知输入；不从实现的转换表推导预期，不 mock 被测规则，不用常量存在断言替代行为。数据库未改变、API 权限正确等集成结论不在本批测试能力之内。

执行顺序：`.\.venv\Scripts\python.exe -m pytest tests/m3 -q`，然后一次 `.\.venv\Scripts\python.exe scripts/ci.py`。另检查新文件空白/链接、Git 范围及旧 spec 的 SHA256；原 SHA256 为 `D186109F3001840F0E45F7B8B72A52175CD564BD9D4208A0362448461ABFE275`。

## 实际结果与交接

2026-11-12，使用项目虚拟环境 Python 3.10.20 实际执行：

| 命令 / 检查 | 实际结果 |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests/m3 -q` | 26 passed，1 warning，0.12s；两条合法、七条已知状态非法组合、十一条未知状态及六条非字符串输入均覆盖 |
| `.\.venv\Scripts\python.exe scripts/ci.py` | Note、编译通过；114 passed，1 warning，5.43s；All checks passed。包括原有 88 项与新增 26 项 |
| `.\.venv\Scripts\python.exe -S -` 执行一次性直接调用检查 | 不加载 site-packages，两条合法转换返回；跳级、逆向、重复和未知状态均抛出 InvalidStateTransition；没有使用 HTTP 或数据库 |
| 旧 spec SHA256 与 Git 范围复核 | 旧文档与上文哈希一致；只有本批三个新文件和原先未提交的 M3-LOCAL-001；没有已跟踪文件修改或暂存内容 |

没有测试失败；唯一警告是原有共享 conftest 导入 TestClient 时的 Starlette/httpx 弃用提示，与上一轮相同，未屏蔽或更换依赖。基础状态规则已实现、已本地测试；用户随后在会话中明确人工验收通过，该确认不替代团队 PR 代码评审。提交前核对规则和测试源码与上述测试时一致，仅修订本文的独立阅读、验收状态和可移植命令说明，沿用已实际执行的测试结果。没有执行数据库、认证集成或故意破坏实验，不把本批结果写成这些工作已验证。本轮不声称 M3-R02/M3-R03 全部完成，不更新共享需求基线的交付状态。

PowerShell 人工复核（在正式工作副本中执行）：

```powershell
# 在正式 Git 工作副本的仓库根目录执行
.\.venv\Scripts\python.exe -m pytest tests/m3/test_state_rules.py -v
.\.venv\Scripts\python.exe -S -c "from app.m3.state_rules import validate_transition; validate_transition('REPORTED', 'ASSIGNED'); validate_transition('ASSIGNED', 'IN_REPAIR'); print('OK')"
```

第一条测试命令应显示 26 项通过，可逐项查看拒绝场景；第二条直接调用应输出 OK。若将第二条中的目标改成 REPORTED→IN_REPAIR，则应抛 InvalidStateTransition、进程非零退出，这是预期拒绝。无临时网页或接口可供浏览器验收。

后续真实集成仍需：原 V1 与 G2 认证/RBAC 进入共同基线；工单表/外键及迁移编号和负责人确认；M3 权限码、合法受理人及对象级权限确认；共享 schema 测试与种子的责任划分；在数据库事务中调用本函数并完成条件写入。上述工作不由本批自动授权。

本批提交标题：`feat(m3): 增加工单基础状态转换校验`。用户已明确授权提交、推送本批三个文件并创建以 main 为目标的小范围 PR；原 M3-LOCAL-001 文档不纳入，不开始下一批、不合并 PR、不虚构评审人。首次实际成功推送后单独记录北京时间、SHA 与下一批最早可推送时间（加 30 分钟），不以 commit 时间替代 push 时间。
