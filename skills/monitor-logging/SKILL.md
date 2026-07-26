---
name: monitor-logging
description: 日志聚合、监控告警与健康检查，覆盖 Prometheus/Grafana/ELK 栈
metadata:
  category: 监控
  platform: 通用
  difficulty: 进阶
---

# 监控与日志

> 为应用建立日志聚合、指标监控和告警体系，在用户发现之前就知道出了问题。

## 能力

- **日志收集**：Docker 日志驱动、Filebeat、Fluentd 配置
- **指标暴露**：Prometheus metrics endpoint、Node Exporter 配置
- **仪表板**：Grafana dashboard JSON 模板生成
- **告警规则**：Prometheus Alertmanager 规则编写
- **健康检查**：HTTP/TCP/脚本探活配置和优雅关闭

## 使用方式

在 Claude Code 中使用 `/monitor-logging` 调用。

```
/monitor-logging 为 Node.js 应用添加 Prometheus 监控
/monitor-logging 配置 Grafana 面板监控 API 延迟
```

## 工作流

1. 分析应用架构（Web/数据库/队列/缓存）
2. 识别关键指标（延迟/错误率/吞吐/资源）
3. 生成 Prometheus 指标暴露代码
4. 生成 Grafana dashboard 配置
5. 配置告警规则（临界值、通知渠道）
6. 输出 docker-compose 一键启动监控栈

## 适用场景

- 从无监控到有监控的第一步
- 应用上线前接入监控体系
- 事故后补充告警规则
- 小团队搭建轻量级可观测性

## 限制

- 不处理 APM 级分布式追踪（需配合 OpenTelemetry）
- 大规模日志存储需单独的集群规划
- 告警阈值需根据实际运行数据调优