#!/usr/bin/env python3
"""绩效资料的载入与推导 —— gen_perf / gen_risk_matrix / check_consistency 共用。

两个资金栏位，刻意分开：

  backtest_capital  回测实际使用的起始资金。这是历史事实，不该因为文案而改。
  display_capital   网站上用来计算报酬率与回撤的基准（＝建议本金）。
                    省略时等于 backtest_capital。

推导规则（同样的手数下）：
  净利、获利因子、交易笔数   与资金无关，直接取用
  报酬率      = 净利 ÷ display_capital
  最大净值回撤 = 回测浮亏金额 ÷ display_capital
              = (回测回撤% × backtest_capital) ÷ display_capital

换句话说：**回撤百分比会跟报酬率一起等比缩放**。把基准资金调小，
报酬率变漂亮的同时回撤也会同比例放大 —— 两者不能只调一边。
若推导出的回撤超过 100%，代表该资金根本撑不过这段历史，会直接报错。
"""
import json
import pathlib
from decimal import Decimal, ROUND_HALF_UP

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "tools" / "data" / "performance.json"


def r1(v):
    """四舍五入到小数一位（half-up）。"""
    return float(Decimal(str(v)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


class BlownAccountError(ValueError):
    """以指定的 display_capital 计算时，历史回撤会超过 100%。"""


def derive(ea):
    """就地补上推导栏位，并回传 (display_capital, periods)。"""
    bt = ea["backtest_capital"]
    disp = ea.get("display_capital") or bt
    if bt <= 0 or disp <= 0:
        raise ValueError(f'{ea["slug"]}: 资金必须为正数')

    scale = bt / disp
    for p in ea["periods"]:
        p["_ret"] = r1(p["net_profit"] / disp * 100.0)
        p["_dd_amount"] = p["max_dd_pct"] / 100.0 * bt
        p["_dd"] = r1(p["max_dd_pct"] * scale)
        if p["_dd"] > 100.0:
            raise BlownAccountError(
                f'{ea["name"]}（{ea["slug"]}）{p["label"]}：'
                f'回测在 ${bt:,} 上的最大浮亏为 ${p["_dd_amount"]:,.0f}，'
                f'以 ${disp:,} 为基准会是 {p["_dd"]:.1f}% 的回撤 —— 帐户撑不过这段历史。'
            )
    ea["_display_capital"] = disp
    return disp, ea["periods"]


def load():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    for ea in data["eas"]:
        derive(ea)
    return data
