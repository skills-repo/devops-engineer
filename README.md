# DevOps 工程师技能库

> AI Agent Skills for DevOps —— 覆盖 CI/CD 流水线、容器化部署、基础设施即代码、监控告警

## 定位

为个人开发者和小团队提供一套可安装的 AI Agent DevOps 技能，让 Claude Code 成为你的运维搭档。

## 核心理念

> DevOps 不只是大厂的专利。一个人也能用自动化把代码从提交送到生产。

- **自动化优先**——能自动化的绝不手动
- **面向小团队**——不需要 Kubernetes 集群也能部署
- **安全第一**——每个部署流程内建安全检查点

## 技能清单

| 环节 | 技能 | 描述 |
|------|------|------|
| 🔄 CI/CD | `ci-cd-pipeline` | GitHub Actions/GitLab CI 流水线设计与优化 |
| 🐳 容器化 | `docker-deploy` | Docker 容器化部署与 compose 编排 |
| 🏗️ IaC | `infra-as-code` | Terraform/Pulumi 基础设施即代码 |
| 📊 监控 | `monitor-logging` | 日志聚合、监控告警与健康检查 |

## 快速开始

```bash
npx skills add skills-repo/devops-engineer@ci-cd-pipeline -g -y
npx skills add skills-repo/devops-engineer@docker-deploy -g -y
npx skills add skills-repo/devops-engineer@infra-as-code -g -y
npx skills add skills-repo/devops-engineer@monitor-logging -g -y
```

## 推荐工作流

```
代码推送 → CI/CD 构建 → Docker 打包 → IaC 部署 → 监控告警
ci-cd-      docker-        infra-as-    monitor-
pipeline    deploy         code         logging
```

## 许可

MIT