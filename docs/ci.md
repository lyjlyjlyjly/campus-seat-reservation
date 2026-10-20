# CI 规范与本地检查

本轮以 [Review 1 计划](Review1计划.md) 为范围，只有一个 `check` job。配置在 [.github/workflows/ci.yml](../.github/workflows/ci.yml)，本地与 CI 共用 [scripts/ci.py](../scripts/ci.py)。当前没有部署 job、服务器凭据或发布操作。

## 触发和执行

| 项目 | 约定 |
|---|---|
| 自动触发 | 指向 main 的 Pull Request；main 的 push |
| 手动触发 | workflow_dispatch，只运行检查 |
| 环境 | GitHub 托管 Ubuntu 24.04，Python 3.10 |
| 权限 | contents: read；checkout 不保留凭据 |
| 依赖 | 从 requirements.txt 安装；按该文件缓存 pip 下载 |
| Actions | 官方 checkout/setup-python 固定 commit SHA，注释保留对应版本 |
| 同一分支多次提交 | 新运行取消旧运行；10 分钟超时 |
| 通过条件 | 所有步骤退出码为 0，没有 continue-on-error 或允许失败的测试 |

检查顺序：

1. `python scripts/check_notes.py`：校验决策文档的可机械检查部分。
2. `python -m compileall -q app scripts tests`：编译 Python，发现语法错误。
3. `python -m pytest`：执行应用、数据库、Note 校验器以及后续模块的行为测试。

统一脚本使用调用它的同一个 Python 解释器，并将工作目录定位到仓库根。任一步失败立即返回非零，不继续后续步骤。依赖安装失败也会让 job 失败。

## 本地怎样检查

在项目虚拟环境中执行 `python scripts/ci.py` 可重现完整检查。日常改动选择有关检查：

| 改动 | 最小检查 |
|---|---|
| Note 格式、路径或互链 | `python scripts/check_notes.py` |
| Note 校验器 | 上一命令及 `python -m pytest tests/test_notes.py` |
| 应用入口、配置、连接 | `python -m pytest tests/test_app.py tests/test_bootstrap.py` |
| 迁移、种子 | `python -m pytest tests/test_bootstrap.py`，再跑受影响模块测试 |
| M1/M2/M3/D 业务 | 对应 `tests/<module>/` 中实际存在的测试，覆盖成功/拒绝路径 |
| CI 入口及跨目录基础变更 | `python scripts/ci.py` |
| 普通文档 | 核对链接、范围和事实；涉及 Note 时运行格式检查 |

Windows 未激活环境时用 `.\.venv\Scripts\python.exe` 替代 `python`。模块测试目录中的 `.gitkeep` 不算测试；未有业务测试时不得据 CI 为绿色就把需求标成完成。

## 测试与迁移证据

数据库测试在临时目录建立真实迁移和幂等种子，验证从空库重放、重复执行、失败回滚及版本保护。应用测试通过 TestClient 调用实际路由，并检查 SQLite 不可用时的失败响应。当前仓库没有业务迁移/种子，测试用的样例表不冒充 D-R03 演示数据。

业务代码接入后，每条本轮需求至少关联实现和行为测试，数据初始化测试应覆盖仓库实际迁移/种子。使用真实被测逻辑；不 mock 预约冲突、权限和状态校验本身。每个业务模块的故意破坏实验另在 spec/PR 留下真实失败与恢复证据。

Note 检查器验证格式、必需章节、日期/编号/状态、仓库内链接和替代关系；无法证明人的确认真实或方案合理。内容规则以 [.agents/notes/README.md](../.agents/notes/README.md) 为准。

## GitHub 上还需配置的事项

工作流文件提交并推送后才会在 GitHub 运行。本次本地检查结果不能写成远端 Actions 已通过。

负责人应为 main 配置 PR 合并、必需的 `check` 状态检查和评审；在 GitHub 实际出现工作流结果后选择对应检查名称。公共层、跨组和 schema 改动必须由其他组成员实际评审。先把真实成员账号填入 CODEOWNERS，目前仅有仓库所有者兜底规则，不能替代跨组评审。

README、YAML 和 CODEOWNERS 都不能自行开启分支保护。受仓库权限或套餐限制无法配置时，在项目记录中写明限制并执行人工合并检查，不虚构自动门禁。测试环境自动部署、人工生产审批和回滚见 [发布安排](release-process.md)。
