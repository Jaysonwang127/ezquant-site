#!/usr/bin/env python3
"""把观摩账号的 MT5 报表换算成「以建议本金为分母」的绩效卡数字。

用途：TG 绩效卡对外报的百分比，分母要用**建议本金**，不是观摩账号自己的本金。
前提（已确认）：观摩账号跑的手数即建议本金对应的手数，所以净利与浮亏金额
可以直接除以建议本金，不需要再按手数比例缩放。

    python3 tools/tg_card.py --slug caifu 观摩账号报表.html
    python3 tools/tg_card.py --slug caifu --json 观摩账号报表.html

金额类（净利、浮亏）与比率无关，直接取用；比率类一律用建议本金当分母：

    报酬率       = 净利       ÷ recommended_capital
    最大净值回撤 = 浮亏金额   ÷ recommended_capital

两者共用同一个分母 —— 只换报酬率不换回撤，会让绩效卡看起来比实际安全。
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from mt5_report_to_json import PCT_RE, decode, parse_report, to_number  # noqa: E402
from perfdata import DATA, r1  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", help="观摩账号汇出的 MT5 HTML 报表")
    ap.add_argument("--slug", required=True, help="EA 代号，如 caifu")
    ap.add_argument("--label", default=None, help="区间名称，仅用于显示")
    ap.add_argument("--json", action="store_true", help="输出 JSON 供程式消费")
    ap.add_argument("--encoding", default=None)
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    ea = next((e for e in data["eas"] if e["slug"] == args.slug), None)
    if ea is None:
        print(f"✗ performance.json 里没有 slug「{args.slug}」", file=sys.stderr)
        return 2
    rec = ea.get("recommended_capital")
    if not rec:
        print(f"✗ {ea['name']} 没有设定 recommended_capital", file=sys.stderr)
        return 2

    text = decode(pathlib.Path(args.report).read_bytes(), args.encoding)
    if text is None:
        print("✗ 无法解码报表，请用 --encoding 指定编码", file=sys.stderr)
        return 2
    f = parse_report(text)

    missing = [k for k in ("net_profit", "profit_factor", "trades") if k not in f]
    if missing:
        print("✗ 报表里找不到栏位：" + "、".join(missing), file=sys.stderr)
        return 2

    acct = to_number(f.get("initial_deposit", "")) or 0
    net = to_number(f["net_profit"])

    # 浮亏金额：报表写成「1 234.56 (12.34%)」，优先取金额
    dd_src = f.get("equity_dd") or f.get("balance_dd") or ""
    dd_amount = to_number(dd_src)
    if dd_amount is None:
        m = PCT_RE.search(dd_src)
        if not (m and acct):
            print("✗ 报表里读不到净值最大回撤金额", file=sys.stderr)
            return 2
        dd_amount = float(m.group(1)) / 100.0 * acct
    if not f.get("equity_dd"):
        print("⚠ 报表没有「净值最大回撤」，已改用余额最大回撤 —— "
              "这不含未平仓浮亏，与对外口径不同。", file=sys.stderr)

    ret = r1(net / rec * 100.0)
    dd = r1(dd_amount / rec * 100.0)

    if dd > 100.0:
        print(f"✗ 以建议本金 ${rec:,} 为分母，回撤会是 {dd:.1f}% —— "
              f"浮亏 ${dd_amount:,.0f} 已超过本金，这个数字不该对外发布。\n"
              f"  请确认观摩账号的手数是否真的对应建议本金。", file=sys.stderr)
        return 1

    out = {
        "slug": args.slug, "name": ea["name"], "label": args.label,
        "recommended_capital": rec,
        "net_profit": round(net),
        "return_pct": ret,
        "max_dd_pct": dd,
        "max_dd_amount": round(dd_amount),
        "profit_factor": round(to_number(f["profit_factor"]), 2),
        "trades": int(to_number(f["trades"])),
    }

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    sign = "+" if net >= 0 else "-"
    print(f"\n  {ea['name']}" + (f"　{args.label}" if args.label else ""))
    print(f"  {'─' * 46}")
    print(f"  建议本金（分母）    ${rec:,}")
    print(f"  净利                {sign}${abs(round(net)):,}")
    print(f"  报酬率              {sign}{abs(ret):.1f}%")
    print(f"  最大净值回撤        {dd:.1f}%　（浮亏 ${dd_amount:,.0f}）")
    print(f"  获利因子            {out['profit_factor']:.2f}")
    print(f"  交易笔数            {out['trades']:,}")
    print(f"  {'─' * 46}")
    if acct:
        print(f"  对照：观摩账号本金 ${acct:,.0f} → 报酬率 {net/acct*100:+.1f}%、"
              f"回撤 {dd_amount/acct*100:.1f}%")
        print(f"  （对外一律用建议本金那组，两组不可混用）")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
