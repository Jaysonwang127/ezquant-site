---
name: youtube-transcript
description: 抓取 YouTube 影片字幕（可指定時間區段，例如 6:25–7:40），用於分析影片內容、仿寫行銷素材、摘要或翻譯。只要使用者貼 YouTube / youtu.be 連結並要「看這段影片」「這段在講什麼」「把這段仿造到我的素材」，就使用本技能。需要環境允許連線 youtube.com。
---

# youtube-transcript

把 YouTube 連結（或 11 碼影片 ID）轉成帶時間戳的字幕文字。支援時間區段裁切、語言優先序、JSON 輸出。

## 步驟

1. 確認套件已安裝（pypi 在受信任網路政策下也可連）：
   ```bash
   python3 -c "import youtube_transcript_api" 2>/dev/null || pip install -q youtube-transcript-api
   ```
2. 抓字幕。使用者給的時間點直接塞 `--start/--end`，前後各多抓 10–15 秒比較好抓上下文：
   ```bash
   python3 .claude/skills/youtube-transcript/scripts/fetch_transcript.py "<url>" --start 6:10 --end 7:55
   ```
   - 預設語言順序：`zh-Hant,zh-TW,zh-Hans,zh-CN,zh,en`；找不到會自動翻譯成第一順位。
   - 加 `--json` 可拿結構化資料（start/end/text）。
3. 讀完字幕後再做使用者真正要的事（拆解手法、對照現有素材、改稿）。字幕只是輸入，不要只貼字幕就結束。

## 失敗時怎麼辦

- **`YouTube blocked the request` / connection 錯誤**：這個遠端環境的網路政策擋住 youtube.com。請使用者到 claude.ai/code → Environments → 該環境的 Network access 改成 Full（或把 youtube.com 加入允許清單），然後**開新 session**（政策只在容器啟動時套用）。
- **`captions are disabled`**：影片沒字幕，請使用者從播放頁「顯示轉錄稿」貼文字，或描述內容。
- **只有自動字幕**：中文自動字幕錯字多，引用前先用上下文修正明顯錯誤，並向使用者說明是自動字幕。

## 產出慣例（仿造行銷素材時）

先給「該段用了什麼手法」的拆解（結構、鉤子、節奏、證據類型、CTA），再對照使用者現有素材說「套到哪裡、怎麼改」，最後才動手改檔。與本站口徑一致：不承諾收益、講數據不講截圖、回撤用最大淨值回撤。
