---
name: docker-deploy
description: Docker 容器化：Dockerfile 编写、compose 多服务、镜像优化、安全最佳实践
source:
  type: derived
  repo: skills-repo/devops-engineer
  path: skills/docker-deploy/SKILL.md
  version: 1.0.0
  updated: 2026-07-26
  url: https://skills.sh/mukul975/anthropic-cybersecurity-skills/hardening-docker-containers-for-production
metadata:
  category: 容器化
  platform: 通用
  difficulty: 入门
---

# Docker 容器化部署

> 容器化应用从开发到生产：Dockerfile 最佳实践、compose 多服务编排、镜像优化、安全加固。

## 能力

- **Dockerfile 编写**：多阶段构建、层缓存优化、最小基础镜像、非 root 运行
- **Compose 多服务**：服务定义、网络配置、卷管理、环境变量、健康检查
- **镜像优化**：减小镜像体积、安全扫描、SBOM 生成
- **安全加固**：只读文件系统、能力限制（cap-drop）、资源限制、seccomp/AppArmor
- **零停机部署**：滚动更新、健康检查、回滚策略

## 使用方式

```
/docker-deploy 为这个 Node.js 应用写 Dockerfile
/docker-deploy 用 compose 编排这个多服务应用
/docker-deploy 审查这个 Dockerfile 的安全性
```

## 工作流

1. 分析应用结构和依赖
2. 编写多阶段 Dockerfile（build → production）
3. 配置 docker-compose.yml（服务/网络/卷/环境）
4. 安全加固检查（用户/能力/文件系统/资源）
5. 测试构建和运行

## 适用场景

- 应用容器化从零开始
- 多服务本地开发环境
- 生产环境镜像安全加固
- CI/CD 中的容器构建优化

## 限制

- 不涉及 Kubernetes 编排
- 不涉及容器网络深度配置
- 不涉及容器注册表管理

## 相关参考（Playbook）

Dockerfile 多阶段/层缓存/安全加固的决策与踩坑 → [`references/containerization.md`](../../references/containerization.md)；
何时上 K8s 与三探针 → [`references/kubernetes.md`](../../references/kubernetes.md)；
发布策略与回滚 → [`references/deployment-strategies.md`](../../references/deployment-strategies.md)；
镜像体检 → [`references/scripts-usage.md`](../../references/scripts-usage.md)（`dockerfile_lint.py` / `k8s_manifest_check.py`）。
