# DevOps Engineer — Agent 入口

> 本仓库是 skills-repo 组织下的 DevOps 与平台工程技能库，采用 **superpower 架构（Level A）**。
> Agent 在处理 CI/CD、容器化、Kubernetes、IaC、可观测性、部署与事故响应任务时加载本文件。

## 加载顺序（务必遵守）

```
1. SKILL.md            必读。路由层，判断任务归属哪一条能力线
2. scripts/*.py        要对现有配置下判断时，先跑脚本拿客观结论
3. references/*.md     按路由表命中的那一篇读，不要全部读入
4. skills/*/SKILL.md   需要某个具体工具的具体写法时才读
5. assets/*            要产出配置时，以模板为起点改，而不是从零手写
```

**不要一次性把 `references/` 全读进上下文**——这会抵消 superpower 架构的全部收益。
根 SKILL.md 的路由表已给出每篇的 grep 关键词，按需精确命中。

**审查类任务必须先跑脚本**。用户拿来一份 Dockerfile / workflow / manifest 让你"看看有没有问题"，
先跑对应脚本，再基于输出的具体条目展开讲，不要肉眼扫一遍就下结论。

## 目录约定

| 层 | 路径 | 内容 |
|----|------|------|
| L1 路由 | `SKILL.md` | 能力索引表、grep 关键词、核心原则 |
| L2 方法论 | `references/` | 7 篇深层 playbook，按需加载 |
| L3 子技能 | `skills/<name>/SKILL.md` | 4 个细粒度能力，可单独安装，**路径不可改名** |
| L4 脚本 | `scripts/` | 4 个确定性检查脚本，纯标准库、零依赖、只读不改 |
| L5 模板 | `assets/` | 6 份生产级模板，全部通过 L4 脚本严格检查 |

## references 索引

| 文件 | 解决什么 |
|------|---------|
| `ci-cd-pipeline.md` | 门禁怎么分层、CI 为什么慢、密钥与权限、分支策略、build once |
| `containerization.md` | 多阶段构建、层缓存失效、镜像瘦身、安全加固、SIGTERM 优雅退出 |
| `kubernetes.md` | 什么情况下不该上 K8s、资源配额怎么定、三探针分工、故障排查路径 |
| `infrastructure-as-code.md` | state 远程与加锁、模块化边界、多环境隔离、漂移检测、危险操作清单 |
| `observability.md` | 三支柱取舍、四黄金信号、高基数成本陷阱、告警设计、SLO 与燃烧率 |
| `deployment-strategies.md` | 滚动/蓝绿/金丝雀选型、Feature Flag、数据库扩展-收缩、回滚检查清单 |
| `incident-response.md` | 事故分级、IC 角色分工、排查路径、对外沟通模板、无指责复盘与 5 Whys |

## scripts 索引

| 脚本 | 何时用 | 退出码 |
|------|--------|--------|
| `dockerfile_lint.py <file>` | 审查 Dockerfile，或产出 Dockerfile 后自检 | 有 error 时 1；`--strict` 时 warn 也算 1 |
| `ci_audit.py <dir/file>` | 审查 GitHub Actions，尤其关注 action 未 pin 与命令注入 | 同上 |
| `k8s_manifest_check.py <dir/file>` | 审查 K8s manifest，上线前生产就绪度体检 | 同上 |
| `slo_budget.py --slo N ...` | 需要把可用性目标翻译成具体数字，或设计告警阈值 | 0 |

统一约定：都支持 `--json`（结构化输出，便于二次处理）与 `--strict`（进 CI 用）。
脚本**只读不写**，不会修改被检查的文件，可以放心对用户的真实项目执行。

## 子技能清单

| 技能 | 文件 | 用途 |
|------|------|------|
| ci-cd-pipeline | `skills/ci-cd-pipeline/SKILL.md` | GitHub Actions 流水线自动化与质量门禁 |
| docker-deploy | `skills/docker-deploy/SKILL.md` | Dockerfile、compose、镜像优化与安全加固 |
| infra-as-code | `skills/infra-as-code/SKILL.md` | Terraform 云资源、状态管理、模块化 |
| monitor-logging | `skills/monitor-logging/SKILL.md` | Datadog 日志、APM、监控告警 |

## 行为准则

1. **先量化再建议**。用户说"CI 太慢"，先要各阶段耗时；说"服务不稳"，先算 SLO 与错误预算。
   没有数字的优化建议一律是猜。
2. **每个方案附带回滚路径**。给出部署方案时必须同时说明怎么回滚、多久回滚完、有没有不可逆步骤
   （尤其是数据库迁移）。
3. **密钥零容忍**。发现配置里有明文密钥，立刻标为最高优先级，并提醒用户轮换——已经提交过的
   密钥即使删掉也仍在 git 历史里。
4. **不代为执行破坏性操作**。`terraform destroy`、`kubectl delete`、删除生产资源、覆盖 state：
   只给命令 + 风险说明 + 确认清单，由用户自己执行。
5. **区分"能跑"和"能上生产"**。快速演示可以给最小配置，但要明确标注它缺了什么（资源配额、
   探针、非 root、密钥外置），不要让用户误以为可以直接上线。
6. **承认边界**。容量规划、成本优化、多云选型、合规审计出分析不出结论；跨服务架构级改造
   转 `skills-repo/infrastructure-engineer`。

## 技能来源

4 个子技能改编自 skills.sh 社区的成熟技能，详情见各 SKILL.md 的 `source` 字段。
`references/`、`scripts/`、`assets/` 为本仓库原创。
