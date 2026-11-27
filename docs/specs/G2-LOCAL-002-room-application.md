# G2-LOCAL-002：教室申请与一级审批

原任务日期：2026-10-20。原分支记录：方案已由用户确认，按模块实施，交付后待人工验收。

2026-11-27 文档整合草稿，来源为 `dd7474918e9ca956e8fb2549fd6ea0ee1ac58042`。原编号为 SPEC-002，整合时改用组内任务编号。以下实现说明已按该分支代码校正：房间列表为 `GET /m2/rooms`，时长上限为 `app/m2/times.py` 中固定的 `MAX_HOURS = 4`。2026-10-21 的结果和实验保留原日期与命令；本次未重新执行这些验证。

需求：[M2-R01](../requirements.md)（申请角色门槛）、[M2-R02](../requirements.md)（教室、时段、用途和人数）、[M2-R03](../requirements.md) 的一级审批部分。认证前置见 [G2-LOCAL-001](G2-LOCAL-001-auth-session-rbac.md)。

## 背景与原任务依据

原分支记录：用户（G2 负责人）在 2026-10-20 确认 `room:apply` 授予 `teacher` 与 `org_leader`、`student` 不授予，并要求页面采用静态 HTML + 原生 JS 调 JSON 接口。本任务实现 `/m2` 下“登录 → 申请 → 一级审批”这条主链。原 Review 1 计划文件现已删除，当前范围见 [需求基线](../requirements.md)。

二级审批（M2-R03 剩余部分）、超时撤销（M2-R04）、申请人撤销（M2-R05 未实现部分）、审批占用 M1 座位（M2-R06）、D-R05 审计均按计划延期；本人列表和受控详情查询已包含在该分支实现中。

## 范围

- `room_application` 表（DDL 见下）与只读的 `room` 主数据引用。
- 接口：`GET /m2/rooms`（登录后读取可申请房间）、`POST /m2/applications`、`GET /m2/applications`（本人申请，可按状态筛选）、`GET /m2/applications/pending`（审批人待审列表）、`GET /m2/applications/{id}`（本人或有审批权限者查看详情）、`POST /m2/applications/{id}/approve`、`POST /m2/applications/{id}/reject`。
- 校验：必填、整点、时长、过去时间、容量、房间状态、同房间时段重叠。
- `tests/m2/` 下按需求 ID 命名的行为测试，覆盖成功与拒绝路径。

## 不做项

二级审批、超时撤销、申请人撤销、审批结果通知、审批后写入 M1 座位状态、房间/教室管理界面、申请编辑与删除、分页与导出、附件上传。

## 约束

- 单次最长 4 小时，实现使用 `MAX_HOURS = 4` 常量；尚未实现原方案中拟议的环境变量配置。页面时长选项同步为 1–4 小时。
- 服务端按 `Asia/Shanghai` 校验本地整点与开放时间，落库和 JSON 时间字段使用 UTC 文本。页面负责格式化展示；不做跨时区用户支持。
- 人数为 `1..min(room.capacity, 500)` 的整数；`room.is_active = 0` 的房间不可申请。
- 时段重叠判定只对占用状态（`PENDING_L1`、`PENDING_L2`、`APPROVED`）生效；重叠返回 `409`，表示输入与现有记录冲突。
- “查重叠 + 插入”与状态流转都在 `BEGIN IMMEDIATE` 事务内完成，避免两个请求同时通过校验；审批用 `UPDATE ... WHERE status = 'PENDING_L1'` 的 `rowcount` 判断竞争。
- 业务模块不写其他模块的表：审批只改 `room_application` 的审批相关字段，M1/M3 的占用（M2-R06）等契约确认后再做。
- 房间主数据属于 G3（D-R03）。本任务只依赖 `room(id, name, capacity, is_active)`，其余字段由 G3 扩展；公共字段变化须先协调。
- 已提交 V1 保持不变；后续 schema 变化新增版本。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A 应用层校验 + `BEGIN IMMEDIATE` 事务内查重叠后插入；审批用条件 `UPDATE` 判断 `rowcount` | 无新增依赖；错误信息可精确到字段；并发安全和 SQLite 的写锁语义一致 | 需要显式事务边界和一处手工加锁逻辑 | 原任务采用 |
| B 交给数据库约束（唯一索引/触发器） | 并发由数据库保证 | SQLite 没有区间排除约束，无法表达“时段重叠”；触发器里的错误信息难以返回 `422` | 不采用 |
| C 引入 `transitions` 等状态机库表达审批流转 | 状态转移声明清晰 | 本轮只有 3 个可达状态，增加依赖收益不足 | 不采用 |

## 相关文件

`database/migrations/V1__init.sql`（G3 汇总的公共文件）、`app/m2/applications.py`、`app/m2/times.py`、`app/m2/router.py`、`tests/m2/`、`web/templates/m2-login.html`、`web/templates/m2-apply.html`、`web/templates/m2-approve.html`、`web/assets/m2.js`、`web/assets/m2.css` 与本文件。

## 数据契约

```sql
CREATE TABLE room (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  capacity INTEGER NOT NULL CHECK (capacity > 0),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE room_application (
  id INTEGER PRIMARY KEY,
  applicant_id INTEGER NOT NULL REFERENCES app_user(id) ON DELETE RESTRICT,
  room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE RESTRICT,
  start_at TEXT NOT NULL,
  end_at TEXT NOT NULL,
  purpose TEXT NOT NULL CHECK (length(purpose) BETWEEN 1 AND 200),
  attendee_count INTEGER NOT NULL CHECK (attendee_count > 0),
  status TEXT NOT NULL DEFAULT 'PENDING_L1'
    CHECK (status IN ('PENDING_L1','PENDING_L2','APPROVED','REJECTED','REVOKED','CANCELLED')),
  decided_by INTEGER REFERENCES app_user(id) ON DELETE SET NULL,
  decision_note TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  CHECK (end_at > start_at)
);
CREATE INDEX room_application_room_time ON room_application (room_id, start_at, end_at);
CREATE INDEX room_application_applicant ON room_application (applicant_id);
```

重叠判定：`start_at < 新 end_at AND end_at > 新 start_at AND room_id = ? AND status IN (...)`。时间字段为定长 UTC 文本，字符串比较等价于时间比较。

## 验收标准

- Given `teacher`/`org_leader` 会话，When 提交合法申请，Then `201` 并返回 `PENDING_L1`；Given `student` 会话，Then `403`；Given 未登录，Then `401`。
- Given 缺少用途、人数非正、超过房间容量或 500 人、开始时间在过去、非整点、`end <= start`、时长超过上限，When 提交，Then `422` 且不新增记录（逐条断言）。
- Given 房间已停用，When 提交申请，Then `409` 且不新增记录；Given 房间不存在，Then `404`。
- Given 同房间与已存在申请时段重叠，When 提交 `PENDING_L1`，Then `409`；Given 仅首尾相接（`end == 新 start`），Then `201`；Given 同房间但另一方已 `REJECTED`，Then `201`。
- Given 待审申请与 `approver` 会话，When approve，Then `200`，状态 `APPROVED`，记录 `decided_by` 与 `updated_at`；When 再次 approve，Then `409` 且状态不变。
- Given `student` 或 `teacher` 会话，When approve，Then `403`；Given 不存在的 id，Then `404`。
- Given reject 且请求体带 `note`，Then `200`、状态 `REJECTED`、响应和数据库的 `decision_note` 保存该备注；Given 无备注，Then `422`（驳回必须给申请人可读的理由）。
- Given 审批人对自己提交的申请 approve/reject，Then `409`（自己不能批自己）。
- Given 本人申请列表，When `GET /m2/applications`，Then 只返回自己的记录；Given `approver` 请求 `/m2/applications/pending`，Then 返回 `PENDING_L1` 记录。
- Given 非法 `status` 值，When 直接写库，Then 被 `CHECK` 约束拒绝（在 schema 测试中断言）。

## 验证计划

整合后的待执行命令：`python -m pytest tests/m2 -q`、`python scripts/ci.py`；本机 `uvicorn` + `curl` 走一遍“teacher 申请 → approver 通过 → 重复审批 409”。实际结果须另记日期和提交号。本次文档整理未运行这些验证。

## 实际结果（2026-10-21，原分支记录）

以下保留原命令、数量及日期，反映源分支当时的记录。原命令中的 `tests/d` 是当时目录，整合后认证测试归入 `tests/d/auth/`。本节不是本次整合的验证结果。

验证日期 2026-10-21，执行 `.venv/bin/python -m pytest tests/m2 tests/d -q` → 42 passed；
`.venv/bin/python scripts/ci.py` → 130 passed 且输出 `[CI] All checks passed.`。

- 已实现：`GET /m2/rooms`、`POST /m2/applications`、`GET /m2/applications`（含 `?status=`）、`GET /m2/applications/pending`、`GET /m2/applications/{id}`、`POST …/approve`、`POST …/reject`。
- 并发：`create_application` 与 `decide_application` 都在 `BEGIN IMMEDIATE` 事务内先查后写；状态更新带 `WHERE status = 'PENDING_L1'` 并以 `rowcount` 检测被抢先处理的情况，返回 `409`。
- 与原计划的差异：①驳回时把「无备注允许」收紧为 `422`；②「自己不能批自己」写成显式 `409` 并加测试（演示账号默认不同时持两项权限，测试在临时库补授权后验证该分支）。
- 当时未实现：二级审批、申请人撤销、超时撤销、M2 占用/释放 M1 座位、审计写入。
- 页面：`/m2/login`、`/m2/apply`、`/m2/approve` 三个静态页 + `/assets/m2.js`、`/assets/m2.css`，全部通过公开 JSON 接口读写。
- 本机 `uvicorn --port 8123` + `curl` 冒烟（2026-10-21）：teacher01 登录 200 → 提交 201 `PENDING_L1`（`09:00+08:00` 存为 `01:00Z`）→ student01 提交 `403 forbidden` → approver01 待审列表可见 → approve 200 `APPROVED` → 重复 approve `409 conflict`。页面与静态资源均 200。
- 当时待人工：浏览器里点一遍三个页面的交互；`decided_by` 展示名依赖种子账号。本次未补记人工验收。

## 故意破坏实验（2026-10-21，原分支记录）

以下为同一历史分支的实验记录，本次未重新执行。

- **实验 B（冲突判定与状态机）**：把 `app/m2/applications.py` 的重叠条件从 `start_at < 新end AND end_at > 新start` 改成 `start_at = ? AND end_at <> ?`，并把审批的“必须待审”判断改成恒假；`python -m pytest tests/m2 -q` → **2 failed, 15 passed**（时段冲突、重复审批两条用例失败）。恢复后 → **17 passed**。
- 说明：只破坏状态机时「自己不能批自己」用例仍会通过，因为该护栏在状态判断之前——这反而确认了护栏顺序是有意的。
- 原实验未覆盖：真正并发的两个请求争抢同一时段（需要多线程/多进程 + 真实锁等待），当时只验证了“先查后写在同一事务里”的代码路径。
