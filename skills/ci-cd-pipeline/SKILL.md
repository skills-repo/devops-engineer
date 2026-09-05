---
name: ci-cd-pipeline
description: CI/CD 流水线自动化：质量门禁、测试集成、部署策略、GitHub Actions
source:
  type: derived
  repo: skills-repo/devops-engineer
  path: skills/ci-cd-pipeline/SKILL.md
  version: 1.0.0
  updated: 2026-07-26
  url: https://skills.sh/addyosmani/agent-skills/ci-cd-and-automation
metadata:
  category: CI/CD
  platform: 通用
  difficulty: 入门
---

# CI/CD 流水线与自动化

> 自动化质量门禁：任何变更未经 lint/typecheck/test/build 不进入生产。CI/CD 是所有其他技能的强制执行机制。

## 能力

- **质量门禁流水线**：Lint → Type Check → Unit Test → Build → Integration → E2E → Security → Bundle
- **左移策略**：问题越早发现成本越低，静态分析优先于测试，测试优先于部署
- **部署策略**：蓝绿部署、金丝雀发布、功能开关（feature flags > 长期分支）
- **GitHub Actions**：workflow 配置、matrix build、cache 优化、环境变量管理
- **更快更安全**：小批量 + 高频发布降低风险，3 个变更的部署比 30 个更容易排错

## 使用方式

```
/ci-cd-pipeline 为这个 Node.js 项目配置 GitHub Actions
/ci-cd-pipeline 设计一个包含 lint/test/build/deploy 的流水线
/ci-cd-pipeline 这个 CI 失败了，帮我排错
```

## 工作流

1. 确定项目类型和技术栈
2. 配置质量门禁顺序（lint → type → test → build）
3. 设置触发条件（PR/merge/push/tag）
4. 配置部署策略和环境
5. 测试流水线，确保每个门禁实际执行

## 适用场景

- 新项目 CI/CD 搭建
- 现有流水线优化加速
- 部署策略选择和实施
- CI 失败排错

## 限制

- 主要覆盖 GitHub Actions，其他 CI 平台类似
- 不涉及 Kubernetes 部署策略（归属 infra-as-code）
- 不涉及 monorepo 管理（lerna/nx/turborepo）

## 相关参考（Playbook）

需要判断门禁怎么分层、密钥怎么管、分支/触发策略怎么定 → 读 [`references/ci-cd-pipeline.md`](../../references/ci-cd-pipeline.md)。
门禁放行后的发布策略选型 → [`references/deployment-strategies.md`](../../references/deployment-strategies.md)；对现有 workflow 做体检 → [`references/scripts-usage.md`](../../references/scripts-usage.md)（`ci_audit.py`）。
