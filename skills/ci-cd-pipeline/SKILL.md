---
name: ci-cd-pipeline
description: GitHub Actions/GitLab CI 流水线设计优化，自动生成构建、测试、部署配置
source:
  type: original
  repo: skills-repo/devops-engineer
  path: skills/ci-cd-pipeline/SKILL.md
  version: 1.0.0
  updated: 2026-07-26
metadata:
  category: CI/CD
  platform: 通用
  difficulty: 进阶
---

# CI/CD 流水线

> 为项目自动设计和优化 CI/CD 流水线，支持 GitHub Actions、GitLab CI 等主流平台。

## 能力

- **流水线生成**：分析项目结构，自动生成 CI 配置文件
- **多平台支持**：GitHub Actions、GitLab CI、Jenkinsfile
- **矩阵构建**：多 Node/Python/Go 版本并行测试
- **缓存优化**：依赖缓存策略，减少构建时间
- **部署集成**：自动连接 Docker 镜像构建和部署步骤

## 使用方式

在 Claude Code 中使用 `/ci-cd-pipeline` 调用。

```
/ci-cd-pipeline 为这个 Next.js 项目生成 GitHub Actions 配置
/ci-cd-pipeline 优化现有 CI 的构建速度
```

## 工作流

1. 分析项目类型和依赖（package.json/go.mod/requirements.txt）
2. 确定 CI 平台（默认 GitHub Actions）
3. 生成：checkout → 缓存 → 安装依赖 → lint → test → build
4. 按需添加：矩阵测试、Docker 构建、自动部署
5. 输出 yml 文件和配置说明

## 适用场景

- 新项目初始化 CI/CD
- 构建时间过长需要优化
- 从 Travis/Jenkins 迁移到 GitHub Actions
- 添加自动化测试和 lint 到现有流水线

## 限制

- 不处理私有 runner 配置
- 复杂 Monorepo 需人工调整
- Secret 管理需配合平台文档