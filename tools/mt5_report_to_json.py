#!/usr/bin/env python3
"""把 MT5 汇出的报表（HTML）转成 performance.json 的 periods 片段。

MT5 有两种报表都能吃：
  * 策略测试报告：测试器 → 结果 → 右键 → 「报告」→ HTML
  * 实盘/观摩账号报告：终端 → 历史 → 右键 → 「报告」→ HTML

之所以走报表而不是自己从成交纪录重算：MT5 报表里的
「净值最大回撤 / Equity Drawdown Maximal」本来就是含未平仓浮亏的口径，
跟我们网站上「最大净值回撤」的定义一致，直接取用不会有口径落差。

用法：
    python3 tools/mt5_report_to_json.py --label "2026 年至今" report.html
    python3 tools/mt5_report_to_json.py --label "2025 全年" --capital 5000 report.html

输出可直接贴进 tools/data/performance.json 的 periods 阵列，
再跑 python3 tools/gen_perf.py 重新生成页面。
"""
import argparse
import html as html_mod
import json
import re
import sys
from pathlib import Path

# MT5 报表的栏位标签（英文 / 简体 / 繁体）。key 是我们内部的栏位名。
LABELS = {
    "initial_deposit": ["initial deposit", "初始存款", "初始入金"],
    "net_profit": ["total net profit", "总净盈利", "净利润", "總淨利", "淨利"],
    "profit_factor": ["profit factor", "盈利因子", "获利因子", "獲利因子"],
    "trades": ["total trades", "总交易", "交易总数", "總交易"],
    "equity_dd": [
        "equity drawdown maximal", "maximal equity drawdown",
        "净值最大回撤", "最大净值回撤", "淨值最大回撤",
    ],
    "balance_dd": [
        "balance drawdown maximal", "maximal balance drawdown",
        "余额最大回撤", "餘額最大回撤",
    ],
}

CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]*>")
NUM_RE = re.compile(r"-?[\d  ,]+(?:\.\d+)?")
PCT_RE = re.compile(r"\(\s*(-?[\d.]+)\s*%\s*\)")


def clean(cell):
    return html_mod.unescape(TAG_RE.sub("", cell)).replace(" ", " ").strip()


def to_number(s):
    m = NUM_RE.search(s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(" ", "").replace(" ", "").replace(",", ""))
    except ValueError:
        return None


def parse_report(text):
    """把报表所有储存格拉平，用「标签储存格 → 下一个储存格」的方式取值。"""
    cells = [clean(c) for c in CELL_RE.findall(text)]
    found = {}
    for i, cell in enumerate(cells):
        key_text = cell.rstrip(":：").strip().lower()
        for field, aliases in LABELS.items():
            if field in found:
                continue
            if any(key_text == a or key_text.startswith(a) for a in aliases):
                # 值可能在同一格（「标签: 值」）或下一格
                inline = cell.split(":")[-1].split("：")[-1].strip()
                value = inline if inline and inline.lower() != key_text else (
                    cells[i + 1] if i + 1 < len(cells) else "")
                found[field] = value
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report", help="MT5 汇出的 HTML 报表")
    ap.add_argument("--label", required=True, help='区间名称，如 "2026 年至今"')
    ap.add_argument("--capital", type=float, default=None,
                    help="初始资金；不给则用报表里的初始存款")
    ap.add_argument("--encoding", default=None,
                    help="报表编码；MT5 常见 utf-16 / utf-8，预设自动尝试")
    args = ap.parse_args()

    raw = Path(args.report).read_bytes()
    text = None
    for enc in ([args.encoding] if args.encoding else ["utf-8", "utf-16", "cp1252", "gbk"]):
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError, TypeError):
            continue
    if text is None:
        print("✗ 无法解码报表，请用 --encoding 指定编码", file=sys.stderr)
        return 2

    f = parse_report(text)

    missing = [k for k in ("net_profit", "profit_factor", "trades") if k not in f]
    if missing:
        print("✗ 报表里找不到栏位：" + "、".join(missing), file=sys.stderr)
        print("  认得的栏位：" + "、".join(f) if f else "  一个栏位都没认出来", file=sys.stderr)
        print("  若报表是其他语言，请在本档 LABELS 里补上对应标签。", file=sys.stderr)
        return 2

    capital = args.capital or to_number(f.get("initial_deposit", ""))
    if not capital:
        print("✗ 报表里没有初始存款，请用 --capital 指定", file=sys.stderr)
        return 2

    # 净值最大回撤：优先取百分比；MT5 写成「1 234.56 (12.34%)」
    dd_src = f.get("equity_dd") or f.get("balance_dd") or ""
    dd_pct = None
    m = PCT_RE.search(dd_src)
    if m:
        dd_pct = float(m.group(1))
    else:
        dd_abs = to_number(dd_src)
        if dd_abs is not None:
            dd_pct = dd_abs / capital * 100.0
    if dd_pct is None:
        print("✗ 报表里找不到净值最大回撤，请确认报表来源", file=sys.stderr)
        return 2
    if not f.get("equity_dd"):
        print("⚠ 报表没有「净值最大回撤」，已改用余额最大回撤 —— "
              "这不含未平仓浮亏，与网站口径不同，请人工确认。", file=sys.stderr)

    period = {
        "label": args.label,
        "net_profit": round(to_number(f["net_profit"])),
        "max_dd_pct": round(dd_pct, 1),
        "profit_factor": round(to_number(f["profit_factor"]), 2),
        "trades": int(to_number(f["trades"])),
    }

    print(f"# 初始资金（请确认与 performance.json 的 initial_capital 一致）：{capital:,.0f}",
          file=sys.stderr)
    print(json.dumps(period, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
