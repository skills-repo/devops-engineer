---
name: docker-deploy
description: Docker 容器化部署，自动生成 Dockerfile 和 docker-compose，支持零停机部署
metadata:
  category: 容器化
  platform: 通用
  difficulty: 进阶
---

# Docker 容器化部署

> 将应用容器化并编排部署，自动生成最佳实践的 Dockerfile 和 docker-compose 配置。

## 能力

- **Dockerfile 生成**：多阶段构建、最小镜像、安全扫描
- **Compose 编排**：多服务编排与网络配置
- **优化建议**：层缓存、镜像瘦身、启动速度优化
- **部署策略**：滚动更新、蓝绿部署、健康检查
- **环境管理**：开发/测试/生产环境分离

## 使用方式

在 Claude Code 中使用 `/docker-deploy` 调用。

```
/docker-deploy 为这个 Go 项目生成 Dockerfile
/docker-deploy 把这个应用和数据库编排成 docker-compose
```

## 工作流

1. 分析项目结构，识别运行时依赖
2. 生成 Dockerfile（多阶段构建、非 root 用户）
3. 生成 docker-compose.yml（应用 + 数据库 + 缓存）
4. 添加健康检查和 restart 策略
5. 输出构建和部署命令

## 适用场景

- 应用容器化首次尝试
- 从单机部署迁移到 Docker
- 本地开发环境标准化
- VPS/云服务器上的生产部署

## 限制

- 不涉及 Kubernetes 编排
- 复杂微服务网络需配合服务网格
- 镜像安全扫描结果需人工确认