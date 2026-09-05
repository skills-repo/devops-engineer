# 容器化 Playbook

> 镜像的三个目标，按重要性排序：**可复现** > **安全** > **小**。
> 大多数教程只讲第三个，但生产事故几乎都出在前两个。

## 一、Dockerfile 骨架：多阶段构建

```dockerfile
# ---- 依赖层（变化最少，缓存命中率最高）----
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

# ---- 构建层 ----
FROM node:22-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN pnpm build

# ---- 运行层（只带运行时必需品）----
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN addgroup -S app && adduser -S app -G app
COPY --from=build --chown=app:app /app/dist ./dist
COPY --from=deps --chown=app:app /app/node_modules ./node_modules
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD node -e "fetch('http://localhost:3000/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/main.js"]
```

要点逐条对应下面各节。

## 二、层缓存：顺序决定构建速度

Docker 逐层缓存，**任何一层失效，其后所有层都要重建**。所以按变化频率从低到高排列：

```
基础镜像 → 系统包 → 依赖清单 → 安装依赖 → 源码 → 构建
  低频 ─────────────────────────────────────────→ 高频
```

**头号反模式**：

```dockerfile
COPY . .                    # 改任何一个文件都会让下一行失效
RUN npm install
```

正确做法是先只 COPY lock 文件，装完依赖再 COPY 源码。

配套必须写 `.dockerignore`，否则 `.git`、`node_modules`、构建产物会进构建上下文：

```
.git
node_modules
dist
*.log
.env*
**/__pycache__
```

## 三、可复现：锁死一切版本

| 项 | 反例 | 正例 |
|----|------|------|
| 基础镜像 | `FROM node:latest` | `FROM node:22.14-alpine3.21`，生产可再固定 digest |
| 系统包 | `apt-get install curl` | 固定版本 或 至少 `--no-install-recommends` |
| 语言依赖 | `npm install` | `npm ci` / `pnpm install --frozen-lockfile` / `pip install -r requirements.txt --require-hashes` |
| 构建参数 | 依赖构建机环境变量 | 显式 `ARG` 并有默认值 |

`latest` 标签在生产环境是定时炸弹：今天构建和下周构建可能是不同的操作系统。

## 四、安全加固清单

- [ ] **非 root 运行**：`USER` 指令必须有。容器逃逸时 root 意味着宿主机 root
- [ ] **只读根文件系统**：运行时加 `--read-only`，需要写的目录挂 tmpfs
- [ ] **不装不必要的东西**：生产镜像里不该有 curl、wget、bash、包管理器、编译工具
- [ ] **不放密钥**：不 COPY `.env`、不 `ARG SECRET=`（会留在镜像历史里）
- [ ] **丢弃能力**：`--cap-drop=ALL`，按需加回
- [ ] **镜像扫描**：CI 里跑 trivy / grype，高危漏洞阻断
- [ ] **签名与来源**：生产镜像用 cosign 签名，部署时验签

### 密钥的正确传递方式

```dockerfile
# ✗ 会永久留在镜像层历史里
ARG NPM_TOKEN
RUN echo "//registry.npmjs.org/:_authToken=${NPM_TOKEN}" > .npmrc

# ✓ BuildKit secret mount，不进入任何层
RUN --mount=type=secret,id=npmrc,target=/root/.npmrc \
    pnpm install --frozen-lockfile
```

运行时密钥一律走环境变量或密钥管理服务，不打进镜像。

## 五、瘦身：按收益排序

| 手段 | 典型收益 | 代价 |
|------|---------|------|
| 多阶段构建，只拷产物 | **最大**，常见 1.2GB → 150MB | 无 |
| 换 slim / alpine 基础镜像 | 大 | alpine 用 musl，某些原生模块要重编 |
| distroless / scratch | 大 | 无 shell，调试困难 |
| 合并 RUN 层、清理缓存 | 中 | 可读性略降 |
| 删文档/locale | 小 | 收益不值得复杂度 |

```dockerfile
# 清理必须和安装在同一 RUN 里，否则删除层之前的文件仍在镜像中
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
```

**alpine 的坑**：musl libc 与 glibc 行为差异（DNS 解析、时区、某些 Python wheel 不可用）。
Python/ML 场景通常 `-slim`（Debian）比 alpine 更省心，构建也更快。

## 六、健康检查与优雅退出

### HEALTHCHECK

- 检查真实依赖（能连上数据库），不要只返回 200
- `start-period` 要覆盖冷启动时间，否则启动期就被判死
- 编排层（K8s）有自己的探针时，Dockerfile 的 HEALTHCHECK 是给本地/compose 用的

### 信号处理

容器停止时收到 `SIGTERM`，应用必须优雅退出，否则请求会被硬切断。

```dockerfile
# ✗ shell 形式，PID 1 是 sh，信号不会传给 node
CMD npm start

# ✓ exec 形式，应用直接是 PID 1
CMD ["node", "dist/main.js"]
```

应用侧要监听 SIGTERM → 停止接新请求 → 等待在途请求完成 → 退出。
不处理信号的容器会在每次部署时丢请求。

## 七、Compose：本地与小规模编排

```yaml
services:
  api:
    build:
      context: .
      target: runtime
    env_file: .env.local
    ports: ["3000:3000"]
    depends_on:
      db:
        condition: service_healthy    # 关键：不是启动就绪，是健康才继续
    restart: unless-stopped

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      retries: 10

volumes:
  pgdata:
```

要点：

- `depends_on` 默认只等**启动**不等**就绪**，必须配 `condition: service_healthy`
- 数据一律用 named volume，不要用容器内路径（删容器即丢数据）
- 本地开发用 `docker-compose.override.yml` 挂载源码热重载，不污染基础配置
- Compose 适合本地和单机小规模；多节点、需要自愈和滚动更新时上 K8s（见 `kubernetes.md`）

## 八、排查手册

| 症状 | 排查 |
|------|------|
| 构建每次都很慢 | 层顺序错了（COPY . . 太早）或没 .dockerignore |
| 本地能跑，CI 构建失败 | 依赖没锁版本 / 构建上下文不同 / 平台架构差异（arm64 vs amd64） |
| 容器起来就退出 | `docker logs`；常见是 CMD 前台进程结束、配置缺失、端口占用 |
| 部署时丢请求 | 没处理 SIGTERM，或 CMD 用了 shell 形式 |
| 镜像莫名很大 | `docker history <image>` 逐层看，通常是构建产物没走多阶段 |
| 容器内改了文件，重启就没了 | 正常，容器文件系统是临时的。需要持久化就挂 volume |
| 跨平台镜像跑不起来 | 用 `docker buildx build --platform linux/amd64,linux/arm64` 构建多架构 |

---

## 相关子技能与层次边界

本 playbook 负责**镜像怎么写才生产就绪**（多阶段、层缓存、安全加固、瘦身、优雅退出）的决策与踩坑；
具体 Dockerfile / compose 写法请调对应子技能。

- 落地到 [`skills/docker-deploy/SKILL.md`](../skills/docker-deploy/SKILL.md)：Dockerfile 编写、compose 多服务编排、镜像优化、安全加固的具体写法与命令。
- 兄弟参考：
  - [`references/kubernetes.md`](kubernetes.md)：容器之上何时该上 K8s、三探针与资源配额怎么定。
  - [`references/deployment-strategies.md`](deployment-strategies.md)：构建好的镜像如何发布（蓝绿/金丝雀/回滚）。
  - [`references/ci-cd-pipeline.md`](ci-cd-pipeline.md)：把镜像构建放进 CI，用缓存提速、用门禁挡劣质镜像。
  - [`references/scripts-usage.md`](scripts-usage.md)：`dockerfile_lint.py` 对现有 Dockerfile 做 12 类规则体检。
