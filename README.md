# DevOps 工程师技能库

> AI Agent Skills for DevOps —— CI/CD、容器化、Kubernetes、IaC、可观测性、部署策略与事故响应

采用 **superpower 架构**：一个路由层 + 八篇深层 playbook + 五个可独立安装的子技能 +
四个零依赖审查脚本 + 六份生产级模板。

## 定位

给个人开发者和小团队一套能直接用的 AI Agent DevOps 能力：不止生成"能跑"的配置，
而是生成**能在生产上活下来**的配置，并说清每个决策的取舍。

## 核心理念

> DevOps 不只是大厂的专利。一个人也能用自动化把代码从提交安全送到生产。

- **一切皆代码，一切可复现**——控制台点出来的东西不算数
- **回滚优先于修复**——答不出"怎么回滚"的方案不叫方案
- **先量化再优化**——"CI 慢""服务不稳"必须落到具体数字
- **安全默认关闭**——最小权限、短期凭据、密钥不落盘

## 架构

```
devops-engineer/
├── SKILL.md                  # L1 路由层：能力索引 + grep 关键词，只做分发
├── references/               # L2 深层 playbook，按需加载
│   ├── ci-cd-pipeline.md            分层门禁 / fail-fast / 四个提速杠杆 / 密钥与权限
│   ├── containerization.md          多阶段构建 / 层缓存 / 镜像瘦身 / 信号处理
│   ├── kubernetes.md                何时不该上 K8s / 资源配额 / 三探针 / 排查路径
│   ├── infrastructure-as-code.md    state 管理 / 模块化 / 多环境隔离 / 危险操作
│   ├── observability.md             三支柱 / 四黄金信号 / 高基数陷阱 / SLO 与燃烧率
│   ├── deployment-strategies.md     滚动·蓝绿·金丝雀选型 / 扩展-收缩 / 回滚
│   ├── ssh-deploy.md                rsync 同步 / 版本目录+软链接 / systemd 托管 / 回滚
│   └── incident-response.md         分级与角色 / 排查路径 / 沟通模板 / 无指责复盘
├── skills/                   # L3 细粒度子技能，可单独安装
│   ├── ci-cd-pipeline/
│   ├── docker-deploy/
│   ├── infra-as-code/
│   ├── monitor-logging/
│   └── ssh-deploy/
├── scripts/                  # L4 确定性脚本，纯标准库、零依赖、不联网
│   ├── dockerfile_lint.py           Dockerfile 生产就绪度审查（12 类规则）
│   ├── ci_audit.py                  GitHub Actions 安全与效率审计
│   ├── k8s_manifest_check.py        K8s manifest 体检（内置 YAML 子集解析器）
│   └── slo_budget.py                错误预算 / 燃烧率 / 多窗口告警阈值
└── assets/                   # L5 生产级模板，全部通过自带脚本严格检查
    ├── github-actions-ci.yml
    ├── Dockerfile.node.multistage + .dockerignore
    ├── k8s-deployment.yaml
    ├── terraform-baseline.tf
    └── postmortem-template.md
```

## 快速开始

### 安装完整技能库（推荐，含 references / scripts / assets）

```bash
npx skills add skills-repo/devops-engineer -g -y
```

### 只安装某个细粒度子技能

```bash
npx skills add skills-repo/devops-engineer@ci-cd-pipeline -g -y
npx skills add skills-repo/devops-engineer@docker-deploy -g -y
npx skills add skills-repo/devops-engineer@infra-as-code -g -y
npx skills add skills-repo/devops-engineer@monitor-logging -g -y
npx skills add skills-repo/devops-engineer@ssh-deploy -g -y
```

## 直接当工具用

四个脚本不依赖本仓库其他部分，clone 下来就能对你现有项目做体检：

```bash
# Dockerfile 生产就绪度
python3 scripts/dockerfile_lint.py Dockerfile

# CI 工作流安全与效率（含命令注入、action 未 pin、密钥暴露检测）
python3 scripts/ci_audit.py .github/workflows

# K8s manifest 体检（不需要连集群，也不需要装 PyYAML）
python3 scripts/k8s_manifest_check.py k8s/

# SLO 错误预算：还能坏多少、烧得多快、什么时候烧完、告警阈值设在哪
python3 scripts/slo_budget.py --slo 99.9 --window 30 --total 12000000 --bad 9800
```

都支持 `--strict`（有 error/warn 即退出码 1，可直接接进 CI）和 `--json`（供程序消费）。

## 技能清单

| 环节 | 子技能 | 描述 | 来源 |
|------|--------|------|------|
| 🔄 CI/CD | `ci-cd-pipeline` | CI/CD 流水线自动化：质量门禁、测试集成、部署策略 | [衍生](https://skills.sh/addyosmani/agent-skills/ci-cd-and-automation) |
| 🐳 容器化 | `docker-deploy` | Docker 容器化：Dockerfile、compose、镜像优化、安全加固 | [衍生](https://skills.sh/mukul975/anthropic-cybersecurity-skills/hardening-docker-containers-for-production) |
| 🏗️ IaC | `infra-as-code` | Terraform 基础设施即代码：云资源、状态管理、模块化 | [衍生](https://skills.sh/aradotso/data-skills/terraform-iac-data-engineering) |
| 📊 监控 | `monitor-logging` | Datadog 可观测性：日志、APM 追踪、监控告警 | [衍生](https://skills.sh/datadog-labs/agent-skills/agent-skills) |
| 🖥️ 服务器部署 | `ssh-deploy` | SSH/rsync 部署到 Linux 服务器：systemd 托管、可回滚发布、健康检查 | [衍生](https://skills.sh/duck4nh/antigravity-kit/linux-server-expert) |

## 推荐工作流

```
提交代码 ──► CI 分层门禁 ──► 构建镜像 ──► IaC 编排 ──► 灰度发布 ──► 观测 ──► 事故响应
            ci-cd-pipeline   containerization  infrastructure  deployment  observability  incident
                                              -as-code        -strategies                -response
              ci_audit.py    dockerfile_lint  terraform-      k8s_manifest  slo_budget   postmortem
                                 .py          baseline.tf      _check.py       .py       -template
```

每个环节都有配套的 playbook（判断怎么做）、脚本（检查做得对不对）和模板（直接抄）。

## 许可

MIT
