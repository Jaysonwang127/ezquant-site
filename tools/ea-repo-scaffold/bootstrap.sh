#!/usr/bin/env bash
# 建立 EA 原始码 repo 的骨架。
#
# 用法：
#   bash tools/ea-repo-scaffold/bootstrap.sh ~/ezquant-ea
#
# 产生的目录可直接 git init + push 成一个独立的 private repo。
# 刻意跟网站 repo 分开：网站是公开的（GitHub Pages），EA 原始码不是。
set -euo pipefail

DEST="${1:-}"
if [ -z "$DEST" ]; then
  echo "用法：bash $0 <目标目录>" >&2
  exit 1
fi
if [ -e "$DEST" ] && [ -n "$(ls -A "$DEST" 2>/dev/null)" ]; then
  echo "✗ $DEST 已存在且非空，请换一个空目录。" >&2
  exit 1
fi

# slug|中文名|平台|风险等级
EAS="
goldtripod|金鼎 GoldTripod|MT5|稳健
bailian|百炼成金|MT5|均衡
liangyi|两仪|MT5|均衡
jinshe|金蛇出洞|MT5|进取
h1trend|黄金罗盘|MT4+MT5|进取
shuangwei|黄金双卫|MT4+MT5|进取
caifu|顺势之星|MT4+MT5|进取
"

mkdir -p "$DEST"

cat > "$DEST/.gitignore" <<'EOF'
# ---- 编译产物：src/ 底下的编译结果不进版控 ----
ea/*/src/*.ex4
ea/*/src/*.ex5

# ---- 但 releases/ 底下的发行版二进位「要」进版控 ----
# 这是唯一能回答「这个客户跑的到底是哪一版」的方式，
# 所以不要把 releases/ 加进这里。
!ea/*/releases/**/*.ex4
!ea/*/releases/**/*.ex5

# ---- MetaEditor / 终端杂物 ----
*.bak
*.log
*.tmp
MQL4/Logs/
MQL5/Logs/

# ---- 绝对不能进版控的东西 ----
*.ini
.mcp.json
credentials*
*password*
accounts.*
EOF

cat > "$DEST/README.md" <<'EOF'
# EZQUANT EA 原始码

七支黄金 CFD 策略的原始码、参数档与发行纪录。

> **这是 private repo。** 网站（ezquant-site）是公开的，这个不是。
> 提交前先确认没有夹带帐号、密码或客户资料。

## 目录结构

```
ea/<slug>/
  src/                 MQL 原始码（.mq4 / .mq5）
  sets/                参数档（.set），一个情境一个档
  releases/<version>/  发行版：编译好的 .ex4/.ex5 + 当版 .set + RELEASE.md
  docs/                逻辑解析、开发笔记
  RISK.md              风控机制清单（对应网站的风控矩阵）
  CHANGELOG.md         这支 EA 的变更纪录
```

## 版本与发行

- Tag 格式：`<slug>-v<MAJOR>.<MINOR>.<PATCH>`，例如 `goldtripod-v2.3.1`
  - MAJOR：交易逻辑改变（客户需重新评估）
  - MINOR：新增参数或过滤条件，既有行为不变
  - PATCH：修 bug、改日志，不影响交易行为
- **每次交付给客户，都要先打 tag、建 `releases/<version>/`。**
  没有对应 tag 的二进位不准发出去 —— 出问题时无法回溯是这类产品最麻烦的状况。
- `releases/<version>/RELEASE.md` 至少要写：改了什么、附哪几个 `.set`、
  跟前一版的相容性、已知限制。

## 与网站的关系

网站上的绩效数字与风控矩阵由 `ezquant-site/tools/` 底下的脚本生成。
**这支 EA 的行为改了，记得同步更新网站的 `risk-matrix.json`**，
否则文案会跟程式码脱节 —— 详见 `ezquant-site/tools/audit/RISK_AUDIT.md`。
EOF

cat > "$DEST/CONTRIBUTING.md" <<'EOF'
# 开发约定

## 分支
- `main`：只放已发行的版本，永远可编译
- `dev/<slug>/<主题>`：单支 EA 的开发分支
- 合进 main 前必须：能编译、跑过回测、更新 CHANGELOG

## 提交讯息
```
<slug>: <动词开头的一句话>

例：
caifu: 加入逆势加仓层数硬上限（预设 12 层）
shuangwei: 修正点差过滤在跨日时段误判
```

## 改动交易逻辑时的检查清单
- [ ] 更新该 EA 的 `CHANGELOG.md`
- [ ] 更新 `RISK.md`（若风控机制有变）
- [ ] 跑回测，把报告放进 `releases/<version>/`
- [ ] 同步 `ezquant-site/tools/data/risk-matrix.json` 与产品页文案
- [ ] 若绩效数字要更新，走 `ezquant-site/tools/mt5_report_to_json.py` 的流程

## 参数档（.set）
- 命名：`<slug>-<情境>-<版本>.set`，例：`caifu-conservative-v1.4.0.set`
- 每个 `.set` 在 `sets/README.md` 里要有一行说明：适用资金、适用行情、风险取舍
- **不要**把客户专属的 `.set` 放在这里 —— 那属于客户资料
EOF

cat > "$DEST/CHANGELOG.md" <<'EOF'
# 变更纪录

各 EA 的详细变更请看 `ea/<slug>/CHANGELOG.md`，本档只记跨产品的共通事项。

## [未发行]
- 建立 repo 骨架
EOF

count=0
echo "$EAS" | while IFS='|' read -r slug name platform risk; do
  [ -z "$slug" ] && continue
  d="$DEST/ea/$slug"
  mkdir -p "$d/src" "$d/sets" "$d/releases" "$d/docs"

  cat > "$d/README.md" <<EOF
# $name（\`$slug\`）

| | |
|---|---|
| 品种 | XAUUSD |
| 平台 | $platform |
| 风险等级 | $risk |
| 产品页 | https://ezquant.example/ea/$slug.html |

## 目前发行版
_尚未建立第一个 tag。_

## 开发笔记
见 \`docs/\`。风控机制清单见 \`RISK.md\`。
EOF

  cat > "$d/RISK.md" <<EOF
# $name — 风控机制

对应网站风控矩阵的七个栏位。**每一项都要填「档名:行号」**，
只写「有」不算 —— 没有行号就无法验证。

| 机制 | 有 / 无 / 有条件 | 程式位置 | 说明 |
|---|---|---|---|
| 逆势加仓 | | | |
| 单笔硬止损 | | | |
| 层数硬上限 | | | |
| 整批 / 全局止损 | | | |
| 账户权益熔断 | | | |
| 点差过滤 | | | |
| 对冲 / 反手削单 | | | |

## 预设关闭的保护机制
（这一段最重要 —— 列出所有「程式里有、但预设不启用」的保护）

## 可被参数设成无上限的项目

## 稽核纪录
| 日期 | 版本 | 稽核人 | 结果 |
|---|---|---|---|
EOF

  cat > "$d/CHANGELOG.md" <<EOF
# $name 变更纪录

## [未发行]
- 移入版控
EOF

  cat > "$d/sets/README.md" <<EOF
# $name 参数档

| 档名 | 适用资金 | 适用行情 | 风险取舍 |
|---|---|---|---|
EOF

  cat > "$d/releases/README.md" <<EOF
# $name 发行版

每个发行版一个目录，目录名 = 版本号（如 \`v1.0.0\`），内含：

- 编译好的 \`.ex4\` / \`.ex5\`
- 该版随附的 \`.set\`
- \`RELEASE.md\`：改了什么、相容性、已知限制

发行前先打 tag：\`git tag $slug-v1.0.0\`
EOF

  touch "$d/docs/.gitkeep"
  count=$((count + 1))
done

echo "✓ 已在 $DEST 建立 EA repo 骨架"
echo
echo "下一步："
echo "  cd $DEST"
echo "  git init && git add -A && git commit -m 'chore: 建立 EA 原始码 repo 骨架'"
echo "  # 在 GitHub 开一个 private repo，然后："
echo "  git remote add origin <private repo url>"
echo "  git push -u origin main"
echo
echo "接着把各 EA 的 .mq4/.mq5 放进 ea/<slug>/src/，"
echo "现有的 .set 放进 ea/<slug>/sets/，然后为目前正在跑的版本打第一个 tag。"
