#!/usr/bin/env python3
"""Dockerfile 静态审查——生产就绪度检查。

只用标准库，不依赖 docker/hadolint。检查项对齐 references/containerization.md：
基础镜像固定、多阶段构建、非 root 运行、层缓存友好、包管理器清理、
HEALTHCHECK、信号处理、.dockerignore。

用法:
    python3 scripts/dockerfile_lint.py Dockerfile
    python3 scripts/dockerfile_lint.py path/to/Dockerfile --strict
    python3 scripts/dockerfile_lint.py Dockerfile --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEV_ORDER = {"error": 0, "warn": 1, "info": 2}


def parse_instructions(text: str):
    """把 Dockerfile 解析成 (行号, 指令, 参数) 三元组，处理反斜杠续行与注释。"""
    out = []
    buf, start = "", 0
    for i, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip()
        stripped = line.strip()
        if not buf and (not stripped or stripped.startswith("#")):
            continue
        if not buf:
            start = i
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        buf += stripped
        parts = buf.split(None, 1)
        if parts:
            out.append((start, parts[0].upper(), parts[1] if len(parts) > 1 else ""))
        buf = ""
    if buf.strip():
        parts = buf.split(None, 1)
        out.append((start, parts[0].upper(), parts[1] if len(parts) > 1 else ""))
    return out


def lint(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    ins = parse_instructions(text)
    findings = []

    def add(sev, line, code, msg, fix):
        findings.append({"severity": sev, "line": line, "code": code,
                         "message": msg, "fix": fix})

    froms = [(ln, arg) for ln, op, arg in ins if op == "FROM"]
    if not froms:
        add("error", 0, "DF001", "没有找到 FROM 指令，这不是有效的 Dockerfile", "补上基础镜像")
        return findings

    # 1. 基础镜像必须固定版本，禁止 latest / 裸镜像名
    for ln, arg in froms:
        image = arg.split(" AS ")[0].split(" as ")[0].strip()
        if image.startswith("$"):
            continue
        if "@sha256:" in image:
            continue
        if ":" not in image.split("/")[-1]:
            add("error", ln, "DF002", f"基础镜像 `{image}` 未指定 tag，隐式使用 latest",
                "固定到具体版本，如 node:22.14-alpine；生产建议 pin digest")
        elif image.rsplit(":", 1)[-1] in ("latest", "stable", "main"):
            add("error", ln, "DF003", f"基础镜像 `{image}` 使用浮动 tag，构建不可复现",
                "改成语义化版本 tag，或 pin 到 @sha256 digest")

    # 2. 多阶段构建
    has_stage_alias = any(" as " in a.lower() for _, a in froms)
    if len(froms) == 1 and not has_stage_alias:
        add("warn", froms[0][0], "DF010", "单阶段构建：编译产物与构建工具链会一起进入运行镜像",
            "拆成 builder / runtime 两阶段，运行阶段只 COPY --from=builder 必需产物")

    # 3. 非 root 运行
    users = [(ln, arg.strip()) for ln, op, arg in ins if op == "USER"]
    effective_user = users[-1][1] if users else None
    if not effective_user:
        add("error", 0, "DF020", "全程以 root 运行容器，容器逃逸后果被放大",
            "创建低权限用户并在运行阶段 `USER app`（K8s 侧再配 runAsNonRoot: true）")
    elif effective_user.split(":")[0] in ("root", "0"):
        add("error", users[-1][0], "DF021", "最后一条 USER 指令仍是 root",
            "把 root 操作前置，运行阶段切回非特权用户")

    # 4. 层缓存友好：依赖清单应先于全量 COPY
    copy_lines = [(ln, arg) for ln, op, arg in ins if op in ("COPY", "ADD")]
    manifest_re = re.compile(
        r"(package\.json|package-lock\.json|pnpm-lock|yarn\.lock|requirements[\w.-]*\.txt|"
        r"poetry\.lock|pyproject\.toml|go\.mod|go\.sum|Gemfile|Cargo\.toml)")
    first_bulk = next((ln for ln, arg in copy_lines
                       if re.match(r"^(--\S+\s+)*\.\s", arg) or arg.strip().startswith(". ")), None)
    first_manifest = next((ln for ln, arg in copy_lines if manifest_re.search(arg)), None)
    if first_bulk and (first_manifest is None or first_manifest > first_bulk):
        add("warn", first_bulk, "DF030", "先 COPY 全部源码再装依赖，任何代码改动都会击穿依赖层缓存",
            "先 COPY 依赖清单 → RUN install → 再 COPY 源码")

    # 5. ADD 用于本地文件
    for ln, arg in copy_lines:
        if arg and not arg.startswith("--from"):
            pass
    for ln, op, arg in ins:
        if op == "ADD" and not re.search(r"https?://|\.tar", arg):
            add("warn", ln, "DF031", "用 ADD 拷贝本地文件（ADD 会自动解压、可拉远程 URL，语义不明确）",
                "本地文件一律用 COPY，只有需要自动解压 tar 时才用 ADD")

    # 6. 包管理器缓存清理
    runs = [(ln, arg) for ln, op, arg in ins if op == "RUN"]
    for ln, arg in runs:
        low = arg.lower()
        if "apt-get install" in low and "rm -rf /var/lib/apt/lists" not in low:
            add("warn", ln, "DF040", "apt-get install 后未清理 /var/lib/apt/lists，镜像白胖几十 MB",
                "同一 RUN 层内追加 `&& rm -rf /var/lib/apt/lists/*`")
        if "apt-get install" in low and "--no-install-recommends" not in low:
            add("info", ln, "DF041", "apt-get install 未加 --no-install-recommends，会装入大量非必需包",
                "加上 --no-install-recommends")
        if re.search(r"\bapk add\b", low) and "--no-cache" not in low:
            add("warn", ln, "DF042", "apk add 未加 --no-cache", "改成 `apk add --no-cache`")
        if "pip install" in low and "--no-cache-dir" not in low:
            add("info", ln, "DF043", "pip install 未加 --no-cache-dir", "加上 --no-cache-dir")
        if "apt-get upgrade" in low or "apt-get dist-upgrade" in low:
            add("warn", ln, "DF044", "在 Dockerfile 里跑 apt-get upgrade，构建结果随时间漂移",
                "改为升级基础镜像版本，而不是在构建期升级系统包")

    # 7. 密钥泄漏
    secret_re = re.compile(
        r"(?i)\b(ARG|ENV)\s+\w*(PASSWORD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL)\w*\s*=?")
    for ln, op, arg in ins:
        if op in ("ARG", "ENV") and secret_re.search(f"{op} {arg}"):
            add("error", ln, "DF050", f"{op} 中出现疑似密钥变量，会固化进镜像层历史（docker history 可读）",
                "构建期密钥用 BuildKit `RUN --mount=type=secret`，运行期密钥由编排层注入")
        if op == "RUN" and re.search(r"(?i)(curl|wget)[^\n]*(token|api[_-]?key)=", arg):
            add("error", ln, "DF051", "RUN 命令行内联密钥，会写入镜像层",
                "改用 --mount=type=secret 或在运行期获取")

    # 8. HEALTHCHECK
    if not any(op == "HEALTHCHECK" for _, op, _ in ins):
        add("info", 0, "DF060", "未定义 HEALTHCHECK（纯 K8s 环境可忽略，探针在 manifest 里配）",
            "docker/compose 场景补 HEALTHCHECK；K8s 场景改配 liveness/readiness 探针")

    # 9. 信号处理：shell 形式 CMD/ENTRYPOINT 会让 PID1 变成 sh，收不到 SIGTERM
    for ln, op, arg in ins:
        if op in ("CMD", "ENTRYPOINT") and arg and not arg.strip().startswith("["):
            add("warn", ln, f"DF07{0 if op == 'CMD' else 1}",
                f"{op} 用 shell 形式，PID 1 会是 /bin/sh，进程收不到 SIGTERM，优雅退出失效",
                f'改成 exec 形式：{op} ["executable", "arg"]')

    # 10. WORKDIR 优于 RUN cd
    for ln, arg in runs:
        if re.match(r"^\s*cd\s+\S+\s*(&&|$)", arg):
            add("info", ln, "DF080", "用 `RUN cd` 切目录，只在该层生效，容易踩坑", "改用 WORKDIR")

    # 11. .dockerignore
    ignore = path.parent / ".dockerignore"
    if not ignore.exists():
        add("warn", 0, "DF090", "同目录缺少 .dockerignore，构建上下文会把 .git/node_modules 全部上传",
            "新建 .dockerignore，至少排除 .git、node_modules、dist、*.env")

    # 12. EXPOSE 提示
    if not any(op == "EXPOSE" for _, op, _ in ins):
        add("info", 0, "DF100", "未声明 EXPOSE（不影响运行，但丢失了端口的自描述信息）",
            "补一条 EXPOSE <port> 作为文档")

    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["line"]))
    return findings


def main():
    ap = argparse.ArgumentParser(description="Dockerfile 生产就绪度静态审查")
    ap.add_argument("dockerfile", nargs="?", default="Dockerfile", help="Dockerfile 路径")
    ap.add_argument("--strict", action="store_true", help="存在 error 或 warn 时退出码为 1")
    ap.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    args = ap.parse_args()

    path = Path(args.dockerfile)
    if not path.is_file():
        print(f"找不到文件: {path}", file=sys.stderr)
        return 2

    findings = lint(path)
    counts = {s: sum(1 for f in findings if f["severity"] == s) for s in ("error", "warn", "info")}

    if args.as_json:
        print(json.dumps({"file": str(path), "counts": counts, "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        icon = {"error": "[ERROR]", "warn": "[WARN ]", "info": "[INFO ]"}
        print(f"\nDockerfile 审查: {path}")
        print("=" * 72)
        if not findings:
            print("未发现问题，生产就绪度检查全部通过。")
        for f in findings:
            loc = f"L{f['line']}" if f["line"] else "全局"
            print(f"{icon[f['severity']]} {f['code']} ({loc}) {f['message']}")
            print(f"         → {f['fix']}")
        print("-" * 72)
        print(f"error {counts['error']} / warn {counts['warn']} / info {counts['info']}")

    if args.strict and (counts["error"] or counts["warn"]):
        return 1
    if counts["error"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
