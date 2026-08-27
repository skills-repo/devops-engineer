# Kubernetes 部署与运维 Playbook

> K8s 的核心心智模型：**你声明期望状态，控制器不断把现实拉向它**。
> 排查问题时永远问两个问题：期望是什么？现实是什么？差距卡在哪个控制器上？

## 一、什么时候不该上 K8s

先说这个，因为过早引入 K8s 是常见的自伤：

| 场景 | 建议 |
|------|------|
| 单体应用、单机能跑、流量平稳 | 用托管 PaaS 或 docker compose + 一台机器 |
| 团队 < 5 人且无专职运维 | 用云厂商的容器托管服务（Cloud Run / ECS Fargate / ACA） |
| 需要多服务、自愈、滚动更新、水平伸缩 | 上 K8s |
| 需要多集群、多租户、复杂网络策略 | K8s + 平台工程投入 |

K8s 的复杂度是**固定成本**，不随业务规模缩小。没有对应收益就是纯负债。

## 二、最小可用 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 3
  selector:
    matchLabels: { app: api }
  template:
    metadata:
      labels: { app: api }
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
      containers:
        - name: api
          image: registry.example.com/api:sha-abc1234   # 永远不用 latest
          ports: [{ containerPort: 3000 }]
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits:   { memory: 512Mi }                 # 注意：不设 cpu limit
          readinessProbe:
            httpGet: { path: /ready, port: 3000 }
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /health, port: 3000 }
            periodSeconds: 15
            failureThreshold: 3
          startupProbe:
            httpGet: { path: /health, port: 3000 }
            failureThreshold: 30
            periodSeconds: 2
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
```

## 三、资源配额：最容易搞错的一块

### requests vs limits

| | 作用 | 设错的后果 |
|---|------|-----------|
| `requests` | 调度依据，保证下限 | 设太低 → 节点超卖，高峰互相踩；设太高 → 资源浪费、调度不上 |
| `limits` | 硬上限 | memory 超限 → **OOMKilled**；cpu 超限 → 被限流（throttle） |

### 三条实践建议

1. **memory 一定要设 limit**。不设的话，一个内存泄漏的 Pod 能拖垮整个节点。
2. **cpu limit 通常不设**（或设得很宽松）。CPU 是可压缩资源，设 limit 会导致
   CFS 限流，在低负载时也会人为增加延迟。设好 `requests` 保证调度即可。
3. **requests 从实测来**。跑一周看 P95 用量，不要拍脑袋。

### QoS 等级

```
Guaranteed  requests == limits（全部资源）  → 最后被驱逐
Burstable   设了 requests，limits 不同或缺失 → 中间
BestEffort  什么都没设                      → 节点压力时第一个被杀
```

生产服务至少要 Burstable，关键服务用 Guaranteed。

## 四、三种探针：职责完全不同

| 探针 | 失败后果 | 用途 |
|------|---------|------|
| `startupProbe` | 阻止另两个探针启动 | 保护慢启动应用不被 liveness 误杀 |
| `readinessProbe` | 从 Service 摘除，**不重启** | 控制流量准入 |
| `livenessProbe` | **重启容器** | 只用于死锁等自愈场景 |

**头号事故模式**：liveness 探针检查了下游依赖（数据库）。
数据库抖动 → 所有 Pod liveness 失败 → 全部重启 → 雪崩。

```
liveness  = "我这个进程还活着吗"     → 只检查自身，越简单越好
readiness = "我现在能处理请求吗"     → 可以检查依赖
```

## 五、发布与回滚

```bash
kubectl set image deploy/api api=registry/api:sha-def5678
kubectl rollout status deploy/api --timeout=5m     # 阻塞等待
kubectl rollout undo deploy/api                    # 回滚上一版
kubectl rollout history deploy/api
```

滚动更新参数：

```yaml
strategy:
  rollingUpdate:
    maxUnavailable: 0      # 不减少可用副本（要求集群有余量）
    maxSurge: 1
```

配合 **PodDisruptionBudget**，防止节点维护时被一次性驱逐：

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
spec:
  minAvailable: 2
  selector: { matchLabels: { app: api } }
```

更高级的金丝雀 / 蓝绿见 `deployment-strategies.md`。

## 六、配置与密钥

| 类型 | 用什么 | 注意 |
|------|--------|------|
| 非敏感配置 | ConfigMap | 挂为 env 时修改**不会**自动生效，需重启；挂为 volume 会自动更新（有延迟） |
| 密钥 | Secret | **base64 不是加密**。必须开 etcd 静态加密，或用外部密钥管理 |
| 生产级密钥 | External Secrets Operator / Vault / 云厂商 KMS | 密钥不进 git，自动轮换 |

**绝不要**把 Secret 的 yaml 提交到仓库。需要 GitOps 时用 sealed-secrets 或 SOPS 加密。

## 七、伸缩

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { apiVersion: apps/v1, kind: Deployment, name: api }
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300    # 防抖，避免频繁缩容
```

- HPA 基于 CPU 是默认选择，但对 IO 密集型服务往往不准 → 用自定义指标（QPS、队列长度）
- HPA 生效的前提是**设了 requests**，没设的话利用率算不出来
- 扩容有延迟（指标采集 + 调度 + 启动），突发流量场景要预留余量或做预热

## 八、排查路径（按顺序走）

```bash
kubectl get pod -l app=api              # 状态和重启次数
kubectl describe pod <pod>              # Events 段是金矿
kubectl logs <pod> --previous           # 崩溃前的日志
kubectl get events --sort-by=.lastTimestamp | tail -30
```

| Pod 状态 | 含义 | 排查方向 |
|---------|------|---------|
| `Pending` | 调度不上 | 资源不足 / 节点选择器 / 污点容忍 / PVC 未绑定 |
| `ImagePullBackOff` | 拉不到镜像 | 镜像名/tag 错、私有仓库没配 imagePullSecrets、网络 |
| `CrashLoopBackOff` | 反复启动失败 | 看 `logs --previous`；配置缺失、依赖不可达、启动即退出 |
| `OOMKilled` | 内存超 limit | 提高 limit 或修内存泄漏；看是否是启动峰值 |
| `Running` 但没流量 | readiness 未通过 | `describe` 看探针失败原因 |
| `Terminating` 卡住 | 优雅退出超时 | 应用没处理 SIGTERM；检查 finalizer |

**Events 是最被低估的排查入口**。80% 的问题在 `kubectl describe` 的 Events 段有直接答案。

## 九、清单管理：不要手写 yaml

| 工具 | 适合 |
|------|------|
| **Kustomize** | 基础 yaml + 环境 overlay，无模板语言，K8s 原生 |
| **Helm** | 需要打包分发、参数化程度高、装第三方组件 |
| GitOps（ArgoCD / Flux） | 声明式部署，集群状态与 git 自动同步，可审计可回滚 |

推荐组合：**自研服务用 Kustomize，第三方组件用 Helm，交付方式用 GitOps**。

避免的做法：把 `kubectl apply` 直接写在 CI 脚本里且没有版本化的清单——
这样集群的真实状态无人知晓，也无法回滚。

---

## 相关子技能与层次边界

本 playbook 负责**要不要上 K8s、上之后怎么生产就绪**（资源配额、三探针、发布回滚、排查路径）的决策；
镜像本身来自容器化，声明式资源落地见子技能。

- 落地到 `skills/docker-deploy/SKILL.md`：镜像与容器基础（多阶段构建、非 root、信号）。
- 落地到 `skills/infra-as-code/SKILL.md`：Terraform 声明式资源（K8s 之外的基础设施，Helm/Kustomize 之外的模块）。
- 兄弟参考：
  - `references/containerization.md`：镜像从哪来、为什么要多阶段。
  - `references/deployment-strategies.md`：K8s 滚动/蓝绿/金丝雀发布与回滚（含扩展-收缩）。
  - `references/observability.md`：探针、监控与告警如何配合 SLO。
  - `references/scripts-usage.md`：`k8s_manifest_check.py` 对 manifest 做体检（镜像 tag/配额/探针/安全上下文/PDB）。
