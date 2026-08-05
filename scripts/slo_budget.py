#!/usr/bin/env python3
"""SLO 错误预算与燃烧率计算器。

把"可用性目标"翻译成可执行的数字：本周期还能坏多少请求 / 停多少分钟、
当前烧得多快、按这个速度什么时候烧完、多窗口告警阈值应该设在哪。
对齐 references/observability.md 与 incident-response.md。

用法:
    # 用请求数算
    python3 scripts/slo_budget.py --slo 99.9 --window 30 --total 12000000 --bad 9800

    # 用错误率算（%）
    python3 scripts/slo_budget.py --slo 99.95 --window 28 --error-rate 0.07

    # 指定周期已过去的时间，得到消耗速度与预计耗尽时间
    python3 scripts/slo_budget.py --slo 99.9 --total 5e6 --bad 4200 --elapsed-days 9

    # 只看多窗口告警阈值表
    python3 scripts/slo_budget.py --slo 99.9 --alerts-only
"""
from __future__ import annotations

import argparse
import json
import sys

# Google SRE 多窗口多燃烧率告警的标准配置
# (长窗口, 短窗口, 燃烧率, 触发时消耗的预算比例, 处置方式)
ALERT_POLICY = [
    ("1h", "5m", 14.4, 0.02, "Page（呼叫值班）"),
    ("6h", "30m", 6.0, 0.05, "Page（呼叫值班）"),
    ("24h", "2h", 3.0, 0.10, "Ticket（工单跟进）"),
    ("72h", "6h", 1.0, 0.10, "Ticket（工单跟进）"),
]


def fmt_duration(minutes: float) -> str:
    if minutes < 1:
        return f"{minutes * 60:.0f} 秒"
    if minutes < 60:
        return f"{minutes:.1f} 分钟"
    if minutes < 1440:
        return f"{minutes / 60:.2f} 小时"
    return f"{minutes / 1440:.2f} 天"


def fmt_num(n: float) -> str:
    return f"{n:,.0f}" if abs(n) >= 1 else f"{n:.4g}"


def compute(slo: float, window_days: float, total=None, bad=None,
            error_rate=None, elapsed_days=None):
    if not 0 < slo < 100:
        raise ValueError("--slo 必须在 (0, 100) 区间，例如 99.9")
    budget_ratio = (100.0 - slo) / 100.0          # 允许的不可用比例
    window_min = window_days * 24 * 60
    allowed_min = window_min * budget_ratio        # 折算成允许的停机分钟

    res = {
        "slo_percent": slo,
        "window_days": window_days,
        "budget_ratio": budget_ratio,
        "allowed_downtime_minutes": allowed_min,
        "allowed_downtime_human": fmt_duration(allowed_min),
    }

    if total is not None:
        allowed_bad = total * budget_ratio
        res["total_requests"] = total
        res["allowed_bad_requests"] = allowed_bad
        if bad is not None:
            res["bad_requests"] = bad
            res["observed_error_rate"] = bad / total if total else 0.0
            consumed = bad / allowed_bad if allowed_bad else float("inf")
            res["budget_consumed_ratio"] = consumed
            res["budget_remaining_ratio"] = 1 - consumed
            res["remaining_bad_requests"] = allowed_bad - bad
            res["burn_rate"] = (bad / total) / budget_ratio if budget_ratio else float("inf")
    if error_rate is not None:
        rate = error_rate / 100.0
        res["observed_error_rate"] = rate
        res["burn_rate"] = rate / budget_ratio if budget_ratio else float("inf")
        res["budget_consumed_ratio"] = res.get("budget_consumed_ratio", res["burn_rate"] *
                                               ((elapsed_days or window_days) / window_days))
        res["budget_remaining_ratio"] = 1 - res["budget_consumed_ratio"]

    br = res.get("burn_rate")
    if br is not None and elapsed_days:
        # 按周期内实际观测的时间比例，换算真实消耗
        consumed_by_time = br * (elapsed_days / window_days)
        res["elapsed_days"] = elapsed_days
        res["budget_consumed_ratio"] = consumed_by_time
        res["budget_remaining_ratio"] = 1 - consumed_by_time
        remaining = 1 - consumed_by_time
        if br > 0 and remaining > 0:
            res["days_to_exhaustion"] = remaining * window_days / br
        elif remaining <= 0:
            res["days_to_exhaustion"] = 0.0
    if br is not None:
        res["sustainable"] = br <= 1.0
    return res


def render(res: dict, alerts: bool = True):
    slo, wd = res["slo_percent"], res["window_days"]
    print()
    print("=" * 68)
    print(f" SLO {slo}%  ·  周期 {wd:g} 天  ·  错误预算 {res['budget_ratio'] * 100:.4g}%")
    print("=" * 68)
    dt = res["allowed_downtime_human"]
    extra = "" if dt.endswith("分钟") else f"（{res['allowed_downtime_minutes']:.1f} 分钟）"
    print(f"允许不可用时长      : {dt}{extra}")
    for label, days in (("每天", 1), ("每周", 7)):
        m = days * 24 * 60 * res["budget_ratio"]
        print(f"  折算 {label}          : {fmt_duration(m)}")

    if "allowed_bad_requests" in res:
        print(f"\n请求总量            : {fmt_num(res['total_requests'])}")
        print(f"允许失败请求数      : {fmt_num(res['allowed_bad_requests'])}")
    if "bad_requests" in res:
        print(f"已失败请求数        : {fmt_num(res['bad_requests'])}")
        print(f"剩余可失败请求数    : {fmt_num(res['remaining_bad_requests'])}")
    if "observed_error_rate" in res:
        print(f"当前错误率          : {res['observed_error_rate'] * 100:.4g}%")

    if "budget_consumed_ratio" in res:
        c = res["budget_consumed_ratio"]
        bar_len = 40
        filled = max(0, min(bar_len, int(round(c * bar_len))))
        bar = "█" * filled + "·" * (bar_len - filled)
        print(f"\n预算消耗            : {c * 100:.1f}%  剩余 {res['budget_remaining_ratio'] * 100:.1f}%")
        print(f"                      [{bar}]")

    if "burn_rate" in res:
        br = res["burn_rate"]
        verdict = ("可持续：按此速度到周期结束预算刚好够用或有富余"
                   if br <= 1 else f"超速：比可持续速度快 {br:.2f} 倍")
        print(f"\n燃烧率 (burn rate)  : {br:.2f}×")
        print(f"判定                : {verdict}")
        if "days_to_exhaustion" in res:
            d = res["days_to_exhaustion"]
            if d <= 0:
                print("预算耗尽            : 已耗尽——应冻结特性发布，全部产能转向可靠性")
            else:
                tail = "（超出本周期，说明速度可持续）" if d > (
                    res["window_days"] - res.get("elapsed_days", 0)) else ""
                print(f"预算耗尽            : 约 {d:.2f} 天后{tail}")
        print("\n处置建议            : " + (
            "已耗尽 → 停止发布新特性，优先修复可靠性欠债" if res.get("budget_remaining_ratio", 1) <= 0
            else "预算紧张（<25%）→ 提高发布门槛，加强灰度与回滚准备"
            if res.get("budget_remaining_ratio", 1) < 0.25
            else "预算充裕 → 可以正常甚至更激进地发布，预算就是拿来花的"))

    if alerts:
        print("\n" + "-" * 68)
        print(" 多窗口多燃烧率告警阈值（Google SRE 标准配置）")
        print("-" * 68)
        for long_w, short_w, rate, frac, action in ALERT_POLICY:
            thr = rate * res["budget_ratio"] * 100
            head = f"{long_w} / {short_w}"
            print(f"  {head:<12} 燃烧率 {rate:>4.1f}×   触发时已耗预算 {frac * 100:>3.0f}%   {action}")
            print(f"  {'':<12} └─ 条件：两个窗口的错误率同时 > {thr:.4g}%")
        print("\n要点：长窗口保证「问题真实存在」，短窗口保证「问题仍在持续」，")
        print("      两者同时满足才告警——既避免抖动误报，也避免恢复后还在响。")
    print()


def main():
    ap = argparse.ArgumentParser(
        description="SLO 错误预算与燃烧率计算器",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--slo", type=float, required=True, help="可用性目标百分比，如 99.9")
    ap.add_argument("--window", type=float, default=30, dest="window_days",
                    help="SLO 周期天数（默认 30）")
    ap.add_argument("--total", type=float, help="周期内请求总数")
    ap.add_argument("--bad", type=float, help="周期内失败请求数")
    ap.add_argument("--error-rate", type=float, help="当前错误率百分比，如 0.07")
    ap.add_argument("--elapsed-days", type=float, help="周期已过去的天数（用于算耗尽时间）")
    ap.add_argument("--alerts-only", action="store_true", help="只输出告警阈值表")
    ap.add_argument("--json", action="store_true", dest="as_json")
    args = ap.parse_args()

    if not args.alerts_only and args.total is None and args.error_rate is None:
        ap.error("需要 --total（可配合 --bad）或 --error-rate；或使用 --alerts-only")
    if args.bad is not None and args.total is None:
        ap.error("--bad 需要配合 --total 使用")

    try:
        res = compute(args.slo, args.window_days, args.total, args.bad,
                      args.error_rate, args.elapsed_days)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.as_json:
        res["alert_policy"] = [
            {"long_window": lw, "short_window": sw, "burn_rate": br,
             "budget_consumed_at_trigger": frac, "action": act,
             "error_rate_threshold_percent": br * res["budget_ratio"] * 100}
            for lw, sw, br, frac, act in ALERT_POLICY]
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0

    if args.alerts_only:
        render({"slo_percent": args.slo, "window_days": args.window_days,
                "budget_ratio": (100 - args.slo) / 100,
                "allowed_downtime_minutes": args.window_days * 1440 * (100 - args.slo) / 100,
                "allowed_downtime_human": fmt_duration(
                    args.window_days * 1440 * (100 - args.slo) / 100)}, alerts=True)
        return 0

    render(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
