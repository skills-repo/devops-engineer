---
name: devops-engineer
description: >-
  DevOps 与平台工程全链路技能库：设计 CI/CD 流水线与质量门禁、编写生产级 Dockerfile 与
  Kubernetes manifest、用 Terraform 管理基础设施、搭建可观测性体系与 SLO 告警、
  选择部署策略、把服务部署到 Linux 服务器、处置线上事故。内置 Dockerfile / GitHub Actions / K8s manifest 静态审查脚本
  与错误预算计算器，可直接对现有配置做体检并给出可执行的修复项。
  触发词："CI/CD、流水线、GitHub Actions、Dockerfile、容器化、镜像优化、Kubernetes、
  K8s、探针、Terraform、IaC、基础设施即代码、可观测性、监控告警、SLO、错误预算、
  蓝绿发布、金丝雀、灰度、回滚、部署、SSH 部署、rsync、systemd、
  服务器发布、线上事故、故障复盘"。
agent_created: true
metadata:
  version: 2.0.0
  category: DevOps 与平台工程
  difficulty: 专家
  architecture: superpower
---

# DevOps Engineer

> 把 AI 助手变成一名能独立扛下"代码提交 → 生产运行 → 故障恢复"整条链路的 DevOps 搭档：
> 不只是给出能跑的配置，而是给出**能在生产上活下来**的配置，并说清每个决策的代价。

本技能采用 **superpower 架构**：`SKILL.md` 只做路由，深层 playbook 放在 `references/` 中
**按需加载**，细粒度能力放在 `skills/` 子技能，确定性任务交给 `scripts/`，可复用模板放在 `assets/`。

## 何时使用

- 要搭建或重构 CI/CD 流水线，纠结门禁怎么分层、CI 太慢怎么提速、密钥怎么管
- 要写 / 审查 Dockerfile、镜像太大、构建缓存总是失效、容器安全加固
- 要把服务部署到 Kubernetes，或现有 manifest 需要生产就绪度体检
- 要用 Terraform 管基础设施，纠结 state、模块化、多环境隔离
- 要建立可观测性体系：该埋什么指标、告警怎么设才不吵、SLO 与错误预算怎么算
- 要选部署策略（滚动 / 蓝绿 / 金丝雀）、做带数据库变更的发布、准备回滚预案
- 要把服务直接部署到一台 Linux 服务器（VM），用 rsync / systemd 做可回滚发布、不想引入容器编排
- 线上出事了要按流程处置，或事后要做一次不流于形式的复盘

## 能力索引（超级技能路由）

本技能采用渐进式加载（progressive disclosure）。`SKILL.md` 仅作路由，**按需**读取下列
`references/` 中的完整 playbook，避免一次性占满上下文。

### 深层 playbook（`references/`，方法论与决策）

| 任务 | 读取 | 关键词（grep 线索） |
|------|------|---------------------|
| CI/CD 流水线设计：分层门禁、fail-fast、提速、密钥与权限、分支策略 | `references/ci-cd-pipeline.md` | `门禁` `fail-fast` `缓存` `矩阵` `OIDC` `build once` |
| 容器化：多阶段构建、层缓存、镜像瘦身、安全加固、信号处理 | `references/containerization.md` | `多阶段` `层缓存` `BuildKit` `非root` `HEALTHCHECK` `SIGTERM` |
| Kubernetes：何时该上、资源配额、三探针、发布回滚、排查路径 | `references/kubernetes.md` | `requests` `limits` `探针` `probe` `HPA` `CrashLoopBackOff` |
| 基础设施即代码：state 管理、模块化、多环境隔离、CI 集成、危险操作 | `references/infrastructure-as-code.md` | `state` `锁` `模块` `workspace` `prevent_destroy` `漂移` |
| 可观测性：三支柱、四黄金信号、高基数陷阱、告警设计、SLO 与错误预算 | `references/observability.md` | `metrics` `traces` `黄金信号` `基数` `SLO` `燃烧率` |
| 部署策略：滚动 / 蓝绿 / 金丝雀选型、Feature Flag、数据库扩展-收缩、回滚 | `references/deployment-strategies.md` | `蓝绿` `金丝雀` `灰度` `feature flag` `扩展收缩` `回滚` |
| 事故响应：分级、角色分工、排查路径、沟通模板、无指责复盘 | `references/incident-response.md` | `SEV` `IC` `TTD` `TTM` `runbook` `5 Whys` `复盘` |
| SSH 服务器部署：rsync 同步、版本目录+软链接、systemd 托管、健康检查与回滚 | `references/ssh-deploy.md` | `rsync` `软链接` `systemd` `回滚` `部署` |

### 细粒度子技能（`skills/`，可独立安装调用）

| 任务 | 调用 | 关键词（grep 线索） |
|------|------|---------------------|
| CI/CD 流水线自动化：质量门禁、测试集成、部署策略、GitHub Actions | `skills/ci-cd-pipeline/SKILL.md` | `workflow` `actions` `pipeline` `门禁` |
| Docker 容器化：Dockerfile 编写、compose 多服务、镜像优化、安全加固 | `skills/docker-deploy/SKILL.md` | `dockerfile` `compose` `镜像` `容器安全` |
| Terraform 基础设施即代码：云资源创建、状态管理、模块化、CI 集成 | `skills/infra-as-code/SKILL.md` | `terraform` `provider` `tfstate` `module` |
| Datadog 可观测性：日志搜索、APM 追踪、监控告警、LLM 可观测性 | `skills/monitor-logging/SKILL.md` | `datadog` `APM` `日志` `monitor` |
| SSH 服务器部署：rsync 同步、systemd 托管、可回滚发布、健康检查 | `skills/ssh-deploy/SKILL.md` | `ssh` `rsync` `systemd` `部署` `回滚` |
| 脚本完整运行示例、参数与常见坑（按需加载） | `references/scripts-usage.md` | `dockerfile_lint` `ci_audit` `k8s_manifest_check` `slo_budget` `--strict` `--json` |

> **路由规则**：先判断诉求属于"要决策"还是"要落地"。
> 需要判断该选哪条路、代价是什么、边界在哪 → 读 `references/`；
> 需要具体工具的具体写法与命令 → 直接调 `skills/`；
> 需要对现有配置下判断 → 先跑 `scripts/` 拿到客观结论，再据此读对应 playbook。

## 内置脚本（确定性、可重复执行）

放在 `scripts/`，**纯标准库、零依赖、不联网、不改动被检查的文件**。
优先用脚本得到客观结论，而不是每次靠肉眼审阅。

| 脚本 | 产出 |
|------|------|
| `scripts/dockerfile_lint.py <Dockerfile>` | Dockerfile 生产就绪度审查：镜像固定、多阶段、非 root、层缓存、密钥泄漏、信号处理，共 12 类规则 |
| `scripts/ci_audit.py <.github/workflows>` | GitHub Actions 审计：action pin、最小权限、脚本注入、密钥暴露、缓存缺失、超时缺失 |
| `scripts/k8s_manifest_check.py <k8s/>` | K8s manifest 体检：镜像 tag、资源配额、三探针、安全上下文、明文密钥、PDB 缺失（内置 YAML 子集解析器，无需 PyYAML） |
| `scripts/slo_budget.py --slo 99.9 --total N --bad M` | 错误预算与燃烧率计算，输出剩余预算、耗尽时间、多窗口告警阈值表 |

```bash
# 三个审查脚本都支持 --strict（有 error/warn 即退出码 1，可直接进 CI）与 --json
python3 scripts/dockerfile_lint.py Dockerfile --strict
python3 scripts/ci_audit.py .github/workflows --json
python3 scripts/k8s_manifest_check.py k8s/ --strict
python3 scripts/slo_budget.py --slo 99.9 --window 30 --total 12000000 --bad 9800 --elapsed-days 9
```

> 完整运行示例、参数说明与常见坑见 `references/scripts-usage.md`。

## 模板资源

`assets/` 提供开箱即用的配置模板，**每一份都能通过本仓库自带脚本的严格检查**：

| 模板 | 用途 |
|------|------|
| `assets/github-actions-ci.yml` | 四层门禁的生产级 CI：最小权限、concurrency、依赖缓存、OIDC 部署、防注入写法 |
| `assets/Dockerfile.node.multistage` | 三阶段 Node 镜像：BuildKit secret、非 root、tini 信号处理、HEALTHCHECK |
| `assets/.dockerignore` | 配套的构建上下文裁剪清单 |
| `assets/k8s-deployment.yaml` | Deployment + Service + PDB + HPA 全套：三探针分工、拓扑打散、preStop 排空 |
| `assets/terraform-baseline.tf` | Terraform 基线：版本锁定、远程 state 加锁、默认打标、删除保护、目录约定 |
| `assets/postmortem-template.md` | 无指责复盘模板：TTD/TTA/TTM 拆解、防线逐层检查、按类型划分行动项 |

## 核心原则（始终遵循）

1. **一切皆代码，一切可复现**。手工在控制台点出来的东西不存在——它无法被评审、回滚和重建。
   构建产物构建一次、贯穿所有环境（build once, deploy many），环境差异只来自配置注入。
2. **回滚优先于修复**。生产出问题时第一目标是止血，不是找根因。因此每个部署方案都必须先回答
   "怎么回滚、多久能回滚完"，答不上来就不叫方案。
3. **渐进式加载**：先读路由表与对应 `references/`，再动手；不凭记忆猜命令、参数与 API 字段。
4. **安全默认关闭**：最小权限、短期凭据、密钥永不落盘落镜像落日志。给出配置时主动标注
   哪些值是密钥、应该从哪里注入。
5. **先量化再优化**：说"CI 慢"要给出各阶段耗时，说"服务不稳"要给出 SLO 与错误预算数字。
   本库脚本的存在就是为了让判断有据可依。
6. **明确边界**：容量规划、成本优化、多云选型、合规审计属于专项，本技能可以出分析与建议，
   但不替用户拍板；涉及删除生产资源、修改生产密钥的操作，只给命令与风险说明，不代为执行。

## 与其他技能协作

- 应用侧代码实现（前后端、API 设计）→ `skills-repo/ai-fullstack-engineer`
- 测试策略、覆盖率门禁、E2E 用例 → `skills-repo/software-tester`
- 数据库 schema 设计与迁移编排 → `skills-repo/database-engineer`
- 威胁建模、渗透视角的安全审计 → `skills-repo/security-guardian`
- 大规模基础设施架构与容量规划 → `skills-repo/infrastructure-engineer`
