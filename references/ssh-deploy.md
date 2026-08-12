# SSH 服务器部署 Playbook

> 把"构建产物 → 一台 Linux 服务器 → 跑起来"这条最朴素、也最常见的部署链路做对。
> 适用场景：单台/少量 VM、没有 K8s、不想引入容器编排的小团队服务、定时脚本、内部工具。
> 本文只讲**机制**（怎么把文件送上去、怎么重启、怎么回滚），发布**策略**（蓝绿/金丝雀/扩展-收缩）
> 见 `deployment-strategies.md`，容器化见 `containerization.md`，K8s 见 `kubernetes.md`。

## 一、什么时候该用 SSH 部署（决策树）

```
诉求是"把服务放到服务器上跑"？
├── 目标环境是 K8s 集群？        → 走 kubernetes.md，别手动 ssh
├── 目标环境是 PaaS（Vercel/Heroku/Fly）？ → 用平台 CLI，不用本文
├── 多实例、需要自动扩缩容？     → kubernetes.md 或 PaaS
└── 单台/少量 VM、简单服务？     → ✅ 本文（SSH + rsync + systemd）
```

SSH 部署的核心优势：**透明、可控、零额外基础设施**。你完全知道文件在哪、进程归谁管。
代价：扩缩容、自愈、灰度都要自己写，不适合规模化的场景。把这件事做对的前提是
**一切走脚本、一切可回滚、密钥不落地**。

## 二、前置条件（部署前必须确认）

- [ ] **密钥登录**：部署机用 `ssh-copy-id deploy@host` 配好公钥，禁用密码登录（`PasswordAuthentication no`）。
      绝不把私钥 scp 到服务器；需要拉取私有仓库时用 ssh agent forwarding（`ssh -A`）或
      部署机专用 deploy key，而不是复用开发机密钥。
- [ ] **部署用户**：建专用 `deploy` 用户，仅对该服务目录有写权；用 `sudo` 仅放开
      `systemctl restart <svc>` / `nginx -s reload` 等白名单命令（`/etc/sudoers.d/deploy`），
      不开 NOPASSWD 全权限。
- [ ] **目录约定**（推荐，回滚依赖它）：

```
/var/www/app/
├── releases/           # 每次发布一个带时间戳的目录
│   ├── 20260812-1430/
│   └── 20260811-0915/  # 上一个版本，回滚用
├── current -> releases/20260812-1430   # 软链接，原子切换
├── shared/             # 跨版本共享：.env、uploads、logs、sockets
└── tmp/
```

- [ ] **健康检查端点**：服务暴露 `/healthz` 或监听端口可探测，回滚前靠它判断新版本是否真起来了。
- [ ] **`.env` 在 `shared/` 而不在仓库**：密钥永不进版本库（见 `security-guardian` 的密钥管理原则）。

## 三、标准发布流程（带版本目录 + 软链接）

```bash
HOST=deploy@server
RELEASE=$(date +%Y%m%d-%H%M)
BASE=/var/www/app

# 1) 构建产物已在本机 dist/。先建版本目录（--link-dest 做硬链接去重，省空间省时间）
ssh $HOST "mkdir -p $BASE/releases/$RELEASE"
rsync -az --delete --exclude=node_modules --link-dest=$BASE/current/ \
      dist/ $HOST:$BASE/releases/$RELEASE/

# 2) 链接共享文件（.env / 上传目录），不要复制
ssh $HOST "ln -sfn $BASE/shared/.env $BASE/releases/$RELEASE/.env"

# 3) 原子切换软链接（rename 是原子的，正在运行的进程不受影响）
ssh $HOST "ln -sfn $BASE/releases/$RELEASE $BASE/current"

# 4) 重启服务（systemd 管理进程）
ssh $HOST "sudo systemctl restart app.service"

# 5) 健康检查（不通过立刻回滚，见第四节）
ssh $HOST "curl -fsS http://localhost:8000/healthz" || { echo 'HEALTH FAIL'; ...回滚...; }
```

**零停机的关键点**：
- 软链接切换 + 优雅重启（`ExecReload` / `systemd` 的 `Type=notify` 或 `KillSignal=SIGTERM` 等进程自己排空）。
- 纯 web 服务：前面挂 nginx，切换软链接后 `nginx -s reload`（reload 是优雅的）。
- 做不到真正零停机（如长连接服务）：接受几秒中断，但**永远先确认新版本能起再切流量**。

## 四、回滚（必备，且要先验证能回滚）

```bash
# 保留最近 N 个版本即可，回滚就是改回上一个软链接 + 重启
PREV=$(ls -1t $BASE/releases/ | sed -n '2p')   # 上一个版本
ssh $HOST "ln -sfn $BASE/releases/$PREV $BASE/current && sudo systemctl restart app.service"
ssh $HOST "curl -fsS http://localhost:8000/healthz" && echo 'ROLLBACK OK'
```

回滚要做到"答得出多久能回滚完"——理想 < 30 秒。定期演练：很多团队只在出事时才第一次
回滚，结果回滚脚本自己也有 bug。**把回滚当成发布的一部分，每次发布后顺手验证一次回滚路径**。

清理：`ls -1t releases/ | tail -n +6 | xargs -r rm -rf`（保留最近 5 个）。

## 五、systemd 单元（进程管理的基础）

`/etc/systemd/system/app.service` 最小可用：

```ini
[Unit]
Description=My App
After=network.target

[Service]
User=deploy
WorkingDirectory=/var/www/app/current
ExecStart=/var/www/app/current/bin/server
EnvironmentFile=/var/www/app/shared/.env
Restart=on-failure
RestartSec=3
# 优雅停机：给进程时间排空，而不是 SIGKILL
KillSignal=SIGTERM
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

常用：`systemctl status app`、`journalctl -u app -f`、`systemctl reload`、
`systemctl edit app`（不改原文件追加配置，符合"只增不减"）。

## 六、常见陷阱（踩坑清单）

| 坑 | 现象 | 正确做法 |
|----|------|----------|
| `rsync --delete` 误删 | 把整个目录清掉 | 对 `releases/<ver>/` 用 `--delete`，**绝不对 `shared/` 用**；先在 `--dry-run` 看差异 |
| 权限/属主不对 | 服务起不来，Permission denied | 部署用户持有目录；`EnvironmentFile` 权限 `600` 且仅 deploy 可读 |
| 旧进程残留 | 端口被占，新版本起不来 | 重启前确认旧进程已退出（`systemctl restart` 自带）；不要用 `kill -9` 跳过优雅停机 |
| 密钥落盘 | 泄露、被扫 | `.env` 在 `shared/`；私钥永不 scp；用 deploy key / agent forwarding |
| 盲目重启无健康检查 | 切到了起不来的版本，全体 502 | 重启后必跑 `/healthz` 探测，失败立即回滚 |
| 数据库迁移与发布耦合 | 回滚代码但 schema 已变，回不去 | 迁移脚本与应用**解耦部署**（见 `deployment-strategies.md` 扩展-收缩）；先迁数据再发代码 |
| 主机指纹未收录 | 首次 ssh 卡住或 `REMOTE HOST IDENTIFICATION` | 预置 `known_hosts` 或 `StrictHostKeyChecking accept-new`，但不可直接 `no`（中间人风险） |
| 在服务器上直接改文件 | 配置漂移，回滚把改动覆盖掉 | 一切变更走发布流程，服务器是只读目标 |

## 七、与 CI/CD 的关系

本文是"部署动作"本身。把它接进 `ci-cd-pipeline.md` 的部署阶段即可：打 tag →
跑测试 → 构建产物 → 触发上面的发布脚本（建议用带超时和自动回滚的部署 step，失败即自动回滚）。
构建一次、用同一产物做发布（build once, deploy many），环境差异只来自 `shared/.env` 注入。
