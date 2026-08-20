# tools —— 网站数字的单一事实来源

这个目录把原本靠人工维护的两件事自动化：

1. **绩效数字** —— 7 支 EA 页面 + 首页卡片的绩效区块，全部由 `data/performance.json` 生成
2. **风控矩阵** —— 跨产品的风控机制对照表，由 `data/risk-matrix.json` 生成，
   输出到 `tools/out/`，**仅供内部稽核与业务对话，不放上网站**

改数字请改 JSON，**不要手改 HTML**，否则下次生成会被覆盖。

---

## 常用指令

```bash
# 提交前跑这三条
python3 tools/gen_perf.py --check          # 页面绩效是否与 JSON 一致
python3 tools/check_consistency.py         # 跨页数字有没有互相矛盾

# 改完 JSON 之后重新生成
python3 tools/gen_perf.py
python3 tools/gen_risk_matrix.py   # 输出到 tools/out/，内部检视用
```

无需任何第三方套件，Python 3.9+ 即可。

---

## 更新绩效的完整流程

```
MT5 终端 → 历史 / 测试器 → 右键「报告」→ 存成 HTML
   ↓
python3 tools/mt5_report_to_json.py --label "2026 年至今" --apply caifu report.html
   ↓  （直接写回 performance.json；同 label 覆盖，不同 label 附加）
python3 tools/gen_perf.py
python3 tools/check_consistency.py
```

不加 `--apply` 则只印出 JSON 片段供人工检视。

`--apply` 会检查**报表的初始资金**与 `backtest_capital` 是否一致，不一致直接
挡下 —— 这两个对不上时报酬率与回撤都会算错。确认报表无误要换基准，
加 `--set-capital` 一并更新。

`mt5_report_to_json.py` 认得英文 / 简体 / 繁体三种 MT5 报表标签。
若你的报表是别的语言，在该档的 `LABELS` 补上对应标签即可。

**为什么走报表而不是从成交纪录重算**：MT5 报表里的「净值最大回撤 /
Equity Drawdown Maximal」本来就是含未平仓浮亏的口径，跟网站上
「最大净值回撤」的定义一致，直接取用不会有口径落差。自己从 deals 重算
反而会算成「已平仓回撤」，数字会漂亮很多但不诚实。

---

## 档案说明

| 档案 | 用途 |
|---|---|
| `data/performance.json` | 各 EA 各区间的绩效原始数字（唯一事实来源） |
| `perfdata.py` | 绩效推导逻辑（资金基准换算、防爆仓检查），三支脚本共用 |
| `data/risk-matrix.json` | 各 EA 的风控机制有无（目前尚未经原始码稽核） |
| `gen_perf.py` | 生成 7 支 EA 页面的 `#s1` 区块 + 首页卡片绩效块 |
| `gen_risk_matrix.py` | 生成风控矩阵到 `tools/out/`（内部用，不公开） |
| `check_consistency.py` | 跨页数字矛盾检查 |
| `mt5_report_to_json.py` | MT5 HTML 报表 → performance.json 片段（网站回测绩效用）|
| `tg_card.py` | 观摩账号报表 → 以**建议本金**为分母的绩效卡数字（TG 绩效卡用）|
| `mcp/` | 接 MT5 MCP（只读）的设定与界线 |
| `audit/RISK_AUDIT.md` | EA 原始码风控稽核流程与提示词 |
| `ea-repo-scaffold/bootstrap.sh` | 建立独立的 EA 原始码 repo 骨架 |

---

## TG 绩效卡

对外报的百分比，分母用**建议本金**，不是观摩账号自己的本金：

```
python3 tools/tg_card.py --slug caifu --label "2026 年至今" 观摩账号报表.html
python3 tools/tg_card.py --slug caifu --json 观摩账号报表.html   # 供程式消费
```

前提是观摩账号跑的手数即建议本金对应的手数（已确认），所以净利与浮亏
金额可直接换分母，不需再按手数比例缩放。

⚠ **报酬率与回撤必须共用同一个分母。** 只换报酬率不换回撤，绩效卡会
看起来比实际安全 —— 这是本工具把两者绑在一起算的原因。若换算后回撤
超过 100%，直接报错不输出。

---

## 三个资金栏位

```
backtest_capital     回测实际使用的起始资金。历史事实，不因文案而改。
recommended_capital  建议本金。网站 hero／首页卡片／资金建议表三处显示的数字，
                     也是对外报绩效百分比时该用的分母。
display_capital      选填。网站上用来计算报酬率与回撤的基准。
                     省略时等于 backtest_capital。
```

`recommended_capital` 是给外部消费的（TG 绩效卡、业务简报等）——建议本金
以前只散落在三处 HTML 里，没有单一来源可读。现在改这个栏位，
`check_consistency.py` 会检查三处显示值是否都跟上。

同样的手数下，净利、获利因子、笔数与资金无关；**报酬率与最大净值回撤
则会一起等比缩放**：

```
报酬率       = 净利 ÷ display_capital
最大净值回撤 = 回测浮亏金额 ÷ display_capital
```

把基准资金调小，报酬率变漂亮的同时回撤也会同比例放大 —— 不能只调一边。
若推导出的回撤超过 100%，`perfdata.py` 会直接报错（那个资金根本撑不过
这段历史，数字不该被印出来）。

---

## 生成器的两个约定

**报酬率一律推导，不手填。** `报酬率 = net_profit ÷ initial_capital`，
写在程式里只有一处，所以全站口径不可能飘。

**所有汇总值都先取「显示值」再往上加。** 累计报酬率 = 各区间显示报酬率之和，
长条图宽度依显示值等比缩放。这样读者看到的数字加起来会对得上 ——
若改用原始值汇总，表格里 133.4 + 265.7 会显示成 399.2 而不是 399.1，
看起来像算错。

---

## 已知待处理

`check_consistency.py` 目前会报出 8 项矛盾（首页卡片与 EA 页的「建议资金」
对不上、顺势之星内文的回撤与笔数与绩效表对不上）。这些是**文案决策**，
需要人来判断哪个数字才对，脚本刻意不自动修。修完之后这条指令应该要全绿。
