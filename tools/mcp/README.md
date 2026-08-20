# 接 MT5 MCP（只读）

目的：让 Claude Code / Codex 之类的 agent 能读取 MT5 的行情、账户历史与原始码，
用来 (a) 产出绩效数字、(b) 稽核 EA 原始码的风控机制。

**本专案只接只读用途。任何能开仓、平仓、改单的工具一律不开。**

---

## 一、两条路线

| 路线 | 适用 | 需求 |
|---|---|---|
| MT5 内建 MCP（build 6030 起，6060 完整） | 互动式：叫 agent 看图、解释帐户、debug MQL | 升级 MT5 到 6060+，在平台的 AI / MCP 设定中启用后，依平台给的端点接上 agent |
| 官方 `MetaTrader5` Python 套件 | 自动化：定期汇出绩效、批次统计 | Windows + Python 3.11+ + `pip install MetaTrader5` |

**建议两条都用，但分工不同**：数字走 Python（可重现、可进版控），
互动分析走内建 MCP（方便，但结果不直接进站）。

> 内建 MCP 的选单位置每个 build 都在动，请以你实际安装的版本为准，
> 不要照抄网路上的旧教学。

---

## 二、只读的界线（务必遵守）

接上去之前，先确认这三件事：

1. **用观摩帐号 / 只读投资人密码（investor password）连线，不要用主密码。**
   这是最硬的一道防线 —— 即使 agent 或设定出错，投资人密码在协定层就无法下单。
2. **MT5 里关闭「允许自动交易」**，再让 agent 连线。
3. **不要把任何 `place_order` / `modify_order` / `close_position` 类工具加进允许清单。**

## 三、Claude Code 设定

`mcp.readonly.example.json` 是范本。复制成 `.mcp.json` 放在你本机的工作目录
（**不要提交进这个 repo** —— 里面会有帐号资讯），把 `<...>` 换成实际值。

搭配 `settings.local.json` 的权限设定，把可用工具限制在只读那一组：

```json
{
  "permissions": {
    "allow": [
      "mcp__mt5__get_account_info",
      "mcp__mt5__get_symbol_info",
      "mcp__mt5__copy_rates",
      "mcp__mt5__history_deals_get",
      "mcp__mt5__history_orders_get",
      "mcp__mt5__positions_get"
    ],
    "deny": [
      "mcp__mt5__order_send",
      "mcp__mt5__order_check",
      "mcp__mt5__position_close",
      "mcp__mt5__position_modify"
    ]
  }
}
```

> 实际工具名称依你选用的 MCP server 而异，接上后先请 agent 列出可用工具，
> 再照抄名称填进上面两个清单。**deny 清单要先写好再连线**，不要等出事才补。

## 四、绩效数字的正式流程（不经过 agent）

数字进站走这条，不走 agent 口述 —— agent 会读错、会自己算，且不可重现：

```
MT5 终端 → 历史 / 测试器 → 右键「报告」→ 存成 HTML
   ↓
python3 tools/mt5_report_to_json.py --label "2026 年至今" report.html
   ↓  （输出的 JSON 片段贴进 tools/data/performance.json）
python3 tools/gen_perf.py          # 重新生成 7 支 EA 页面 + 首页卡片
python3 tools/check_consistency.py # 检查内文有没有跟新数字打架
```

agent 的角色是帮你**跑这几个指令、看懂报错、修文案**，而不是自己报数字。
