# AGENTS.md

## 仓库性质

这是一个 **AI Agent 技能库**，不是软件项目。所有内容为 Markdown 格式的技能定义文件。

## 目录约定

```
devops-engineer/
├── README.md              # 项目介绍和使用指南
├── AGENTS.md              # AI 助手使用指引（本文件）
└── skills/                # 技能目录
    ├── <skill-name>/      # 单个技能目录
    │   └── SKILL.md       # 技能定义文件
    └── ...
```

## SKILL.md 格式

```markdown
---
name: <skill-name>
description: <一句话描述>
metadata:
  category: <CI/CD|容器化|IaC|监控>
  platform: <云平台|通用>
  difficulty: <入门|进阶|专家>
---

# <技能名称>

> <一句话简介>

## 能力

- 能力点列表

## 使用方式

在 Claude Code 中使用 `/skill-name` 调用。

## 工作流

1. 步骤化的执行流程

## 适用场景

- 场景列表

## 限制

- 不擅长的领域
```

## 工作约定

- 所有技能内容使用中文编写
- 面向个人开发者和小团队（1-10 人）
- 优先 Docker Compose / VPS 部署，非必须不用 Kubernetes
- 每个技能输出可直接执行的配置文件

## 技能添加流程

1. 在 `skills/` 下创建以技能名命名的目录
2. 编写 `SKILL.md`
3. 确保 `metadata` 字段完整
4. 更新 `README.md` 中的技能清单表

## 不做什么

- 不创建面向企业级 Kubernetes 集群的技能
- 不涉及特定云厂商的内部工具
- 不做安全合规审计（交给 security-guardian）