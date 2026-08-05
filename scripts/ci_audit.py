#!/usr/bin/env python3
"""GitHub Actions 工作流审计——安全、可复现、提速三维体检。

零依赖（不需要 PyYAML），基于缩进感知的行扫描做启发式检查，检查项对齐
references/ci-cd-pipeline.md。适合放进 CI 自身做元检查。

用法:
    python3 scripts/ci_audit.py .github/workflows
    python3 scripts/ci_audit.py .github/workflows/ci.yml --strict
    python3 scripts/ci_audit.py .github/workflows --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SEV_ORDER = {"error": 0, "warn": 1, "info": 2}

# 官方维护、可信度较高的 action 命名空间（未 pin digest 时降级为 info）
TRUSTED_NS = ("actions/", "github/", "docker/", "azure/", "aws-actions/", "google-github-actions/")

# 常见的可被注入的不可信上下文表达式
UNTRUSTED_CTX = re.compile(
    r"github\.event\.(issue|pull_request|comment|review|discussion|head_commit)\."
    r"(title|body|message)|github\.head_ref|github\.event\.pull_request\.head\.(ref|label)")


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def audit_file(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    findings = []

    def add(sev, line, code, msg, fix):
        findings.append({"file": str(path), "severity": sev, "line": line,
                         "code": code, "message": msg, "fix": fix})

    text = "\n".join(lines)
    body_no_comment = "\n".join(re.sub(r"#.*$", "", ln) for ln in lines)

    # ---- 工作流级检查 -------------------------------------------------
    top_keys = {}
    for i, ln in enumerate(lines, 1):
        if ln and indent_of(ln) == 0 and re.match(r"^[A-Za-z_][\w-]*\s*:", ln):
            top_keys[ln.split(":")[0].strip()] = i

    if "permissions" not in top_keys:
        add("warn", 1, "CI001",
            "工作流未声明顶层 permissions，GITHUB_TOKEN 会拿到仓库默认（常为写）权限",
            "顶层加 `permissions: {contents: read}`，需要写权限的 job 单独提权")

    if "concurrency" not in top_keys:
        add("info", 1, "CI002", "未配置 concurrency，同分支连续推送会并行跑重复流水线，浪费额度",
            "加 `concurrency: {group: ${{ github.workflow }}-${{ github.ref }}, "
            "cancel-in-progress: true}`")

    if re.search(r"^\s*pull_request_target\s*:", body_no_comment, re.M):
        add("error", top_keys.get("on", 1), "CI003",
            "使用 pull_request_target：在有仓库密钥的上下文中运行，若同时 checkout PR 代码即等于把密钥交给外部贡献者",
            "确认是否必须；必须时禁止 checkout PR 分支代码，或拆成 workflow_run 两段式")

    # ---- 逐 job / step 检查 -------------------------------------------
    jobs_line = top_keys.get("jobs")
    current_job, job_indent, job_start = None, None, None
    job_has_timeout, job_has_perm = False, False
    seen_jobs = []

    def close_job():
        if current_job and not job_has_timeout:
            add("warn", job_start, "CI010",
                f"job `{current_job}` 未设置 timeout-minutes，卡死的 runner 会跑满 6 小时上限",
                "加 `timeout-minutes: 15`（按实际耗时留 2-3 倍余量）")

    if jobs_line:
        for i, raw in enumerate(lines, 1):
            if i <= jobs_line:
                continue
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            ind = indent_of(raw)
            if ind == 0:
                close_job()
                current_job = None
                break
            if job_indent is None and re.match(r"^\s*[\w-]+\s*:\s*$", raw):
                job_indent = ind
            if ind == job_indent and re.match(r"^\s*[\w-]+\s*:\s*$", raw):
                close_job()
                current_job = raw.strip().rstrip(":")
                seen_jobs.append(current_job)
                job_start, job_has_timeout, job_has_perm = i, False, False
                continue
            if current_job:
                key = raw.strip()
                if key.startswith("timeout-minutes:"):
                    job_has_timeout = True
                if key.startswith("permissions:"):
                    job_has_perm = True
                if re.match(r"^runs-on:\s*.*(ubuntu|windows|macos)-latest", key):
                    add("info", i, "CI011",
                        f"job `{current_job}` 使用 *-latest runner 镜像，镜像升级可能悄悄改变构建环境",
                        "对可复现要求高的构建 pin 到具体版本，如 ubuntu-24.04")
        close_job()

    # ---- uses: 版本固定 ------------------------------------------------
    for i, raw in enumerate(lines, 1):
        m = re.match(r"^\s*-?\s*uses\s*:\s*['\"]?([^'\"#\s]+)", raw)
        if not m:
            continue
        ref = m.group(1)
        if ref.startswith((".", "/")) or ref.startswith("docker://"):
            continue
        if "@" not in ref:
            add("error", i, "CI020", f"`{ref}` 未指定版本引用", "至少 pin 到 tag，第三方 action 建议 pin 到完整 commit SHA")
            continue
        repo, at = ref.rsplit("@", 1)
        if re.fullmatch(r"[0-9a-f]{40}", at):
            continue
        trusted = repo.lower().startswith(TRUSTED_NS)
        if at in ("main", "master", "develop", "HEAD"):
            add("error", i, "CI021", f"`{ref}` 引用可变分支，上游任意提交都会立刻在你的 CI 里执行",
                "pin 到 commit SHA（第三方）或 major tag（官方）")
        elif not trusted:
            add("warn", i, "CI022", f"第三方 action `{ref}` 只 pin 到 tag，tag 可被上游重新指向",
                f"pin 到完整 commit SHA：`{repo}@<40位sha>  # {at}`")

    # ---- 脚本注入 ------------------------------------------------------
    in_run, run_ind = False, 0
    for i, raw in enumerate(lines, 1):
        if re.match(r"^\s*-?\s*run\s*:\s*[|>][-+]?\s*$", raw):
            in_run, run_ind = True, indent_of(raw)
            continue
        if in_run and raw.strip() and indent_of(raw) <= run_ind:
            in_run = False
        target = raw if (in_run or re.match(r"^\s*-?\s*run\s*:", raw)) else None
        if target and UNTRUSTED_CTX.search(target):
            add("error", i, "CI030",
                "run: 脚本中直接内插不可信上下文（PR 标题/正文/分支名），可被构造成命令注入",
                "先经 env 传值：`env: {TITLE: ${{ github.event.pull_request.title }}}`，脚本里用 \"$TITLE\"")

    # ---- 密钥使用 ------------------------------------------------------
    for i, raw in enumerate(lines, 1):
        if re.search(r"\$\{\{\s*secrets\.\*", raw) or re.search(r"toJSON\(secrets\)", raw):
            add("error", i, "CI040", "把整个 secrets 上下文传给某一步，等于给它所有密钥",
                "只传该步骤真正需要的单个 secret")
    if re.search(r"(?i)(api[_-]?key|password|token)\s*:\s*['\"]?[A-Za-z0-9_\-]{16,}", body_no_comment):
        add("error", 1, "CI041", "工作流文件中疑似出现明文密钥",
            "移入 GitHub Secrets / OIDC，并立即轮换已泄漏的凭据")
    if re.search(r"aws-access-key-id|AWS_SECRET_ACCESS_KEY", text) and "id-token" not in text:
        add("info", 1, "CI042", "使用长期云凭据而非 OIDC 短期凭据",
            "改用 OIDC：`permissions: {id-token: write}` + configure-aws-credentials 的 role-to-assume")

    # ---- 提速 ----------------------------------------------------------
    installs = re.search(r"(npm ci|npm install|pnpm install|yarn install|pip install|"
                         r"bundle install|go mod download|mvn|gradle)", text)
    has_cache = ("actions/cache" in text or re.search(r"^\s*cache\s*:", body_no_comment, re.M)
                 or "cache-dependency-path" in text)
    if installs and not has_cache:
        add("warn", 1, "CI050", "存在依赖安装步骤但没有任何缓存配置，每次 CI 都从零下载",
            "用 setup-* action 的 `cache:` 参数，或 actions/cache 缓存依赖目录")
    if "actions/checkout" in text and not re.search(r"fetch-depth", text):
        add("info", 1, "CI051", "checkout 未设置 fetch-depth，默认浅克隆足够时可省，但大仓需确认",
            "只需当前提交时显式 `fetch-depth: 1`；需要 tag/history 时才放开")

    # ---- 质量门禁 ------------------------------------------------------
    if not re.search(r"(?i)(lint|eslint|ruff|flake8|golangci)", text):
        add("info", 1, "CI060", "流水线中未见 lint 步骤", "补一层秒级静态检查作为最外层门禁")
    if not re.search(r"(?i)(test|pytest|jest|vitest|go test)", text):
        add("info", 1, "CI061", "流水线中未见测试步骤", "至少接入单元测试并设置覆盖率阈值")
    if re.search(r"continue-on-error\s*:\s*true", text):
        add("warn", 1, "CI062", "存在 continue-on-error: true，门禁形同虚设（红了也算过）",
            "确认是否有意为之；临时豁免请加注释与到期日")

    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["line"]))
    return findings


def collect(target: Path):
    if target.is_file():
        return [target]
    return sorted([p for p in target.rglob("*") if p.suffix in (".yml", ".yaml")])


def main():
    ap = argparse.ArgumentParser(description="GitHub Actions 工作流安全与效率审计")
    ap.add_argument("target", nargs="?", default=".github/workflows",
                    help="工作流文件或目录（默认 .github/workflows）")
    ap.add_argument("--strict", action="store_true", help="存在 error 或 warn 时退出码为 1")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    target = Path(args.target)
    if not target.exists():
        print(f"找不到路径: {target}", file=sys.stderr)
        return 2

    files = collect(target)
    if not files:
        print(f"{target} 下没有 yml/yaml 工作流文件", file=sys.stderr)
        return 2

    all_findings = []
    for f in files:
        all_findings.extend(audit_file(f))
    counts = {s: sum(1 for f in all_findings if f["severity"] == s)
              for s in ("error", "warn", "info")}

    if args.as_json:
        print(json.dumps({"files": [str(f) for f in files], "counts": counts,
                          "findings": all_findings}, ensure_ascii=False, indent=2))
    else:
        icon = {"error": "[ERROR]", "warn": "[WARN ]", "info": "[INFO ]"}
        print(f"\nGitHub Actions 审计：{len(files)} 个工作流文件")
        print("=" * 76)
        by_file = {}
        for f in all_findings:
            by_file.setdefault(f["file"], []).append(f)
        for fp in [str(f) for f in files]:
            items = by_file.get(fp, [])
            print(f"\n▸ {fp}  ({len(items)} 项)")
            if not items:
                print("  通过")
            for it in items:
                print(f"  {icon[it['severity']]} {it['code']} (L{it['line']}) {it['message']}")
                print(f"           → {it['fix']}")
        print("\n" + "-" * 76)
        print(f"error {counts['error']} / warn {counts['warn']} / info {counts['info']}")

    if args.strict and (counts["error"] or counts["warn"]):
        return 1
    if counts["error"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
