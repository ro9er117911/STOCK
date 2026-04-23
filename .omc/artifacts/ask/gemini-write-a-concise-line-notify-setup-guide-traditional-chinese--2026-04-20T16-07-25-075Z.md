# gemini advisor artifact

- Provider: gemini
- Exit code: 0
- Created at: 2026-04-20T16:07:25.077Z

## Original task

Write a concise LINE Notify setup guide (Traditional Chinese) for a personal stock alert bot. The system is ~/projects/STOCK with a quick-pulse monitoring script.

Cover:
1. 什麼是 LINE Notify（一句話）
2. 申請 LINE Notify token 的步驟（截圖可省略，文字描述即可）
3. 設定環境變數 LINE_NOTIFY_TOKEN
4. 測試指令（一行）
5. 啟用排程（launchctl load 指令）
6. 訊息範例（BUY/WAIT/PASS 各一行示意）

Keep it under 300 words. Output as clean Markdown.

## Final prompt

Write a concise LINE Notify setup guide (Traditional Chinese) for a personal stock alert bot. The system is ~/projects/STOCK with a quick-pulse monitoring script.

Cover:
1. 什麼是 LINE Notify（一句話）
2. 申請 LINE Notify token 的步驟（截圖可省略，文字描述即可）
3. 設定環境變數 LINE_NOTIFY_TOKEN
4. 測試指令（一行）
5. 啟用排程（launchctl load 指令）
6. 訊息範例（BUY/WAIT/PASS 各一行示意）

Keep it under 300 words. Output as clean Markdown.

## Raw output

```text
# LINE Notify 股市警示設定指南

### 1. 什麼是 LINE Notify？
免費的 LINE 官方推送服務，可將系統自動化訊息直接傳送到個人或群組對話框。

### 2. 申請 Token 步驟
1. 登入 [LINE Notify 官網](https://notify-bot.line.me/)。
2. 進入「個人頁面」，點擊「發行權杖 (Generate token)」。
3. 輸入權杖名稱（如：`StockAlert`）並選擇接收通知的聊天室。
4. 點擊「發行」並**複製 Token**（關閉視窗後將無法再次查看）。

### 3. 設定環境變數
在終端機執行以下指令（或加入 `~/.zshrc`）：
```bash
export LINE_NOTIFY_TOKEN="您的_TOKEN_內容"
```

### 4. 測試連線
執行一行指令確認發送功能：
```bash
curl -X POST -H "Authorization: Bearer $LINE_NOTIFY_TOKEN" -F "message=Stock Bot 測試連線成功！" https://notify-bot.line.me/api/notify
```

### 5. 啟用自動化排程
載入項目中的 `launchd` 配置以啟動 Quick-Pulse 監控：
```bash
launchctl load ~/projects/STOCK/launchd/com.ro9air.stock-research.quick-pulse.plist
```

### 6. 訊息範例
* 🟢 **[BUY]** TSMC (2330): $1,050 - 趨勢轉強，滿足買入信號。
* 🟡 **[WAIT]** MSFT: $420 - 接近壓力區，建議觀望回測。
* 🔴 **[PASS]** PLTR: $35 - 動能轉弱，目前不建議進場。


YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.

```

## Concise summary

Provider completed successfully. Review the raw output for details.

## Action items

- Review the response and extract decisions you want to apply.
- Capture follow-up implementation tasks if needed.
