# Agent Note: ADR-002 单体技术栈与本轮工程范围

Status: proposed — 按计划搭建骨架，正式决策仍待组内确认

Date: 2026-10-20
Owner: 项目负责人 / G2 发布负责人 / G3 基础设施负责人
References: [任务规格](../../../../docs/specs/000-repository-bootstrap.md)、[架构现状](../../../../docs/architecture.md)

## Problem

本轮仅两天，既要让三组共享可运行的基础，又要保留任务书对测试、迁移和后续交付的要求。项目没有既有业务代码，服务器、业务 schema 和成员账号尚未完成交接。

## Proposal

使用 Python 3.10+、FastAPI/Uvicorn、标准库 sqlite3 和 HTML/CSS。一个应用按 M1/M2/M3 包组织，共享数据库；D 的子域按职责分目录。固定直接依赖版本，pytest/HTTPX 用于行为验证。

本轮使用一个 GitHub Actions check job，执行与本地相同的脚本。仅提供初始化与迁移入口，真实业务字段经三组冻结后写首个 V1 迁移；当前版本 0 明确表示尚无业务表。服务器部署和生产审批按后续任务交付。

## Alternatives considered

| 方案 | 收益 | 代价 / 取舍 |
|---|---|---|
| FastAPI 单体 + SQLite + 服务端页面 | 只有一个运行进程，Windows/Linux 均可开发，三组共享入口 | 需要约束模块写表边界；作为当前提案 |
| FastAPI + 独立前端 + 数据库服务 | 前后端独立、客户端交互空间更大 | 增加前端构建、数据库安装和接口联调 |
| 按模块拆成多个服务 | 可独立发布，网络边界直观 | 当前规模下增加配置、部署及分布式一致性成本 |

AI 初始建议：沿用计划中的最小单体，先交付可运行基础。用户已授权本次骨架工作；三组的正式技术决策和长期部署安排尚待确认，不能把此授权扩大为已完成会议。

## Acceptance criteria

- Given 新的 Python 虚拟环境，When 按 README 安装、初始化和启动，Then 能访问基础页面与健康检查。
- Given 合法版本迁移和幂等种子，When 对空库重复初始化，Then 版本有序且数据不重复；失败迁移不会留下半次变更。
- Given PR 或 main 更新，When check 执行，Then Note、编译和测试任一步失败都会使 job 失败。
- Given 三组确认技术栈，When 记录采纳，Then 补真实确认依据，并同步需求及架构索引。

## Risks

SQLite 并发写入和本地 HTTP 回调的事务边界需要后续按真实业务验证。固定直接依赖不等于所有间接依赖完全锁定。一个本地检查 job 也不代表服务器部署、分支保护或生产审批已经配置。
