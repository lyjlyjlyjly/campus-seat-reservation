# 项目逻辑图

用浏览器打开 [项目逻辑图](project-logic.html)。这是 Archify 生成的独立 HTML，查看时不需要 Node.js 或启动项目。

图依据 [需求基线](../requirements.md) 中列出的首轮范围，以及 [PJ 计划书](../PJ-计划书.md) 的分组和数据归属。图中业务流程是首轮开发目标；三个前缀表示骨架的路由注册位置，业务端点、共用登录和业务表契约仍由三组实现、确认。

| 三组路由 | 计划业务链 | 共用职责 |
|---|---|---|
| G1（A、B）· M1 `/m1` | 搜索座位 → 校验整点 1–4 小时与冲突 → 预约 | 拥有预约记录和预约状态；读取 D 的空间主数据 |
| G2（C、D）· M2 `/m2` | 提交整教室申请 → 一级通过 / 驳回 | D-R01 / R02：会话 Cookie、固定 RBAC；三组使用同一登录契约 |
| G3（E、F）· M3 `/m3` | 文字报修 → 手动派单 → `REPORTED → ASSIGNED → IN_REPAIR` | D-R03：空间主数据、唯一迁移与幂等种子；协调 D-R04 即时提示约定 |

三组的路由运行在同一个 FastAPI 进程，共用一个 SQLite 文件。公共层 D 按子域归属 G2、G3；`/d` 的具体业务接口待共同确认。D-R04 由三组页面使用同一操作结果提示约定。D 的座位主数据与 M1 的预约状态分别维护。

延期的生产部署、定时任务、M3→M1 / M2→M1 跨模块写回没有画成当前调用链；完整延期项见 [需求基线](../requirements.md)。

## 修改与重新生成

[project-logic.archify.json](project-logic.archify.json) 是可维护源文件，HTML 是生成产物。修改 JSON 后必须重新校验、交付、浏览器检查，再实际查看截图；不要手改 HTML 绕过校验。

在仓库根目录的 PowerShell 中使用本机已安装的 Archify：

```powershell
$archifyCli = Join-Path $env:USERPROFILE '.agents/skills/archify/bin/archify.mjs'
node $archifyCli validate architecture docs/diagrams/project-logic.archify.json --quality showcase --json
node $archifyCli deliver architecture docs/diagrams/project-logic.archify.json docs/diagrams/project-logic.html --quality showcase --json
node $archifyCli visual-check docs/diagrams/project-logic.html --json
```

仅在上一条命令退出码为 0 时继续。重新交付后同步保存 `deliver` 输出和视觉审阅记录；`visual-check` 会写入带产物摘要的浏览器报告、截图和 [截图索引](project-logic.visual-check.html)。Archify 的 Node.js 只用于重画此文档，不属于应用或 CI 依赖。

## 实际验收记录

2026-10-20 使用安装版本 `2.17.0-dev.1` 完成：

- [确定性交付回执](project-logic.delivery.json)：`deliver` 退出码 0，showcase 9/9，0 错误、0 警告。
- [浏览器证据](project-logic.visual-check.json)：`visual-check` 退出码 0，真实 Chrome 检查通过。1440×900、1600×1000、1920×1080、2048×1320 均无横向或纵向溢出。
- [图像审阅记录](project-logic.review.json)：实际查看了最终产物在 1440×900、2048×1320 的浅色和深色截图；三路关系、标签和说明卡片完整，连线无遮挡，大屏布局正常。两次视觉修正分别处理首屏行距和默认阅读模式下业务链文字的可见性。

确定性交付、浏览器检查和图像审阅分别记录。上述结果只验证图的产物与显示，不代表校园业务已实现，也不替代组员的人工验收；交互搜索、全部导出格式和移动端没有逐项测试。
