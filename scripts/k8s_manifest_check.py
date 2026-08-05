#!/usr/bin/env python3
"""Kubernetes manifest 生产就绪度检查。

零依赖：内置一个 YAML 子集解析器（够解析常规 manifest），不需要安装 PyYAML，
也不需要连接集群。检查项对齐 references/kubernetes.md 与 deployment-strategies.md。

用法:
    python3 scripts/k8s_manifest_check.py k8s/
    python3 scripts/k8s_manifest_check.py k8s/deployment.yaml --strict
    python3 scripts/k8s_manifest_check.py k8s/ --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEV_ORDER = {"error": 0, "warn": 1, "info": 2}
WORKLOADS = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob", "ReplicaSet", "Pod"}


# ---------------------------------------------------------------- YAML 子集解析
def _tokens(text: str):
    out = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = re.sub(r"\s+#\s.*$", "", raw.rstrip())
        out.append((len(stripped) - len(stripped.lstrip(" ")), stripped.strip()))
    return out


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v in ("true", "True", "yes"):
        return True
    if v in ("false", "False", "no"):
        return False
    if v in ("null", "~", ""):
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"-?\d+\.\d+", v):
        return float(v)
    return v


def _parse(tok, i, indent):
    """返回 (node, next_index)。node 为 dict / list / scalar。"""
    if i >= len(tok):
        return None, i
    if tok[i][1].startswith("- ") or tok[i][1] == "-":
        items = []
        while i < len(tok) and tok[i][0] == indent and (tok[i][1].startswith("- ") or tok[i][1] == "-"):
            ind, content = tok[i]
            rest = content[1:].lstrip()
            off = ind + (len(content) - len(rest))
            if not rest:
                i += 1
                if i < len(tok) and tok[i][0] > ind:
                    node, i = _parse(tok, i, tok[i][0])
                    items.append(node)
                else:
                    items.append(None)
                continue
            if re.match(r"^[\w.\-/\"']+\s*:", rest):
                sub = [(off, rest)] + [t for t in tok[i + 1:]]
                node, consumed = _parse(sub, 0, off)
                items.append(node)
                i += consumed
            else:
                items.append(_scalar(rest))
                i += 1
        return items, i

    node = {}
    while i < len(tok) and tok[i][0] == indent:
        ind, content = tok[i]
        if content.startswith("- "):
            break
        m = re.match(r"^([\w.\-/]+|\"[^\"]+\"|'[^']+')\s*:\s*(.*)$", content)
        if not m:
            i += 1
            continue
        key = m.group(1).strip("\"'")
        val = m.group(2).strip()
        if val in ("|", ">", "|-", ">-", "|+", ">+"):
            i += 1
            buf = []
            while i < len(tok) and tok[i][0] > ind:
                buf.append(tok[i][1])
                i += 1
            node[key] = "\n".join(buf)
        elif val:
            node[key] = _scalar(val)
            i += 1
        else:
            i += 1
            if i < len(tok) and tok[i][0] > ind:
                child, i = _parse(tok, i, tok[i][0])
                node[key] = child
            elif i < len(tok) and tok[i][0] == ind and (tok[i][1].startswith("- ") or tok[i][1] == "-"):
                child, i = _parse(tok, i, ind)
                node[key] = child
            else:
                node[key] = None
    return node, i


def load_docs(text: str):
    docs = []
    for chunk in re.split(r"^---\s*$", text, flags=re.M):
        tok = _tokens(chunk)
        if not tok:
            continue
        base = min(t[0] for t in tok)
        node, _ = _parse(tok, 0, base)
        if isinstance(node, dict) and node:
            docs.append(node)
    return docs


def dig(node, *keys, default=None):
    cur = node
    for k in keys:
        if not isinstance(cur, dict) or k not in cur or cur[k] is None:
            return default
        cur = cur[k]
    return cur


# ---------------------------------------------------------------- 检查规则
def check_doc(doc, path, findings, index):
    kind = doc.get("kind")
    name = dig(doc, "metadata", "name", default="<unnamed>")
    where = f"{path}[{index}] {kind}/{name}"

    def add(sev, code, msg, fix):
        findings.append({"target": where, "kind": kind, "severity": sev,
                         "code": code, "message": msg, "fix": fix})

    if kind not in WORKLOADS:
        return

    pod = doc if kind == "Pod" else dig(doc, "spec", "template", "spec", default={})
    if kind == "CronJob":
        pod = dig(doc, "spec", "jobTemplate", "spec", "template", "spec", default={})
    if kind == "Pod":
        pod = doc.get("spec", {}) or {}
    if not isinstance(pod, dict):
        return

    containers = pod.get("containers") or []
    if not isinstance(containers, list):
        containers = []

    # 命名空间
    if not dig(doc, "metadata", "namespace"):
        add("info", "K8S001", "未指定 namespace，会落到 default（或 kubectl 当前上下文）",
            "显式声明 namespace，或由 kustomize/helm 统一注入")

    # 副本数与可用性
    if kind == "Deployment":
        replicas = dig(doc, "spec", "replicas")
        if replicas is None:
            add("info", "K8S010", "未声明 replicas，默认 1 副本，滚动更新期间可能出现空窗",
                "生产至少 2 副本，并配 PodDisruptionBudget")
        elif isinstance(replicas, int) and replicas < 2:
            add("warn", "K8S011", f"replicas={replicas}，节点驱逐或滚动更新时服务会中断",
                "生产至少 2 副本；同时配 PDB minAvailable: 1")
        strategy = dig(doc, "spec", "strategy", "type", default="RollingUpdate")
        if strategy == "Recreate":
            add("warn", "K8S012", "更新策略为 Recreate，先全停再全起，必然产生停机",
                "无状态服务改用 RollingUpdate；确需 Recreate 请在注释中说明原因")

    for c in containers:
        if not isinstance(c, dict):
            continue
        cname = c.get("name", "<container>")
        image = str(c.get("image", ""))

        # 镜像固定
        if image:
            tag = image.rsplit(":", 1)[-1] if ":" in image.split("/")[-1] else ""
            if "@sha256:" in image:
                pass
            elif not tag:
                add("error", "K8S020", f"容器 {cname} 镜像 `{image}` 未指定 tag，隐式 latest，回滚无从谈起",
                    "固定到不可变 tag（如 git sha）或 digest")
            elif tag in ("latest", "main", "master", "stable"):
                add("error", "K8S021", f"容器 {cname} 镜像使用浮动 tag `{tag}`，同一 manifest 不同时间拉到不同代码",
                    "用不可变 tag：<service>:<git-sha>")

        # 资源配额
        req = dig(c, "resources", "requests")
        lim = dig(c, "resources", "limits")
        if not req:
            add("error", "K8S030", f"容器 {cname} 未声明 resources.requests，调度器无法合理放置，节点压力下最先被驱逐",
                "至少声明 cpu / memory requests（按实测 P95 设定）")
        if not lim:
            add("warn", "K8S031", f"容器 {cname} 未声明 resources.limits，单个 Pod 可以吃光节点资源",
                "至少设 memory limit（建议 = requests 的 1.5-2 倍）；CPU limit 慎设，易触发限流")
        elif isinstance(lim, dict) and isinstance(req, dict):
            if lim.get("memory") and req.get("memory") and lim["memory"] != req["memory"]:
                pass
            if lim.get("cpu") and req.get("cpu") and str(lim["cpu"]) == str(req.get("cpu")):
                add("info", "K8S032", f"容器 {cname} CPU limits == requests（Guaranteed QoS）",
                    "延迟敏感服务可以这么做；吞吐型服务通常不设 CPU limit 更划算")

        # 探针
        if kind in ("Deployment", "StatefulSet", "DaemonSet", "Pod"):
            if not c.get("readinessProbe"):
                add("error", "K8S040", f"容器 {cname} 缺 readinessProbe，Pod 一启动就会被打流量（此时可能还没连上数据库）",
                    "加 readinessProbe，检查依赖是否就绪")
            if not c.get("livenessProbe"):
                add("warn", "K8S041", f"容器 {cname} 缺 livenessProbe，进程假死时不会被自动重启",
                    "加 livenessProbe，但探测逻辑要轻、不要级联检查下游")
            elif c.get("livenessProbe") == c.get("readinessProbe"):
                add("warn", "K8S042", f"容器 {cname} liveness 与 readiness 探针完全相同",
                    "liveness 只探自身存活；readiness 才探依赖。相同会导致依赖抖动时 Pod 被批量重启")
            if not c.get("startupProbe") and c.get("livenessProbe"):
                add("info", "K8S043", f"容器 {cname} 无 startupProbe，慢启动应用可能在启动期被 liveness 杀掉",
                    "启动慢（>30s）的应用补 startupProbe")

        # 安全上下文
        sc = c.get("securityContext") or {}
        psc = pod.get("securityContext") or {}
        if sc.get("privileged") is True:
            add("error", "K8S050", f"容器 {cname} 以 privileged 运行，等同宿主机 root",
                "去掉 privileged，改用最小 capabilities")
        if not (sc.get("runAsNonRoot") or psc.get("runAsNonRoot")):
            add("warn", "K8S051", f"容器 {cname} 未强制 runAsNonRoot",
                "设 securityContext.runAsNonRoot: true，镜像内也要有非 root 用户")
        if sc.get("allowPrivilegeEscalation") is not False:
            add("info", "K8S052", f"容器 {cname} 未禁止提权", "设 allowPrivilegeEscalation: false")
        if sc.get("readOnlyRootFilesystem") is not True:
            add("info", "K8S053", f"容器 {cname} 根文件系统可写",
                "设 readOnlyRootFilesystem: true，可写目录用 emptyDir 挂载")

        # 明文密钥
        env = c.get("env") or []
        if isinstance(env, list):
            for e in env:
                if not isinstance(e, dict):
                    continue
                ename = str(e.get("name", ""))
                if re.search(r"(?i)(password|secret|token|api[_-]?key|credential)", ename) and "value" in e:
                    add("error", "K8S060", f"容器 {cname} 的 env `{ename}` 直接写明文值",
                        "改用 valueFrom.secretKeyRef，或外部 secret 管理（External Secrets / SOPS）")

    # Pod 级风险
    if pod.get("hostNetwork") is True:
        add("warn", "K8S070", "使用 hostNetwork，Pod 直接占用宿主机网络栈，隔离性下降",
            "确认必要性；一般服务用 Service 暴露即可")
    volumes = pod.get("volumes") or []
    if isinstance(volumes, list):
        for v in volumes:
            if isinstance(v, dict) and v.get("hostPath"):
                add("warn", "K8S071", f"挂载 hostPath（{v.get('name')}），把宿主机目录暴露给容器",
                    "改用 PVC / emptyDir / ConfigMap；确需 hostPath 时限制为只读")
    if kind in ("Deployment", "StatefulSet") and not pod.get("terminationGracePeriodSeconds"):
        add("info", "K8S072", "未设置 terminationGracePeriodSeconds（默认 30s）",
            "长连接/长任务服务按实际收尾时间调大，并确保应用处理 SIGTERM")


def check_bundle(docs_by_file, findings):
    """跨文档检查：多副本工作负载是否配了 PDB。"""
    pdb_targets = []
    multi_replica = []
    for path, docs in docs_by_file.items():
        for idx, d in enumerate(docs):
            if d.get("kind") == "PodDisruptionBudget":
                pdb_targets.append(dig(d, "spec", "selector", "matchLabels", default={}))
            if d.get("kind") in ("Deployment", "StatefulSet"):
                r = dig(d, "spec", "replicas")
                if isinstance(r, int) and r >= 2:
                    multi_replica.append((path, idx, dig(d, "metadata", "name", default="?")))
    if multi_replica and not pdb_targets:
        for path, idx, name in multi_replica:
            findings.append({
                "target": f"{path}[{idx}] {name}", "kind": "Deployment", "severity": "warn",
                "code": "K8S080",
                "message": f"{name} 有多副本但整个 manifest 集合中没有 PodDisruptionBudget，节点排空时可能被一次性全部驱逐",
                "fix": "补一个 PDB：minAvailable: 1（或 maxUnavailable: 1）"})


def main():
    ap = argparse.ArgumentParser(description="Kubernetes manifest 生产就绪度检查")
    ap.add_argument("target", nargs="?", default="k8s", help="manifest 文件或目录")
    ap.add_argument("--strict", action="store_true", help="存在 error 或 warn 时退出码为 1")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"找不到路径: {target}", file=sys.stderr)
        return 2

    files = [target] if target.is_file() else sorted(
        p for p in target.rglob("*") if p.suffix in (".yml", ".yaml"))
    if not files:
        print(f"{target} 下没有 yml/yaml 文件", file=sys.stderr)
        return 2

    findings, docs_by_file = [], {}
    for f in files:
        try:
            docs = load_docs(f.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # 解析失败不阻断整体检查
            findings.append({"target": str(f), "kind": "-", "severity": "warn",
                             "code": "K8S000", "message": f"解析失败：{exc}",
                             "fix": "确认是标准 YAML；模板语法（helm {{ }}）需先 render 再检查"})
            continue
        docs_by_file[str(f)] = docs
        for idx, d in enumerate(docs):
            check_doc(d, str(f), findings, idx)
    check_bundle(docs_by_file, findings)

    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ("error", "warn", "info")}
    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["target"]))

    if args.as_json:
        print(json.dumps({"files": [str(f) for f in files], "counts": counts,
                          "findings": findings}, ensure_ascii=False, indent=2))
    else:
        icon = {"error": "[ERROR]", "warn": "[WARN ]", "info": "[INFO ]"}
        total_docs = sum(len(v) for v in docs_by_file.values())
        print(f"\nK8s manifest 检查：{len(files)} 个文件 / {total_docs} 个对象")
        print("=" * 78)
        if not findings:
            print("全部通过。")
        cur = None
        for f in findings:
            if f["target"] != cur:
                cur = f["target"]
                print(f"\n▸ {cur}")
            print(f"  {icon[f['severity']]} {f['code']} {f['message']}")
            print(f"           → {f['fix']}")
        print("\n" + "-" * 78)
        print(f"error {counts['error']} / warn {counts['warn']} / info {counts['info']}")

    if args.strict and (counts["error"] or counts["warn"]):
        return 1
    if counts["error"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
