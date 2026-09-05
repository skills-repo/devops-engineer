# 内置脚本运行手册（scripts-usage）

> 根 `SKILL.md` 只列脚本用途，本文件给**完整运行示例、参数与常见坑**，按需加载。
> 所有脚本：纯标准库、零依赖、不联网、不改动被检查的文件。

## 1. dockerfile_lint.py — Dockerfile 生产就绪度审查

12 类规则：镜像固定、多阶段、非 root、层缓存、密钥泄漏、信号处理等。

```bash
# 严格模式：有 error/warn 即退出码 1，可直接进 CI
python3 scripts/dockerfile_lint.py Dockerfile --strict

# JSON 输出供流水线消费
python3 scripts/dockerfile_lint.py Dockerfile --json
```

**常见坑**：
- 基础镜像用 `latest`/`<tag>` 浮动标签会被判 error；必须 pin 到 digest 或固定小版本。
- `SIGTERM` 未处理会导致 `docker stop` 等 10s 强杀，长事务被截断；需 `tini` 或显式 trap。

## 2. ci_audit.py — GitHub Actions 审计

检查项：action pin、最小权限、脚本注入、密钥暴露、缓存缺失、超时缺失。

```bash
python3 scripts/ci_audit.py .github/workflows --json
python3 scripts/ci_audit.py .github/workflows --strict
```

**常见坑**：
- `uses: actions/checkout@v4` 未 pin 到 commit SHA 会被判风险（供应链投毒面）。
- 在 `run:` 里直接插值 `${{ github.event.pull_request.title }}` 等外部输入易中脚本注入，需走环境或校验。

## 3. k8s_manifest_check.py — K8s manifest 体检

检查项：镜像 tag、资源配额、三探针、安全上下文、明文密钥、PDB 缺失（内置 YAML 子集解析器，无需 PyYAML）。

```bash
python3 scripts/k8s_manifest_check.py k8s/ --strict
python3 scripts/k8s_manifest_check.py k8s/ --json
```

**常见坑**：
- 无 `resources.requests/limits` 会被判 error（邻居噪声 / 被驱逐）。
- 无 `liveness`+`readiness` 双探针：只配一个会导致流量打进未就绪 Pod 或误杀慢启动。
- `Secret` 明文写在 manifest 会被判风险，应走外部 secret 注入。

## 4. slo_budget.py — 错误预算与燃烧率

输出剩余预算、耗尽时间、多窗口告警阈值表。

```bash
python3 scripts/slo_budget.py --slo 99.9 --window 30 \
  --total 12000000 --bad 9800 --elapsed-days 9
```

**常见坑**：
- `--total` 用「请求数」不是「实例数」；用错分母算出的预算毫无意义。
- 燃烧率告警要配多窗口（快/慢）才能既抓突发又抓慢性劣化，单窗口易误报或漏报。

---

## 相关子技能与层次边界

本手册是**四个内置脚本的运行入口**；脚本只做客观体检（零依赖、不联网、不改动被检文件），
判断该往哪条路走仍回到对应 playbook 与子技能。

- `dockerfile_lint.py` → 落地 [`skills/docker-deploy/SKILL.md`](../skills/docker-deploy/SKILL.md)；决策背景 [`references/containerization.md`](containerization.md)。
- `ci_audit.py` → 落地 [`skills/ci-cd-pipeline/SKILL.md`](../skills/ci-cd-pipeline/SKILL.md)；决策背景 [`references/ci-cd-pipeline.md`](ci-cd-pipeline.md)。
- `k8s_manifest_check.py` → 落地 [`skills/docker-deploy/SKILL.md`](../skills/docker-deploy/SKILL.md)（容器基础）；决策背景 [`references/kubernetes.md`](kubernetes.md)。
- `slo_budget.py` → 落地 [`skills/monitor-logging/SKILL.md`](../skills/monitor-logging/SKILL.md)；决策背景 [`references/observability.md`](observability.md)。
