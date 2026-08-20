#!/usr/bin/env python3
"""生成跨产品风控矩阵页 ea/risk-matrix.html。

资料来源：
  * tools/data/risk-matrix.json   —— 各 EA 的风控机制有无
  * tools/data/performance.json   —— 历史最大净值回撤（不重复登打，直接取用）

页面外壳（header / footer / Telegram 浮动按钮）从 ea/jinshe.html 抓取后复用，
所以之后改了导览或页尾，重跑本脚本即可自动跟上。

用法：
    python3 tools/gen_risk_matrix.py --check
    python3 tools/gen_risk_matrix.py
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from perfdata import derive  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
MATRIX = ROOT / "tools" / "data" / "risk-matrix.json"
PERF = ROOT / "tools" / "data" / "performance.json"
SHELL_SRC = ROOT / "ea" / "jinshe.html"
OUT = ROOT / "ea" / "risk-matrix.html"

HEADER_RE = re.compile(r'<header class="site">.*?</header>', re.S)
TAIL_RE = re.compile(r'<footer class="site">.*\Z', re.S)

EXTRA_CSS = """<style>
.rm-table{font-size:13.5px;}
.rm-table th:first-child,.rm-table td:first-child{text-align:left;white-space:nowrap;}
.rm-table th:not(:first-child),.rm-table td:not(:first-child){text-align:center;}
.rm-table td.cell{cursor:help;}
.rm-table .mk{display:inline-block;font-weight:800;font-size:16px;line-height:1;}
.rm-table .v-yes .mk{color:var(--green);}
.rm-table .v-no .mk{color:var(--red);}
.rm-table .v-part .mk{color:var(--amber);}
.rm-table .v-na .mk{color:var(--muted);}
.rm-table .v-unk .mk{color:var(--blue);}
.rm-table td.dd{font-family:Menlo,Consolas,monospace;font-weight:700;}
.rm-legend{display:flex;flex-wrap:wrap;gap:8px 22px;margin:14px 0 0;padding:12px 16px;background:#f4f7fc;border:1px solid var(--border);border-radius:10px;font-size:13px;}
.rm-legend span{white-space:nowrap;color:var(--muted);}
.rm-legend b{font-size:15px;margin-right:5px;}
.rm-note{color:var(--muted);font-size:12px;margin-top:12px;line-height:1.7;}
.rm-detail h4{margin:22px 0 6px;font-size:15px;color:var(--navy);}
.rm-detail ul{margin:0;padding-left:20px;}
.rm-detail li{font-size:13.5px;margin-bottom:4px;}
.rm-detail li b{color:var(--navy);}
.rm-detail h4 .rm-lv{margin-left:10px;font-size:11px;font-weight:600;color:var(--muted);background:#f4f7fc;border:1px solid var(--border);border-radius:999px;padding:2px 10px;vertical-align:2px;}
.rm-detail .rm-src{font-size:12.5px;color:var(--muted);margin:6px 0 0;line-height:1.7;}
@media (max-width:820px){.rm-scroll{overflow-x:auto;}.rm-scroll table{min-width:760px;}}
</style>"""


def build(matrix, perf):
    perf_by_slug = {e["slug"]: e for e in perf["eas"]}
    vals = matrix["values"]
    cols = matrix["columns"]

    shell = SHELL_SRC.read_text(encoding="utf-8")
    header = HEADER_RE.search(shell).group(0)
    tail = TAIL_RE.search(shell).group(0).replace(
        "start=web_ea_jinshe", "start=web_ea_risk_matrix")

    # ---- 主表 ----
    head_cells = "".join(f"<th>{c['label']}</th>" for c in cols)
    rows = []
    for ea in matrix["eas"]:
        p = perf_by_slug[ea["slug"]]
        derive(p)
        max_dd = max(x["_dd"] for x in p["periods"])
        cells = ""
        for c in cols:
            cell = ea["cells"][c["key"]]
            spec = vals[cell["v"]]
            title = cell["t"].replace('"', "&quot;")
            cells += (f'<td class="cell {spec["cls"]}" title="{title}">'
                      f'<span class="mk">{spec["mark"]}</span></td>')
        rows.append(
            f'<tr><td><a href="{ea["slug"]}.html">{p["name"]}</a> '
            f'<span class="risk {ea["risk_class"]}">{ea["risk_level"]}</span></td>'
            f"{cells}"
            f'<td class="dd">{max_dd:.1f}%</td></tr>'
        )
    table = (
        '<div class="rm-scroll"><table class="rm-table">'
        f"<tr><th>产品</th>{head_cells}<th>历史最大净值回撤</th></tr>"
        + "".join(rows)
        + "</table></div>"
    )

    legend = '<div class="rm-legend">' + "".join(
        f'<span><b class="{v["cls"]}" style="color:inherit">{v["mark"]}</b>{v["meaning"]}</span>'
        for v in vals.values()
    ) + "</div>"

    # ---- 逐项说明 ----
    detail = []
    for ea in matrix["eas"]:
        p = perf_by_slug[ea["slug"]]
        items = "".join(
            f'<li><b>{c["label"]}：</b>{vals[ea["cells"][c["key"]]["v"]]["mark"]} '
            f'{ea["cells"][c["key"]]["t"]}</li>'
            for c in cols
        )
        lvl = matrix["evidence_levels"][ea.get("evidence", "page")]
        note = f'<p class="rm-src">{ea["note"]}</p>' if ea.get("note") else ""
        detail.append(f'<h4>{p["name"]}<span class="rm-lv">{lvl}</span></h4>'
                      f'<ul>{items}</ul>{note}')
    detail_html = '<div class="rm-detail">' + "".join(detail) + "</div>"

    lv = {k: [e["slug"] for e in matrix["eas"] if e.get("evidence", "page") == k]
          for k in ("page", "docs", "code")}
    parts = []
    if lv["code"]:
        parts.append(f'{len(lv["code"])} 支已完成原始码逐条核对')
    if lv["docs"]:
        parts.append(f'{len(lv["docs"])} 支有专案文件或实机佐证')
    if lv["page"]:
        parts.append(f'{len(lv["page"])} 支仅依产品页文案整理、尚待查证')
    verify_note = (
        "各产品的查证程度不一：" + "、".join(parts) + "。"
        "标示为「?」者代表该来源未说明此机制，并不等于该机制不存在。"
    )

    return f"""<!doctype html><html lang="zh-Hans"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>风控矩阵｜EZQUANT 黄金 EA</title>
<meta name="description" content="EZQUANT 七支黄金 EA 的风控机制对照表：逆势加仓、单笔硬止损、层数上限、整批止损、账户权益熔断、点差过滤与对冲削单。">
<link rel="stylesheet" href="../assets/style.css">
{EXTRA_CSS}</head><body>
{header}

<section class="detail-hero"><div class="container">
<h1>风控矩阵</h1>
<p class="subtitle">七支策略的风险控制机制一次对照</p>
<div class="cta"><a class="btn" href="../index.html#products">返回策略库</a><a class="btn ghost" href="../index.html#contact">微信咨询 / 申请观摩</a></div>
</div></section>

<section class="detail-section"><div class="container">
<h2>机制对照</h2>
<p class="lead">回撤大小与风控结构直接相关。下表把七支策略的关键防线并排比较，方便依自身风险承受度选择；把游标移到符号上可看说明。</p>
{table}
{legend}
<p class="rm-note">{verify_note}历史最大净值回撤取自各产品页绩效区间的最大值，为账户权益（含未平仓浮亏）口径。过去绩效不代表未来收益。</p>
</div></section>

<section class="detail-section"><div class="container">
<h2>逐项说明</h2>
{detail_html}
</div></section>

<section class="detail-section"><div class="container">
<h2>怎么读这张表</h2>
<p><b>没有「最好」的一栏组合，只有合不合适。</b>不加仓、有单笔硬止损的结构（如金鼎、百炼成金、两仪）风险边界清楚，但在盘整或低波动期间会明显转弱；含逆势网格的结构（如顺势之星、黄金双卫、黄金罗盘）胜率与获利因子较高，代价是浮亏在极端单边行情下可能显著放大。</p>
<p>特别提醒三点：<b>层数硬上限</b>缺席时，曝险会随行情延续无上限扩张；<b>整批 / 全局止损</b>预设关闭时，等于把最后一道防线交给使用者自行开启；<b>账户权益熔断</b>是唯一在账户层级生效的机制，其余防线都只作用在单笔或单一方向。</p>
<p>若不确定该选哪一支，建议先申请观摩账号实际观察一段时间，或加微信 <b>ezmoney50</b> 说明你的资金规模与可承受回撤，再由我们协助配对。</p>
</div></section>

{tail}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只比对不写档")
    args = ap.parse_args()

    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    perf = json.loads(PERF.read_text(encoding="utf-8"))

    perf_slugs = {e["slug"] for e in perf["eas"]}
    matrix_slugs = {e["slug"] for e in matrix["eas"]}
    if perf_slugs != matrix_slugs:
        print("✗ risk-matrix.json 与 performance.json 的 EA 清单不一致："
              f"仅在绩效档 {sorted(perf_slugs - matrix_slugs)}，"
              f"仅在风控档 {sorted(matrix_slugs - perf_slugs)}", file=sys.stderr)
        return 2

    cols = {c["key"] for c in matrix["columns"]}
    for ea in matrix["eas"]:
        miss = cols - set(ea["cells"])
        if miss:
            print(f"✗ {ea['slug']} 缺少栏位：{sorted(miss)}", file=sys.stderr)
            return 2
        bad = [k for k, v in ea["cells"].items() if v["v"] not in matrix["values"]]
        if bad:
            print(f"✗ {ea['slug']} 有无效的值：{bad}", file=sys.stderr)
            return 2

    out = build(matrix, perf)
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else None

    if args.check:
        if old != out:
            print("✗ ea/risk-matrix.html 与资料档不一致，请执行 "
                  "python3 tools/gen_risk_matrix.py", file=sys.stderr)
            return 1
        print("✓ ea/risk-matrix.html 与资料档一致")
        return 0

    OUT.write_text(out, encoding="utf-8")
    print(f"✓ 已生成 ea/risk-matrix.html（{len(matrix['eas'])} 支 EA × "
          f"{len(matrix['columns'])} 项机制）"
          + ("，内容有更新" if old != out else "，无变更"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
