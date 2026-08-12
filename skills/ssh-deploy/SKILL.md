---
name: ssh-deploy
description: >-
  SSH 服务器部署：把构建产物通过 rsync/scp 送到 Linux 服务器、用 systemd 管理服务进程、
  采用"版本目录 + 软链接"实现可回滚发布、含健康检查与零停机/快速重启策略。
  适用于单台/少量 VM、没有 K8s 的小团队服务、定时脚本与内部工具。
source:
  type: derived
  repo: skills-repo/devops-engineer
  path: skills/ssh-deploy/SKILL.md
  version: 1.0.0
  updated: 2026-08-12
  url: https://skills.sh/duck4nh/antigravity-kit/linux-server-expert
metadata:
  category: 服务器部署
  platform: 通用
  difficulty: 入门
---

# SSH 服务器部署

> 把"构建产物 → 一台 Linux 服务器 → 跑起来"这条最朴素也最常见的部署链路做对：
> 透明、可控、零额外基础设施，但扩缩容/自愈要自己写。

## 能力

- **发布机制**：rsync 增量同步 + `--link-dest` 硬链接去重，版本目录 + 原子软链接切换
- **进程管理**：systemd 单元（优雅停机、自动重启、日志查看）托管服务
- **可回滚发布**：保留最近 N 个版本，回滚即改软链接 + 重启，目标 < 30 秒
- **健康检查与零停机**：发布后必探 `/healthz`，失败自动回滚；nginx reload 实现优雅切换
- **安全默认**：专用 deploy 用户、密钥不落地、`.env` 在 `shared/` 不进版本库

## 使用方式

```
/ssh-deploy 帮我把这个 Node 服务发布到 deploy@server
/ssh-deploy 给我写一个 systemd 单元托管这个 Go 二进制
/ssh-deploy 这个发布失败了，帮我回滚到上一个版本
/ssh-deploy 检查我的 rsync 命令会不会误删 shared 目录
```

## 工作流

1. 确认前置：密钥登录、deploy 用户、目录约定（`releases/current/shared`）
2. 构建产物 → rsync 到带时间戳的 `releases/<ver>/`（排除 node_modules，链接 shared）
3. 原子切换 `current -> releases/<ver>`
4. `systemctl restart` 或 `nginx -s reload`
5. 健康检查，失败立即回滚

## 适用场景

- 单台/少量 VM 上的小团队 Web 服务、API、定时任务、内部工具
- 不愿引入容器编排、要完全掌控文件与进程位置的部署
- 与 CI/CD 流水线（`ci-cd-pipeline`）的部署阶段对接

## 不适用 / 边界

- 多实例、需自动扩缩容 → 走 `kubernetes.md`
- PaaS 平台（Vercel/Fly 等）→ 用平台 CLI
- 发布**策略**（蓝绿/金丝雀/扩展-收缩）→ 见 `references/deployment-strategies.md`
- 容器化构建与镜像优化 → 见 `skills/docker-deploy/` 与 `references/containerization.md`
- 删除生产资源、改生产密钥 → 只给命令与风险，不代为执行

## 深层 playbook

完整决策树、命令范式、systemd 单元、踩坑清单见 `references/ssh-deploy.md`。
