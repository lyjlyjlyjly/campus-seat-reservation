# SPEC-002：教室申请与一级审批

日期：2026-10-20。状态：方案已由用户确认，按模块实施，交付后待人工验收。

需求：[M2-R01](../requirements.md)（申请角色门槛）、[M2-R02](../requirements.md)（教室、时段、用途和人数）、[M2-R03](../requirements.md) 的一级审批部分。

## 背景与授权

用户（G2 负责人）在 2026-10-20 确认 `room:apply` 授予 `teacher` 与 `org_leader`、`student` 不授予，并要求页面采用静态 HTML + 原生 JS 调 JSON 接口。本任务实现 `/m2` 下“登录 → 申请 → 一级审批”这条主链，对应 Review 1 计划的 G2 验收线。

二级审批（M2-R03 剩余部分）、超时撤销（M2-R04）、申请人撤销与状态查询（M2-R05）、审批占用 M1 座位（M2-R06）、D-R05 审计均按计划延期；本任务不因实现一级审批而声称多级流程已完成。

## 范围

- `room_application` 表（DDL 见下）与只读的 `room` 主数据引用。
- 接口：`GET /m2/applications/options`（可申请房间与时长上限，供页面填充）、`POST /m2/applications`、`GET /m2/applications`（本人申请；审批人可见待审列表）、`POST /m2/applications/{id}/approve`、`POST /m2/applications/{id}/reject`。
- 校验：必填、整点、时长、过去时间、容量、房间状态、同房间时段重叠。
- `tests/m2/` 下按需求 ID 命名的行为测试，覆盖成功与拒绝路径。

## 不做项

二级审批、超时撤销、申请人撤销、审批结果通知、审批后写入 M1 座位状态、房间/教室管理界面、申请编辑与删除、分页与导出、附件上传。

## 约束

- 单次最长时长默认 4 小时，由 `CAMPUS_MAX_APPLICATION_HOURS` 覆盖；与 M1 的“最多 4 小时”保持一致，课程任务书未规定 M2 上限，取值作为可配置默认值，改配置即可调整。
- 时间以 `Asia/Shanghai` 输入输出，整点校验在本地时区做，落库为 UTC 文本；不做跨时区用户支持。
- 人数为 `1..room.capacity` 的整数；`room.is_active = 0` 的房间不可申请。
- 时段重叠判定只对占用状态（`PENDING_L1`、`PENDING_L2`、`APPROVED`）生效；重叠返回 `409` 而不是 `422`，因为输入合法但与现有记录冲突。
- “查重叠 + 插入”与状态流转都在 `BEGIN IMMEDIATE` 事务内完成，避免两个请求同时通过校验；审批用 `UPDATE ... WHERE status = 'PENDING_L1'` 的 `rowcount` 判断竞争，不用“先查后改”。
- 业务模块不写其他模块的表：审批只改 `room_application.status`，M1/M3 的占用（M2-R06）等契约确认后再做。
- 房间主数据属于 G3（D-R03）。本任务只依赖 `room(id, name, capacity, is_active)`，其余字段由 G3 扩展；若最终 `room` 字段名不同，仅需改 `app/m2` 中的读取语句。

## 候选方案

| 方案 | 收益 | 代价 | 选择 |
|---|---|---|---|
| A 应用层校验 + `BEGIN IMMEDIATE` 事务内查重叠后插入；审批用条件 `UPDATE` 判断 `rowcount` | 无新增依赖；错误信息可精确到字段；并发安全和 SQLite 的写锁语义一致 | 需要显式事务边界和一处手工加锁逻辑 | 采用 |
| B 交给数据库约束（唯一索引/触发器） | 并发由数据库保证 | SQLite 没有区间排除约束，无法表达“时段重叠”；触发器里的错误信息难以返回 `422` | 不采用 |
| C 引入 `transitions` 等状态机库表达审批流转 | 状态转移声明清晰 | 本轮只有 3 个可达状态，增加依赖收益不足 | 不采用 |

## 预计改动

`database/migrations/V1__init.sql`（新增 `room` 片段与 `room_application`，同时需 G3 评审）、`app/m2/validation.py`、`app/m2/router.py`、`app/m2/__init__.py`、`tests/m2/`、`web/m2/` 页面与本文件。

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
- Given 缺少用途、人数非正、超过房间容量、房间已停用、开始时间在过去、非整点、`end <= start`、时长超过上限，When 提交，Then `422` 且不新增记录（逐条断言）。
- Given 同房间与已存在申请时段重叠，When 提交 `PENDING_L1`，Then `409`；Given 仅首尾相接（`end == 新 start`），Then `201`；Given 同房间但另一方已 `REJECTED`，Then `201`。
- Given 待审申请与 `approver` 会话，When approve，Then `200`，状态 `APPROVED`，记录 `decided_by` 与 `updated_at`；When 再次 approve，Then `409` 且状态不变。
- Given `student` 或 `teacher` 会话，When approve，Then `403`；Given 不存在的 id，Then `404`。
- Given reject 且带 `decision_note`，Then `200`、状态 `REJECTED`、备注保存；Given 无备注，Then `422`（驳回必须给申请人可读的理由）。
- Given 审批人对自己提交的申请 approve/reject，Then `409`（自己不能批自己）。
- Given 本人申请列表，When `GET /m2/applications`，Then 只返回自己的记录；Given `approver` 请求待审列表，Then 返回 `PENDING_L1` 记录。
- Given 非法 `status` 值，When 直接写库，Then 被 `CHECK` 约束拒绝（在 schema 测试中断言）。

## 验证计划

`python -m pytest tests/m2 -q`；`python scripts/ci.py`；本机 `uvicorn` + `curl` 走一遍“teacher 申请 → approver 通过 → 重复审批 409”，并把实际命令与结果补到本节下方。

## 实际结果

验证日期 2026-10-21，执行 `.venv/bin/python -m pytest tests/m2 tests/d -q` → 42 passed；
`.venv/bin/python scripts/ci.py` → 130 passed 且输出 `[CI] All checks passed.`。

- 已实现：`GET /m2/rooms`、`POST /m2/applications`、`GET /m2/applications`（含 `?status=`）、`GET /m2/applications/pending`、`GET /m2/applications/{id}`、`POST …/approve`、`POST …/reject`。
- 并发：`create_application` 与 `decide_application` 都在 `BEGIN IMMEDIATE` 事务内先查后写；状态更新带 `WHERE status = 'PENDING_L1'` 并以 `rowcount` 检测被抢先处理的情况，返回 `409`。
- 与计划的差异：①驳回归还时把「无备注允许」收紧为 `422`；②「自己不能批自己」写成显式 `409` 并加测试（演示账号默认不同时持两项权限，测试在临时库补授权后验证该分支）。
- 未实现（按 Review 1 范围延期）：二级审批、申请人撤销、超时撤销、M2 占用/释放 M1 座位、审计写入。
- 页面：`/m2/login`、`/m2/apply`、`/m2/approve` 三个静态页 + `/assets/m2.js`、`/assets/m2.css`，全部通过公开 JSON 接口读写。
- 本机 `uvicorn --port 8123` + `curl` 冒烟（2026-10-21）：teacher01 登录 200 → 提交 201 `PENDING_L1`（`09:00+08:00` 存为 `01:00Z`）→ student01 提交 `403 forbidden` → approver01 待审列表可见 → approve 200 `APPROVED` → 重复 approve `409 conflict`。页面与静态资源均 200。
- 待人工：浏览器里点一遍三个页面的交互；`decided_by` 展示名依赖种子账号。

## 故意破坏实验（2026-10-21）

- **实验 B（冲突判定与状态机）**：把 `app/m2/applications.py` 的重叠条件从 `start_at < 新end AND end_at > 新start` 改成 `start_at = ? AND end_at <> ?`，并把审批的“必须待审”判断改成恒假；`python -m pytest tests/m2 -q` → **2 failed, 15 passed**（时段冲突、重复审批两条用例失败）。恢复后 → **17 passed**。
- 说明：只破坏状态机时「自己不能批自己」用例仍会通过，因为该护栏在状态判断之前——这反而确认了护栏顺序是有意的。
- 未覆盖：真正并发的两个请求争抢同一时段（需要多线程/多进程 + 真实锁等待），本轮只验证了“先查后写在同一事务里”的代码路径。
