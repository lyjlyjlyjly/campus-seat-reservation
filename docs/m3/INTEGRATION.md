# M3 整合交接（唯一维护入口）

本文件随每个 M3 批次更新；各批 spec 只记录范围、选择及验证并引用这里。当前批次：[M3-LOCAL-004](../specs/M3-LOCAL-004-persistence.md)。本次用户已授权模块按可替换的暂定契约独立开发，不再等待 P/G/S/D 全部回复、共享依赖合入或正式迁移编号；**暂定契约不等于团队批准**，公共接入由固定整合人员负责。

## 当前能力与边界

- **模块持久化已验证，公共基线接入待整合。** 本分支从 main `d8918bbc` 开发，已通过真实 SQLite 验证 M3 SQL、创建/按 ID 读取、升级保留数据、约束及失败回滚；用户于 2026-11-18 授权本批提交、推送、独立 PR 及向 `lyjlyjlyjly` 请求评审。人工验收与团队代码评审仍待进行；发布授权不等于验收或契约批准，实际 Git / PR 状态以远端记录为准。
- [PR #1](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/1) 是基础状态函数，[PR #2](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/2) 是通用文本规范化，[PR #3](https://github.com/lyjlyjlyjly/campus-seat-reservation/pull/3) 是整体契约提案；本批未合并、复制或改写这些 PR。正式创建业务接入时复用已经合入的函数。
- 尚无真实创建 HTTP/表单、登录授权或对象访问控制；没有派单/开始维修接口、座位报修、验收评价、超时及 M3→M1 联动。repository 接收上层传入的身份，不代表已登录或获授权；不能直接作为无鉴权写入口。缺少共享认证时不得默认登录或放行请求。
- 不改默认开发库、公共初始化器、已有 V1、共享种子或其他组业务；本分支默认初始化仍不安装 M3 表。

## 实际路径与调用约定

| 入口 | 当前职责 / 后续适配位置 |
|---|---|
| [app/m3/sql/repair_order.sql](../../app/m3/sql/repair_order.sql) | 唯一 M3 SQL 源；字段、四分类、1–1000 Unicode 码点、外键、三状态 NULL 组合及索引；没有版本/事务 PRAGMA |
| [app/m3/repository.py](../../app/m3/repository.py) | `create_repair_order(database_path, *, reporter_id, room_id, fault_type, description) -> int`；`get_repair_order(database_path, order_id) -> dict 或 None`。时间由服务端生成，独立连接、绑定参数、异常回滚、只写 repair_order；读取不隐含对象授权 |
| [tests/m3/conftest.py](../../tests/m3/conftest.py) | 临时迁移组装及真实共享数据夹具；只在 pytest 临时目录使用 V1 + 临时 V2，无正式版本占号 |
| [app/bootstrap.py](../../app/bootstrap.py) / [app/common/db.py](../../app/common/db.py) | 复用 `initialize_database(..., migrations_dir=...)` 及 `connect_database`，没有修改公共实现 |

类型或 ID 不合法时 repository 抛出 `ValueError`；分类、长度、NUL、外键等存储约束失败保留 `sqlite3.IntegrityError`；库/表未初始化保留 `sqlite3.OperationalError`，不偷偷修库。HTTP 错误转换留给后续真实创建业务入口，不把 SQLite 错误正文直接泄漏给用户。

## 外部依赖与固定测试快照

当前 main 无正式共享业务迁移，采用用户指定仓库 `lyjlyjlyjly/campus-seat-reservation`、提交 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042` 的原始 [database/migrations/V1__init.sql](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/database/migrations/V1__init.sql)，逐字节保存为 [tests/m3/fixtures/V1__init.sql](../../tests/m3/fixtures/V1__init.sql)。**只供测试，不是第二份正式 V1**；未复制 M2 业务实现，也未手写假用户/房间表。

- 源 schema 版本：1；大小：3588 字节；Git blob：`9e811019bda02bb8a2fefac2712ec1fe6fb96a61`。
- SHA-256：`a23f6dbaed498d2bfda0d5942306a6d3535b8bf8f724ed0401474ac57259d319`。测试组装前实际校验，根 `.gitattributes` 保持 SQL 为 LF；更新依赖须重新记录来源及校验，不能静默改快照。
- 依赖字段：`app_user(id, status)` 及既有授权表；`room(id, name, capacity, is_active)`。工单的 reporter/assignee/assigner 引用真实 app_user，room_id 引用真实 room；ON DELETE RESTRICT 保留历史。角色/ACTIVE 校验不是外键保证的能力。
- 认证参考同提交的 [app/d/auth/dependencies.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/dependencies.py)：`current_user`、`require_permission(code)`；[app/d/auth/users.py](https://github.com/lyjlyjlyjly/campus-seat-reservation/blob/dd7474918e9ca956e8fb2549fd6ea0ee1ac58042/app/d/auth/users.py)：`SessionUser(id, username, display_name, roles, permissions)`，会话 Cookie 为 campus_session。此代码尚未作为本批真实集成依赖运行。
- 后续认证/权限转换集中放在一个 M3 创建服务入口；房间读取集中在 M3 repository 的一个读取入口或整合人员指定的 D 函数中，不散落到页面。当前没有创建服务或房间列表需求，不提前建空适配器；这里的入口安排不是已存在文件链接。

## 暂定规则与可调整位置

- 首阶段仅房间报修。**is_active=0 暂按“停借但资产仍存在”处理，允许报修**；当前存储层只要求房间存在，不以 is_active 筛除。后续房间列表与创建校验共用集中读取入口，若整合时改变含义，只在该入口调整并补行为测试。capacity 不限制报修，不写 room/M1 表；座位仍未实现。
- 分类为 ELECTRICAL（电气故障）、WATER（给排水故障）、FURNITURE（家具故障）、OTHER（其他故障）。repository 不强转非字符串，先 strip；SQL 是当前四分类及长度的约束入口。PR #2 的宽松函数保持不变，后续创建业务层复用它并增加具体错误定位，不能把规范化通过等同报修创建合法。
- 描述保存 strip 后的 1–1000 个 Unicode 码点，中文/非 BMP 字符按字符而非 UTF-8 字节计数；保留正文内部空白，不截断、不做额外 Unicode 合并。SQL 显式列出与 Python 3.10 strip 一致的空白字符，直接写入未规范化文本也拒绝。升级 Python 时须复核该集合。
- **本批技术边界：拒绝描述中的 U+0000（NUL）**。SQLite length(TEXT) 在它之前停止计数，会与 Python len 产生偏差，因此 SQL 用 instr 排除；这会拒绝含 NUL 的输入，PR #2 本身仍可接受该字符串，限制只在存储/后续创建业务层生效。
- REPORTED：assigned_to、assigned_by、assigned_at、started_at 全部 IS NULL；ASSIGNED：前三项 IS NOT NULL、started_at IS NULL；IN_REPAIR：四项全 IS NOT NULL。status 自身 NOT NULL 且限三值。数据库约束只保证字段组合，不代表实现了合法状态转换或操作者权限；后续派单/开始维修仍需 PR #1、事务内重查与条件更新。
- created_at/updated_at 由 repository 生成 UTC `YYYY-MM-DDTHH:MM:SSZ`，初始相同。数据库外键不代替真实认证、ACTIVE/角色检查、对象授权或后续并发更新检查。

沿用五权限提案，初始化及最终授权由整合人员与 G2 处理：

| 权限 | 暂定授权 |
|---|---|
| repair:report、repair:read_own | student、teacher、org_leader、approver、repairer、admin；本人报修/本人查询 |
| repair:assign | admin；管理派单 |
| repair:read_assigned、repair:start | repairer；仅本人受理工单，开始时须 ASSIGNED |

维修资格仍为 ACTIVE + repairer + repair:start，普通 admin 不自动获得维修能力。详情暂定未登录 401、缺功能权限 403、具体工单不可见/不存在均同一 404；本批没有 HTTP 接口，未验证这些响应。

## 正式接入步骤与责任

1. 整合人员核对最新 main 的完整迁移历史、用户/角色/房间实际字段及共享认证入口。已有正式迁移时优先使用它们验证，不把测试快照拷回公共目录，不修改已提交 V1；与当前快照不同的部分显式适配并补测试。
2. 分配真实新迁移编号和编写人，将已经验证的 M3 SQL **迁入公共迁移目录**。同一接入变更删除 `app/m3/sql/repair_order.sql` 的副本并更新本文件、测试 SQL 引用，明确公共版本迁移是唯一维护位置，避免双份 SQL 分叉。之后 schema 变化新增版本，不重写已提交迁移。
3. 测试改为组合正式完整迁移历史，移除对旧快照的运行依赖；核验空库、旧库升级、重复执行、真实数据保留和所有约束，不能仅改预期版本号使测试通过。
4. 权限初始化由迁移/整合负责人按 G2 确认的五权限映射写入正式后续版本，保留原 room 授权；不由 M3 请求写授权表。共享测试由其负责人调整 `tests/d/test_auth_schema.py` 等“版本固定为 1、权限数 2、全表映射四行、student 完全无权限”的假设，保留原 M2 授权断言；M3 只维护本模块测试。
5. 后续创建批接通真实认证、集中房间读取、服务层分类/长度/错误转换、接口和表单。身份取真实 current_user，写前检查报修权限和真实位置；缺依赖时拒绝正常请求，不用测试身份兜底。schema 约束和当前 repository 不构成该批的完整授权实现。

## 可复现验证与接入后清单

在项目根目录 PowerShell 执行（仅写 pytest 临时库，不初始化默认开发库）：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/m3/test_schema.py tests/m3/test_repository.py -q
.\.venv\Scripts\python.exe -m pytest tests/m3 -q
.\.venv\Scripts\python.exe scripts/ci.py
```

2026-11-12 实际结果：上述命令依次为 **99 passed、99 passed、187 passed**；完整检查中的 Note 与编译也通过。解释器 Python 3.10.20；每次仅有既有 Starlette/httpx 弃用警告，未屏蔽。详细执行耗时见本批 spec；未运行真实认证/HTTP/公共迁移集成验收。

测试使用真实 SQL/初始化器/连接，不 mock 数据库；fixture 的虚构用户没有登录用途，既有 M2 申请记录只存在于临时库中，用于证明升级未破坏业务数据。临时故障触发器仅用于证明 repository 事务回滚，不进入应用 SQL。

整合后的验收清单（目前未完成）：

- [ ] 正式迁移空库/旧库/重复执行均通过，旧用户、房间和 M2 业务记录保留；SQL 只有一处维护来源。
- [ ] 五权限初始化和共享测试按真实基线通过；未知用户/房间及非法 NULL 组合仍被数据库拒绝。
- [ ] 真实登录用户选真实房间提交，201 与数据库本人名下 REPORTED 一致；非法输入、未知房间、未登录及无权限不留工单。
- [ ] 停借房间规则、对象访问响应、服务端身份/时间和失败回滚通过真实接口验收；没有默认登录或测试适配器进入正常路径。
- [ ] 派单/开始维修另批接入事务内资格检查、状态规则及条件更新；当前表结构不等于这些功能交付。
