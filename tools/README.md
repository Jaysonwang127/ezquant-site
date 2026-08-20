# tools —— 网站数字的单一事实来源

这个目录把原本靠人工维护的两件事自动化：

1. **绩效数字** —— 7 支 EA 页面 + 首页卡片的绩效区块，全部由 `data/performance.json` 生成
2. **风控矩阵** —— 跨产品的风控机制对照页，由 `data/risk-matrix.json` 生成

改数字请改 JSON，**不要手改 HTML**，否则下次生成会被覆盖。

---

## 常用指令

```bash
# 提交前跑这三条（CI 也跑同样的）
python3 tools/gen_perf.py --check          # 页面绩效是否与 JSON 一致
python3 tools/gen_risk_matrix.py --check   # 风控矩阵页是否与 JSON 一致
python3 tools/check_consistency.py         # 跨页数字有没有互相矛盾

# 改完 JSON 之后重新生成
python3 tools/gen_perf.py
python3 tools/gen_risk_matrix.py
```

无需任何第三方套件，Python 3.9+ 即可。

---

## 更新绩效的完整流程

```
MT5 终端 → 历史 / 测试器 → 右键「报告」→ 存成 HTML
   ↓
python3 tools/mt5_report_to_json.py --label "2026 年至今" report.html
   ↓  把输出的 JSON 片段贴进 tools/data/performance.json 的 periods
python3 tools/gen_perf.py
python3 tools/check_consistency.py
```

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
| `data/risk-matrix.json` | 各 EA 的风控机制有无（目前尚未经原始码稽核） |
| `gen_perf.py` | 生成 7 支 EA 页面的 `#s1` 区块 + 首页卡片绩效块 |
| `gen_risk_matrix.py` | 生成 `ea/risk-matrix.html` |
| `check_consistency.py` | 跨页数字矛盾检查 |
| `mt5_report_to_json.py` | MT5 HTML 报表 → performance.json 片段 |
| `mcp/` | 接 MT5 MCP（只读）的设定与界线 |
| `audit/RISK_AUDIT.md` | EA 原始码风控稽核流程与提示词 |
| `ea-repo-scaffold/bootstrap.sh` | 建立独立的 EA 原始码 repo 骨架 |

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
