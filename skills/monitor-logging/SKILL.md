---
name: monitor-logging
description: Datadog 可观测性：日志搜索、APM 追踪、监控告警、LLM 可观测性
source:
  type: derived
  repo: skills-repo/devops-engineer
  path: skills/monitor-logging/SKILL.md
  version: 1.0.0
  updated: 2026-07-26
  url: https://skills.sh/datadog-labs/agent-skills/agent-skills
metadata:
  category: 可观测性
  platform: Cloud
  difficulty: 进阶
---

# 可观测性：监控、日志与追踪

> Datadog 驱动的可观测性实践：日志搜索、APM 追踪、监控告警、LLM 可观测性。

## 能力

- **日志管理**：日志搜索、Pipeline 处理、归档策略、索引配置
- **APM 追踪**：服务拓扑、请求追踪、性能分析、错误定位
- **监控告警**：创建/管理/静默 Monitor、告警策略、SLO 监控
- **LLM 可观测**：LLM 调用追踪、Token 用量、实验对比、评估
- **浏览器 SDK**：RUM、Logs、Session Replay 前端监控

## 使用方式

```
/monitor-logging 搜索过去 1 小时的错误日志
/monitor-logging 为这个 API 创建可用性监控
/monitor-logging 分析这个 Trace 的慢请求原因
```

## 工作流

1. 确认可观测性需求（日志/指标/追踪/前端）
2. 安装对应 Agent/SDK
3. 配置日志 Pipeline 和索引
4. 创建关键指标监控和告警
5. 用 APM 追踪排查性能问题

## 适用场景

- 生产环境可观测性搭建
- 故障排查和根因分析
- 性能监控和告警配置
- LLM 应用的可观测性

## 限制

- 依赖 Datadog 平台（需要 API Key）
- 不涉及开源替代（Prometheus/Grafana/ELK）
- 不涉及日志的 GDPR/PII 合规处理

## 相关参考（Playbook）

指标体系/SLO/错误预算/告警设计的决策 → `references/observability.md`；
告警驱动事故响应与无指责复盘 → `references/incident-response.md`；
错误预算计算 → `references/scripts-usage.md`（`slo_budget.py`）。
