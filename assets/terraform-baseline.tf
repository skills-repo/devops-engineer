// Terraform 项目基线模板
// 设计要点：版本全部锁死、state 远程 + 加锁、环境目录隔离、危险资源加保护、
//          密钥不进 state 明文（能引用就不要硬编码）。
// 对应 playbook: references/infrastructure-as-code.md

terraform {
  // 锁 Terraform 本体版本：CI 与本地必须一致，否则 state 可能被高版本单向升级
  required_version = "~> 1.9.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60" // 锁到 minor，禁止自动跨 major
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  // 远程 state + 分布式锁：本地 state 文件在多人协作下必然出事
  backend "s3" {
    bucket       = "example-tfstate"   // TODO: 换成你的桶，务必开启版本控制
    key          = "prod/network/terraform.tfstate"
    region       = "ap-northeast-1"
    encrypt      = true
    use_lockfile = true                 // TF 1.10+ 原生 S3 锁；旧版用 dynamodb_table
    // dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.region

  // 所有资源统一打标：出账单时能追溯到人和环境
  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "skills-repo/devops-engineer"
      Owner       = var.owner
    }
  }
}

// ── 变量 ─────────────────────────────────────────────────────────────
variable "environment" {
  description = "环境标识，用于命名与打标"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment 只能是 dev / staging / prod。"
  }
}

variable "region" {
  description = "云区域"
  type        = string
  default     = "ap-northeast-1"
}

variable "owner" {
  description = "负责人（团队或邮箱），用于成本归属与故障联系"
  type        = string
}

// 密钥类变量标记 sensitive，避免 plan/apply 输出泄漏
variable "db_password" {
  description = "数据库密码。优先用 secrets manager 动态生成，而不是从外部传入"
  type        = string
  sensitive   = true
  default     = null
}

// ── locals：把命名规则集中一处 ─────────────────────────────────────────
locals {
  name_prefix = "${var.environment}-app"
  is_prod     = var.environment == "prod"
}

// ── 资源示例：带删除保护的有状态资源 ─────────────────────────────────
resource "aws_s3_bucket" "artifacts" {
  bucket = "${local.name_prefix}-artifacts"

  lifecycle {
    // 生产的有状态资源必须防误删：任何会 destroy 它的 plan 都直接失败
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

// ── 输出：只输出下游真正需要的，敏感值标 sensitive ─────────────────────
output "artifacts_bucket" {
  description = "构建产物桶名"
  value       = aws_s3_bucket.artifacts.id
}

// ─────────────────────────────────────────────────────────────────────
// 目录约定（环境隔离靠目录，不靠 workspace）：
//
//   infra/
//     modules/            # 可复用模块，无环境相关硬编码
//       network/
//       service/
//     envs/
//       dev/main.tf       # 引用 modules，backend key = dev/...
//       staging/main.tf
//       prod/main.tf      # 独立 state，误操作炸不到别的环境
//
// CI 集成要点：
//   1. PR 阶段跑 `terraform plan -out=tf.plan` 并把 plan 贴回 PR 评论
//   2. 合并后 apply 的必须是同一个 plan 文件，不要重新 plan（避免漂移）
//   3. `terraform destroy` 永远不进自动化流水线
//   4. 定期跑 `plan -detailed-exitcode` 检测手工改动造成的漂移（exit 2 = 有差异）
// ─────────────────────────────────────────────────────────────────────
