# 数据库初始化

三组共用 SQLite；G3 汇总迁移与演示种子，业务 schema 须先经过三组的公共字段确认。`V1__init.sql` 目前包含 G2 的账号、角色、权限、会话、教室申请表，以及 M2 依赖的房间最小字段；楼宇、座位与工单表仍待 G3 扩展。初始化后 schema 版本为 `1`。

在项目虚拟环境中执行：

```text
python -m app.bootstrap
python -m app.bootstrap --seed
```

第一条执行尚未应用的版本迁移；第二条在迁移后显式执行 `seed.sql`。当前种子写入 6 个虚构演示账号（只含口令散列）与 3 间虚构教室，重复执行不产生重复行。角色与权限映射属于授权契约，随 `V1__init.sql` 写入。

默认文件为仓库下 `var/campus.sqlite3`。可通过进程环境变量 `CAMPUS_DATABASE_PATH` 配置路径，相对值始终以仓库根目录解析；也可传入 `--database path` 覆盖本次命令，命令行的相对路径以当前工作目录解析。测试和演示排查宜使用独立文件，不将 `.sqlite3` 文件加入 Git。

应用启动不创建数据库。尚未初始化、文件为空或不可读取时，`GET /health` 返回 `503`；初始化后返回实际 schema 版本。运行时连接由 [`app/common/db.py`](../app/common/db.py) 管理，每次独立连接、启用外键，正常退出提交、异常回滚并关闭。

演示账号均为虚构数据，仅用于本机验收：

| 用户名 | 演示口令 | 角色 | 主要用途 |
|---|---|---|---|
| `student01` | `Student#2026` | `student` | 验证无 `room:apply` 时的拒绝路径 |
| `teacher01` | `Teacher#2026` | `teacher` | 提交教室申请 |
| `leader01` | `Leader#2026` | `org_leader` | 提交教室申请 |
| `approver01` | `Approver#2026` | `approver` | 一级审批 |
| `maint01` | `Maint#2026` | `repairer` | M3 报修/维修 |
| `admin01` | `Admin#2026` | `admin` | 管理与审批 |

口令散列由 `python -m app.d.auth.password` 生成；明文口令只写在本文档，不得用于任何真实环境。

新增迁移与脚本约束见 [迁移规范](migrations/README.md)。初始化失败时命令返回非零退出码；每个迁移或种子使用独立事务，失败操作回滚，已完成的早期迁移保留。不得通过手改数据库或修改已提交迁移跳过失败。
