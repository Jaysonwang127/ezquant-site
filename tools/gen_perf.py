#!/usr/bin/env python3
"""从 tools/data/performance.json 生成各 EA 页面的「历史绩效」区块（#s1）。

用法：
    python3 tools/gen_perf.py --check    # 只比对，不写档（提交前 / CI 用）
    python3 tools/gen_perf.py            # 实际写回 ea/*.html

设计原则：
  * 报酬率一律由 net_profit / initial_capital 推导，不从 JSON 手填，
    避免各页口径飘移（这正是目前人工维护最容易出错的地方）。
  * 所有汇总值都先取「显示值」再往上加总，确保读者看到的数字加得起来：
    累计报酬率 = 各区间显示报酬率之和；长条图宽度依显示值等比缩放。
  * 只重写 <section ... id="s1"> ... </section>，页面其他部分完全不动。
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from perfdata import r1, derive, BlownAccountError  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data" / "performance.json"
EA_DIR = ROOT / "ea"

# 长条图中最长一条的宽度（%），其余依比例缩放。
BAR_MAX_WIDTH = 92.6

PERF_NOTE = (
    "以上为历史绩效统计，非实盘成交纪录；过去绩效不代表未来收益。"
    "报酬率＝净利 ÷ 初始资金，未计入复利与出入金。"
    "<strong>最大净值回撤</strong>为账户权益（含未平仓浮亏）的最大跌幅，非仅已平仓部分。"
    "实盘运行情况可申请观摩账号查看。"
)

SECTION_RE = re.compile(r'<section class="detail-section" id="s1">.*?</section>', re.S)
CARD_RE = re.compile(r'<article class="card".*?</article>', re.S)
CARD_PERF_RE = re.compile(r'<div class="perf">.*?</div></div></div>', re.S)
CARD_HREF_RE = re.compile(r'href="ea/([a-z0-9_-]+)\.html"')


def money(v):
    """+$3,587 / -$1,204"""
    sign = "+" if v >= 0 else "-"
    return f"{sign}${abs(round(v)):,}"


def pct(v, signed=True):
    """+30.5% / 8.3%"""
    if signed:
        return f"{'+' if v >= 0 else '-'}{abs(v):.1f}%"
    return f"{v:.1f}%"


def cls(v):
    return "pos" if v >= 0 else "neg"


def build_section(ea):
    periods = ea["periods"]
    if not periods:
        raise ValueError(f'{ea["slug"]}: periods 不可为空')
    cap, periods = derive(ea)

    total_net = sum(p["net_profit"] for p in periods)
    total_return = r1(sum(p["_ret"] for p in periods))
    max_dd = max(p["_dd"] for p in periods)
    total_trades = sum(p["trades"] for p in periods)
    avg_pf = sum(p["profit_factor"] for p in periods) / len(periods)
    multi = len(periods) > 1

    net_sub = f"{len(periods)} 个区间合计" if multi else periods[0]["label"]
    pf_sub = f"{'各区间平均' if multi else '毛利 ÷ 毛损'} · {total_trades:,} 笔"

    cond = (
        '<div class="perf-cond">'
        f'<span><b>品种</b> {ea["symbol"]}</span>'
        f"<span><b>初始资金</b> ${cap:,}</span>"
        f'<span><b>起始手数</b> {ea["start_lots"]}</span>'
        "</div>"
    )

    kpi = (
        '<div class="perf-kpi">'
        '<div class="k"><span class="kl">累计净利</span>'
        f'<span class="kv {cls(total_net)}">{money(total_net)}</span>'
        f'<span class="ks">{net_sub}</span></div>'
        '<div class="k"><span class="kl">累计报酬率</span>'
        f'<span class="kv {cls(total_return)}">{pct(total_return)}</span>'
        '<span class="ks">净利 ÷ 初始资金</span></div>'
        '<div class="k"><span class="kl">最大净值回撤</span>'
        f'<span class="kv">{pct(max_dd, signed=False)}</span>'
        '<span class="ks">各区间最大值</span></div>'
        '<div class="k"><span class="kl">获利因子</span>'
        f'<span class="kv">{avg_pf:.2f}</span>'
        f'<span class="ks">{pf_sub}</span></div>'
        "</div>"
    )

    # 报酬率与回撤共用同一比例尺，最长者 = BAR_MAX_WIDTH
    scale_base = max(max(abs(p["_ret"]) for p in periods),
                     max(p["_dd"] for p in periods))
    scale = BAR_MAX_WIDTH / scale_base if scale_base else 0.0

    rows = "".join(
        '<div class="br">'
        f'<span class="bl">{p["label"]}</span>'
        '<div class="bt">'
        f'<div class="bf" style="width:{r1(abs(p["_ret"]) * scale):.1f}%"></div>'
        f'<div class="bd" style="width:{r1(p["_dd"] * scale):.1f}%"></div>'
        "</div>"
        f'<span class="bv">{pct(p["_ret"])}'
        f'<small>回撤 {pct(p["_dd"], signed=False)}</small></span>'
        "</div>"
        for p in periods
    )
    bars = (
        '<div class="perf-bars">'
        '<div class="bh"><b>各区间报酬率 vs 最大回撤</b>'
        '<span><i style="background:var(--green)"></i>报酬率'
        '<i style="background:var(--red)"></i>最大净值回撤</span></div>'
        f"{rows}</div>"
    )

    trs = "\n".join(
        f'<tr><td>{p["label"]}</td>'
        f'<td class="num {cls(p["net_profit"])}">{money(p["net_profit"])}</td>'
        f'<td class="num {cls(p["_ret"])}">{pct(p["_ret"])}</td>'
        f'<td class="num">{pct(p["_dd"], signed=False)}</td>'
        f'<td class="num">{p["profit_factor"]:.2f}</td>'
        f'<td class="num">{p["trades"]:,}</td></tr>'
        for p in periods
    )
    table = (
        '<table class="perf-table"><tr><th>期间</th><th>净利</th><th>报酬率</th>'
        "<th>最大净值回撤</th><th>获利因子</th><th>交易笔数</th></tr>\n"
        f"{trs}\n</table>"
    )

    return (
        '<section class="detail-section" id="s1"><div class="container">\n'
        "<h2>历史绩效</h2>\n"
        f"{cond}\n{kpi}\n{bars}\n{table}\n"
        f'<p class="perf-note">{PERF_NOTE}</p>\n'
        "</div></section>"
    )


def build_card_perf(ea):
    """首页产品卡的绩效块 —— 显示「最新一个区间」，而非累计。"""
    p = ea["periods"][-1]
    cap = ea["_display_capital"]
    ret, dd = p["_ret"], p["_dd"]
    return (
        '<div class="perf">'
        f'<div class="ph">{p["label"]} ・ 历史绩效 ・ ${cap:,} / {ea["start_lots"]}</div>'
        '<div class="phero">'
        f'<span class="pv-big {cls(ret)}">{pct(ret)}</span>'
        f'<span class="pv-sub">报酬率 ｜ 净利 {money(p["net_profit"])}</span></div>'
        '<div class="pr">'
        '<div class="p"><span class="pl">最大净值回撤</span>'
        f'<span class="pv">{pct(dd, signed=False)}</span></div>'
        '<div class="p"><span class="pl">获利因子</span>'
        f'<span class="pv">{p["profit_factor"]:.2f}</span></div>'
        '<div class="p"><span class="pl">交易笔数</span>'
        f'<span class="pv">{p["trades"]:,}</span></div>'
        "</div></div>"
    )


def rewrite_index(by_slug, check):
    """重写首页各产品卡的绩效块。回传 (是否有变更, 问题列表)。"""
    path = ROOT / "index.html"
    problems = []
    if not path.exists():
        return False, ["找不到 index.html"]
    html = path.read_text(encoding="utf-8")

    seen = set()

    def fix_card(m):
        card = m.group(0)
        href = CARD_HREF_RE.search(card)
        if not href:
            return card
        slug = href.group(1)
        seen.add(slug)
        ea = by_slug.get(slug)
        if ea is None:
            problems.append(f"首页卡片指向 ea/{slug}.html，但 performance.json 里没有这支 EA")
            return card
        if not CARD_PERF_RE.search(card):
            problems.append(f"首页 {slug} 卡片找不到绩效块")
            return card
        return CARD_PERF_RE.sub(lambda _: build_card_perf(ea), card, count=1)

    new_html = CARD_RE.sub(fix_card, html)

    for slug in by_slug:
        if slug not in seen:
            problems.append(f"performance.json 有 {slug}，但首页没有对应卡片")

    changed = new_html != html
    if changed and not check:
        path.write_text(new_html, encoding="utf-8")
    return changed, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="只比对不写档；有差异时以状态码 1 结束")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    by_slug = {ea["slug"]: ea for ea in data["eas"]}
    changed, missing = [], []

    for ea in data["eas"]:
        path = EA_DIR / f'{ea["slug"]}.html'
        if not path.exists():
            missing.append(ea["slug"])
            continue
        html = path.read_text(encoding="utf-8")
        if not SECTION_RE.search(html):
            missing.append(f'{ea["slug"]}（找不到 #s1 区块）')
            continue
        new_section = build_section(ea)
        new_html = SECTION_RE.sub(lambda _: new_section, html, count=1)
        if new_html != html:
            changed.append(ea["slug"])
            if not args.check:
                path.write_text(new_html, encoding="utf-8")

    index_changed, index_problems = rewrite_index(by_slug, args.check)
    if index_changed:
        changed.append("index.html")
    missing.extend(index_problems)

    if missing:
        print("✗ 以下项目无法处理：" + "、".join(missing), file=sys.stderr)
        return 2

    if args.check:
        if changed:
            print("✗ 页面与 performance.json 不一致：" + "、".join(changed), file=sys.stderr)
            print("  请执行 python3 tools/gen_perf.py 重新生成。", file=sys.stderr)
            return 1
        print(f"✓ {len(data['eas'])} 支 EA 的绩效区块与首页卡片均与 performance.json 一致")
        return 0

    print(f"✓ 已生成 {len(data['eas'])} 支 EA 的绩效区块与首页卡片"
          + ("，更新：" + "、".join(changed) if changed else "，无变更"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
