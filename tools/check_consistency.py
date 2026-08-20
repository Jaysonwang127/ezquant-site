#!/usr/bin/env python3
"""全站数字一致性检查。

人工维护 8 个 HTML 档最常见的问题不是算错，而是「同一个数字在三个地方各写各的」。
本脚本把这些跨档比对自动化：

  [E] 内文提到的回撤百分比 与 绩效表的最大净值回撤 对不上
  [E] 内文提到的交易笔数   与 绩效表的笔数 对不上
  [E] 首页卡片的「建议资金」与 EA 页 hero 的「建议最低资金」对不上
  [W] 绩效统计的初始资金   与 建议最低资金 不同（口径不同，不一定是错，但要确认文案讲清楚）

用法：python3 tools/check_consistency.py        （有 [E] 时以状态码 1 结束）
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data" / "performance.json"

PERF_SECTION_RE = re.compile(r'<section class="detail-section" id="s1">.*?</section>', re.S)
TAG_RE = re.compile(r"<[^>]*>")
CARD_RE = re.compile(r'<article class="card".*?</article>', re.S)
CARD_HREF_RE = re.compile(r'href="ea/([a-z0-9_-]+)\.html"')
CARD_CAPITAL_RE = re.compile(r'<span class="pl">建议资金</span><span class="pv">([^<]+)</span>')
HERO_CAPITAL_RE = re.compile(r"建议最低资金：<strong>([^<]+)</strong>")

# 内文里的回撤提及。刻意排除「A%~B%」这类区间表述与「达到设定比例（默认20%）」这类参数说明。
DD_MENTION_RE = re.compile(r"(?:最大)?回撤(?:约|約)?\s*([0-9]+(?:\.[0-9]+)?)\s*%")
RANGE_RE = re.compile(r"[0-9.]+\s*%\s*[~～-]\s*[0-9.]+\s*%")
PARAM_RE = re.compile(r"(?:默认|預設|预设|设定比例|达到)\s*[0-9.]+\s*%")
TRADES_MENTION_RE = re.compile(r"共\s*([0-9,]+)\s*笔交易")

TOL = 0.05  # 百分点容差


def text_of(html):
    return TAG_RE.sub("", html)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    eas = {ea["slug"]: ea for ea in data["eas"]}

    errors, warns = [], []

    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    card_capital = {}
    for card in CARD_RE.finditer(index_html):
        href = CARD_HREF_RE.search(card.group(0))
        cap = CARD_CAPITAL_RE.search(card.group(0))
        if href and cap:
            card_capital[href.group(1)] = cap.group(1).strip()

    for slug, ea in eas.items():
        path = ROOT / "ea" / f"{slug}.html"
        name = ea["name"]
        if not path.exists():
            errors.append(f"{name}（{slug}）：找不到 ea/{slug}.html")
            continue

        html = path.read_text(encoding="utf-8")
        body = PERF_SECTION_RE.sub("", html)          # 绩效区块是生成的，不检查自己
        prose = text_of(body)
        # 剔除区间表述与参数说明，避免误报
        prose_clean = PARAM_RE.sub(" ", RANGE_RE.sub(" ", prose))

        known_dd = {round(p["max_dd_pct"], 1) for p in ea["periods"]}
        known_trades = {p["trades"] for p in ea["periods"]}
        known_trades.add(sum(p["trades"] for p in ea["periods"]))

        for m in DD_MENTION_RE.finditer(prose_clean):
            v = float(m.group(1))
            if not any(abs(v - d) <= TOL for d in known_dd):
                errors.append(
                    f"{name}（{slug}）：内文写「回撤 {v}%」，但绩效表的最大净值回撤是 "
                    + "、".join(f"{d}%" for d in sorted(known_dd))
                )

        for m in TRADES_MENTION_RE.finditer(prose_clean):
            v = int(m.group(1).replace(",", ""))
            if v not in known_trades:
                errors.append(
                    f"{name}（{slug}）：内文写「共 {v:,} 笔交易」，但绩效表的笔数是 "
                    + "、".join(f"{t:,}" for t in sorted(known_trades))
                )

        hero = HERO_CAPITAL_RE.search(html)
        hero_cap = hero.group(1).strip() if hero else None
        idx_cap = card_capital.get(slug)
        if hero_cap and idx_cap:
            # 只比对金额本身，忽略「起」「（依…而定）」等尾巴
            h = re.search(r"\$[\d,]+", hero_cap)
            i = re.search(r"\$[\d,]+", idx_cap)
            if h and i and h.group(0) != i.group(0):
                errors.append(
                    f"{name}（{slug}）：首页卡片写「建议资金 {idx_cap}」，"
                    f"但 EA 页 hero 写「建议最低资金 {hero_cap}」"
                )
        elif hero_cap is None:
            warns.append(f"{name}（{slug}）：EA 页 hero 找不到「建议最低资金」")
        elif idx_cap is None:
            warns.append(f"{name}（{slug}）：首页卡片找不到「建议资金」")

        if hero_cap:
            h = re.search(r"\$([\d,]+)", hero_cap)
            if h and int(h.group(1).replace(",", "")) != ea["initial_capital"]:
                warns.append(
                    f"{name}（{slug}）：绩效统计基准 ${ea['initial_capital']:,}，"
                    f"但建议最低资金写 {hero_cap} —— 请确认文案有说明两者口径不同"
                )

    for e in errors:
        print(f"[E] {e}")
    for w in warns:
        print(f"[W] {w}")

    print()
    if errors:
        print(f"✗ {len(errors)} 项矛盾、{len(warns)} 项提醒")
        return 1
    print(f"✓ 无矛盾（{len(warns)} 项提醒）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
