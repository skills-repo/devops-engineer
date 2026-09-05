---
name: infra-as-code
description: Terraform 基础设施即代码：云资源创建、状态管理、模块化、CI 集成
source:
  type: derived
  repo: skills-repo/devops-engineer
  path: skills/infra-as-code/SKILL.md
  version: 1.0.0
  updated: 2026-07-26
  url: https://skills.sh/aradotso/data-skills/terraform-iac-data-engineering
metadata:
  category: IaC
  platform: Cloud
  difficulty: 进阶
---

# Terraform 基础设施即代码

> 使用 Terraform 声明式管理云基础设施：资源定义、状态管理、模块复用、版本控制。

## 能力

- **资源声明**：aws/google/azure provider 的常用资源定义
- **状态管理**：远程 state（S3/GCS）、state lock（DynamoDB）、workspace 隔离
- **模块化**：可复用模块设计、module registry、版本固定
- **变量与输出**：input variables、outputs、locals、terraform.tfvars
- **CI 集成**：terraform plan → apply 流水线、terraform fmt/validate 检查

## 使用方式

```
/infra-as-code 为我的应用创建 AWS 基础设施（EC2 + RDS + S3）
/infra-as-code 审查这个 Terraform 模块的安全性
/infra-as-code 帮我把这个手动创建的资源导入 Terraform
```

## 工作流

1. 确定云平台和资源需求
2. 设计模块结构（网络 → 计算 → 存储 → 监控）
3. 编写 .tf 文件（provider → variables → resources → outputs）
4. terraform init → fmt → validate → plan → apply
5. 配置远程 state 和 CI 集成

## 适用场景

- 云资源从零搭建
- 已有基础设施代码化管理
- 多环境（dev/staging/prod）管理
- 基础设施变更审查

## 限制

- 不涉及 Kubernetes 资源配置（Helm/Kustomize）
- 不涉及多云编排策略
- 需要目标云平台的访问权限

## 相关参考（Playbook）

state 管理/模块化/多环境/危险操作的决策树 → [`references/infrastructure-as-code.md`](../../references/infrastructure-as-code.md)；
把 `terraform plan/apply` 接进 CI → [`references/ci-cd-pipeline.md`](../../references/ci-cd-pipeline.md)；
IaC 变更也需回滚预案 → [`references/deployment-strategies.md`](../../references/deployment-strategies.md)；
体检脚本 → [`references/scripts-usage.md`](../../references/scripts-usage.md)。
