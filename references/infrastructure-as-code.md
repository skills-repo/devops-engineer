# 基础设施即代码 Playbook

> IaC 的价值不是"用代码建资源"，是**让基础设施的每一次变更都可 review、可回溯、可重建**。
> 如果团队还在控制台点，那 Terraform 代码只是一份过期的文档。

## 一、铁律：不要手动改

```
控制台手改 → state 与现实不一致 → 下次 apply 要么报错要么把你的改动删掉
```

紧急情况手改了，必须在 24 小时内补回代码并 `terraform import`（或 `terraform plan` 确认无漂移）。
把"允许手改"当例外，不要当常态。

检测漂移：CI 里定时跑 `terraform plan -detailed-exitcode`，退出码 2 表示有差异，告警。

## 二、State：最需要严肃对待的东西

state 文件记录「代码 ↔ 真实资源」的映射。丢了它，Terraform 就不知道自己管过什么。

### 必须做

```hcl
terraform {
  required_version = "~> 1.9"
  backend "s3" {
    bucket         = "company-tfstate"
    key            = "prod/network/terraform.tfstate"
    region         = "ap-east-1"
    encrypt        = true
    dynamodb_table = "tf-lock"        # 状态锁，防并发 apply
  }
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.70" }
  }
}
```

- **远程 backend**（S3/GCS/Terraform Cloud），绝不用本地 state 管生产
- **开启加密 + 版本控制**（state 里可能含明文密钥）
- **状态锁**：没有锁，两个人同时 apply 会毁掉 state
- **按环境和职责拆分 state**，不要一个 state 管全公司

### state 拆分粒度

```
prod/network/          VPC、子网、路由（几乎不变）
prod/data/             数据库、缓存、对象存储（低频变更）
prod/platform/         K8s 集群、节点组
prod/apps/<service>/   各服务的 IAM、队列、CDN 等（高频变更）
```

拆分依据：**变更频率 + 爆炸半径**。把高频变更的和几乎不变的放一个 state，
等于每次改应用配置都在赌整个 VPC。

### 常用 state 操作

```bash
terraform state list                       # 看管了哪些
terraform state show aws_instance.web      # 看单个资源
terraform import aws_s3_bucket.logs my-bucket   # 纳管已存在资源
terraform state rm aws_instance.old        # 从 state 移除但不销毁
terraform state mv <src> <dst>             # 重构时保住资源不重建
```

**`state rm` 和 `state mv` 前先备份 state 文件**，这两个操作不可撤销。

## 三、模块化

### 什么时候抽模块

```
用过 3 次以上 → 抽模块
只用 1 次      → 不要抽，直接写资源，可读性更重要
```

过早抽象是 IaC 的常见病：为了"复用"把一个 VPC 包成 20 个变量的模块，
结果每次用都要读模块源码才知道怎么传参。

### 模块结构

```
modules/ecs-service/
├── main.tf         资源定义
├── variables.tf    输入（每个都写 description 和 type）
├── outputs.tf      输出
├── versions.tf     provider 版本约束
└── README.md       用法示例（必须有一个可复制的完整例子）
```

变量设计原则：**必填项越少越好，其余给合理默认值**。
超过 15 个变量的模块通常说明抽象层次不对。

### 版本固定

```hcl
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.13.0"          # 精确固定，不用 ~> 或 latest
}
```

公共模块用 `~>` 会在某天自动升级并意外重建资源。生产环境固定到补丁版本。

## 四、多环境

### 推荐：目录隔离（不是 workspace）

```
envs/
├── dev/     main.tf + terraform.tfvars + backend 配置
├── staging/
└── prod/
modules/     共享模块
```

**为什么不用 workspace**：workspace 共享同一份配置代码，容易出现
"dev 能 apply 但 prod 参数不同导致炸掉"，且切错 workspace 直接操作生产的事故常见。
目录隔离虽然有重复，但每个环境的 backend、变量、权限都是显式的。

### 环境差异只放 tfvars

```hcl
# envs/prod/terraform.tfvars
instance_type   = "m6i.xlarge"
min_size        = 3
enable_deletion_protection = true
```

代码结构在各环境应尽量一致，差异收敛到变量。**prod 有而 dev 没有的资源**是排查噩梦的来源。

## 五、CI 集成

```yaml
# PR 阶段
- terraform fmt -check -recursive     # 格式
- terraform validate                  # 语法
- tflint                              # 最佳实践
- tfsec / checkov                     # 安全扫描
- terraform plan -out=tfplan          # 生成计划
- 把 plan 输出贴到 PR 评论            # 人工 review 的核心依据

# 合并后
- terraform apply tfplan              # apply 的是 review 过的那份 plan
```

关键点：

- **apply 必须用 PR 阶段生成的 plan 文件**，而不是重新 plan 再 apply。
  否则 review 的和执行的可能不是一回事
- 生产 apply 加**人工审批门**
- 用 **OIDC** 换取云凭证，不在 CI 里存长期 access key
- plan 输出可能含敏感值，注意 PR 评论的可见范围

## 六、危险操作识别

`terraform plan` 输出里这些标记要停下来看：

| 标记 | 含义 | 风险 |
|------|------|------|
| `+ create` | 新建 | 低 |
| `~ update in-place` | 原地修改 | 低 |
| `-/+ destroy and then create` | **重建** | **高** — 数据库、有状态资源会丢数据 |
| `- destroy` | 删除 | **高** |
| `# forces replacement` | 某属性变更触发重建 | **高** — 检查是哪个属性 |

对有状态资源加保险：

```hcl
lifecycle {
  prevent_destroy = true                     # 阻止误删
  ignore_changes  = [tags["LastModified"]]   # 忽略外部系统写入的字段
}
```

`prevent_destroy` 应该是所有生产数据库、对象存储桶的默认配置。

## 七、密钥处理

```hcl
# ✗ 密钥写进 tf 文件（进 git 且进 state）
resource "aws_db_instance" "main" {
  password = "hunter2"
}

# ✓ 从密钥管理服务读取
data "aws_secretsmanager_secret_version" "db" {
  secret_id = "prod/db/password"
}
resource "aws_db_instance" "main" {
  password = jsondecode(data.aws_secretsmanager_secret_version.db.secret_string)["password"]
}
```

**注意**：即使这样，密码仍会以明文出现在 state 文件里。所以 state 必须加密 + 严格控权。
更彻底的做法是让资源自己生成密钥并直接写入密钥管理服务，Terraform 不接触明文。

## 八、常见故障

| 症状 | 原因 | 处理 |
|------|------|------|
| `Error acquiring the state lock` | 上次 apply 异常中断 | 确认无人在跑后 `terraform force-unlock <ID>` |
| plan 显示大量意外变更 | 漂移（有人手改）或 provider 升级 | 逐条看；provider 大版本升级前读 upgrade guide |
| apply 到一半失败 | 部分资源已创建 | **不要删 state**。修复问题后重新 apply，Terraform 会续上 |
| 资源在云上已删，state 还有 | 手动删除 | `terraform state rm` 或直接 apply 重建 |
| 循环依赖 | 模块间互相引用 | 拆分或用 data source 打破 |
| 模块升级后资源被重建 | 模块内部资源地址变了 | 用 `moved` block 或 `state mv` 保住资源 |

## 九、Terraform 之外

| 工具 | 定位 |
|------|------|
| **Terraform / OpenTofu** | 云资源编排，声明式，生态最广 |
| **Pulumi** | 用通用语言写 IaC，适合需要复杂逻辑的场景 |
| **Ansible** | 配置管理（机器内部），与 Terraform 互补而非竞争 |
| **Crossplane** | 在 K8s 内声明云资源，适合已重度使用 K8s 的平台团队 |

典型分工：**Terraform 建资源 → Ansible/cloud-init 配机器 → K8s 跑应用**。
不要用 Terraform 管应用部署（它没有滚动更新和回滚语义）。

---

## 相关子技能与层次边界

本 playbook 负责**IaC 的决策与纪律**（state、模块化、多环境、危险操作、密钥处理）；
Terraform 资源定义与 CI 集成的具体写法请调对应子技能。

- 落地到 [`skills/infra-as-code/SKILL.md`](../skills/infra-as-code/SKILL.md)：资源声明、远程 state、模块复用、terraform plan/apply 流水线的具体写法与命令。
- 兄弟参考：
  - [`references/ci-cd-pipeline.md`](ci-cd-pipeline.md)：把 `terraform plan/apply` 接进 CI 做变更门禁。
  - [`references/deployment-strategies.md`](deployment-strategies.md)：IaC 变更同样需要回滚预案与扩展-收缩思路。
  - [`references/incident-response.md`](incident-response.md)：IaC 误变更是常见事故源，需按事故流程处置。
  - [`references/scripts-usage.md`](scripts-usage.md)：IaC 相关体检见 `k8s_manifest_check.py` 与 `ci_audit.py`。
