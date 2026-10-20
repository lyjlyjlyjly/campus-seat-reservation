-- 演示种子入口；仅在 python -m app.bootstrap --seed 时执行。
-- 全部为虚构演示数据，不含任何真实师生信息。
-- 使用唯一约束与 INSERT OR IGNORE 保证重复执行不产生重复行。
-- 不在此脚本管理事务、PRAGMA user_version 或 PRAGMA foreign_keys。
-- 口令散列由 python -m app.d.auth.password 生成，明文口令只写在 README 与
-- 演示说明中，便于本机验收，不得用于任何真实环境。

INSERT OR IGNORE INTO app_user (username, password_hash, display_name, status) VALUES
  ('student01', 'pbkdf2_sha256$200000$509c857de728808d9af56b2e51b927f3$8ada17fb8c9ecfdd0ff8bce6ae36ef8acaedf14966d2b7572c89101e653a7652', '演示学生', 'ACTIVE'),
  ('teacher01', 'pbkdf2_sha256$200000$ab2e0047a0a70f333e8f86ac0f9a5223$6f0f7c5919d76d712458a576ee882a8c2978683cacee21a280ff5bd61ebefd3c', '演示教师', 'ACTIVE'),
  ('leader01', 'pbkdf2_sha256$200000$dc9f8a75f44ab9bca7ab49bc759a75c7$35979089f24d0a6ec2ea085dbbba272d036b19898885965df85c44734d9e0f32', '演示组织负责人', 'ACTIVE'),
  ('approver01', 'pbkdf2_sha256$200000$80f136d66b5de667ad1f01b807c1d735$2506cf27351b5e193692c11f002a512b686b2946d8d86cf797aa4d0212bb1972', '演示审批员', 'ACTIVE'),
  ('maint01', 'pbkdf2_sha256$200000$31c5e3a594bc1a41435c59785ebe36e8$9ed83ed6939e83076d1cf3020fb6ef702a65f5bd5923a45b4a2050b8d7ef22c6', '演示维修人员', 'ACTIVE'),
  ('admin01', 'pbkdf2_sha256$200000$9a468fcb6cda695c9ccb9362ad1fd2f6$55a9ba980512d0c5a7026b313ce143a3f623f97f6c3278e98dcc284795535f97', '演示管理员', 'ACTIVE');

-- 角色 → 演示账号。权限由 V1 的 role_permission 决定，此处只绑角色。
INSERT OR IGNORE INTO user_role (user_id, role_id)
SELECT u.id, r.id
FROM app_user AS u
JOIN role AS r
WHERE (u.username = 'student01' AND r.code = 'student')
   OR (u.username = 'teacher01' AND r.code = 'teacher')
   OR (u.username = 'leader01' AND r.code = 'org_leader')
   OR (u.username = 'approver01' AND r.code = 'approver')
   OR (u.username = 'maint01' AND r.code = 'repairer')
   OR (u.username = 'admin01' AND r.code = 'admin');

-- 虚构教室，供 M1/M2/M3 演示；D-R03 的楼宇、座位与容量扩展由 G3 补充。
INSERT OR IGNORE INTO room (name, capacity, is_active) VALUES
  ('A101', 40, 1),
  ('A102', 60, 1),
  ('B201', 120, 1);
