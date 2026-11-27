# SQLite 迁移

`V1__init.sql` 由 G2 先提交自己需要的表（账号、角色、权限、会话、房间最小字段、教室申请），仍由 G3 汇总三组字段后扩展。初始化后 `PRAGMA user_version` 为 `1`，演示数据由 `seed.sql` 提供。

默认数据库在仓库内 `var/campus.sqlite3`。`CAMPUS_DATABASE_PATH` 为相对路径时以仓库根目录解析；命令行显式传入 `--database path` 时以当前工作目录解析。

后续文件按 `V1__init.sql`、`V2__reservation_index.sql` 的连续版本编号；文件主题使用 ASCII 字母、数字、下划线或连字符。迁移历史从 V1 开始，不缺号、不重复，已提交的迁移不改写。目录中的任何 `.sql` 文件都必须符合命名格式。

执行 `python -m app.bootstrap` 时，初始化器读取 `PRAGMA user_version`，按数值顺序仅执行新版本；数据库版本高于仓库迁移时拒绝执行。每个迁移单独使用事务，SQL 失败时回滚该迁移，版本号保持原值；此前已成功的迁移保留。

脚本使用 UTF-8。可以有多条 SQL、注释和触发器；事务、`user_version` 和 `foreign_keys` 由初始化器管理，脚本不得包含自己的事务控制或修改这些 PRAGMA。数据库连接默认启用外键。

演示数据独立放在 [`../seed.sql`](../seed.sql)，只在显式使用 `--seed` 时执行。种子需使用唯一约束及 `INSERT OR IGNORE` 等方式保证重复执行不产生重复数据；当前脚本写入 6 个虚构演示账号与 3 间虚构教室。业务迁移和种子均须通过行为测试及三组的公共契约评审。
