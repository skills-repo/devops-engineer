---
name: infra-as-code
description: Terraform/Pulumi 基础设施即代码，一键创建云资源和环境
source:
  type: original
  repo: skills-repo/devops-engineer
  path: skills/infra-as-code/SKILL.md
  version: 1.0.0
  updated: 2026-07-26
metadata:
  category: IaC
  platform: 云平台
  difficulty: 专家
---

# 基础设施即代码

> 用 Terraform 或 Pulumi 管理云资源，告别手动点击控制台。

## 能力

- **资源建模**：根据需求生成 Terraform/Pulumi 配置
- **多云支持**：AWS、GCP、Azure、VPS（Hetzner/DigitalOcean）
- **模块化**：拆分可复用的基础设施模块
- **状态管理**：远程 state 配置和锁定策略
- **安全基线**：自动添加安全组、IAM 最小权限

## 使用方式

在 Claude Code 中使用 `/infra-as-code` 调用。

```
/infra-as-code 创建一个带 PostgreSQL 的 Web 服务基础设施
/infra-as-code 审查现有 Terraform 配置的安全性
```

## 工作流

1. 描述基础设施需求（服务器、数据库、域名等）
2. AI 设计架构（VPC/网络/计算/存储）
3. 生成 Terraform/Pulumi 配置文件
4. 检查安全配置（端口暴露、IAM 策略）
5. 输出部署命令和成本预估

## 适用场景

- 从手动管理迁移到 IaC
- 快速搭建开发/测试环境
- 多云部署统一管理
- 基础设施变更的安全审查

## 限制

- 不处理已有资源的反向导入
- 云成本优化需结合具体账单
- 生产环境应用前需人工审查