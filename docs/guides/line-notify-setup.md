# LINE Messaging API 建置指南 — Quick Pulse 股票警報

> 版本：Phase 3.1 | 更新：2026-04-21

## 驗證結論

LINE Notify 已於 2025-03-31 結束服務，Quick Pulse 不應再使用舊的 `LINE_NOTIFY_TOKEN` / `notify-api.line.me` 流程。新版要走 LINE Official Account 的 Messaging API。

你手上的兩個值要放在本機環境變數，不是貼到 LINE 官方帳號的 AI 聊天機器人頁面：

| 你拿到的值 | 貼到哪裡 | 用途 |
|---|---|---|
| Channel ID | `LINE_CHANNEL_ID` | 用來向 LINE 換短效 channel access token |
| Channel secret | `LINE_CHANNEL_SECRET` | 用來向 LINE 換短效 channel access token |

一對一推播還需要第三個值：

| 還需要的值 | 貼到哪裡 | 用途 |
|---|---|---|
| Your user ID / userId | `LINE_MESSAGING_TARGET_ID` | 指定 Quick Pulse 要推送給哪個 LINE 使用者 |

`Channel ID` / `Channel secret` 本身不能直接發訊息。Messaging API 發訊息實際使用的是 `Authorization: Bearer {channel access token}`，而本專案可用 `LINE_CHANNEL_ID` + `LINE_CHANNEL_SECRET` 自動換 15 分鐘短效 token。

## 官方後台要在哪裡看這些值

### Channel ID

1. 開啟 LINE Official Account Manager: <https://manager.line.biz/>
2. 選擇你的官方帳號
3. 右上角進入「設定」
4. 側邊欄點「Messaging API」
5. 在 Channel Info 旁可看到 Channel ID

也可以從 LINE Developers Console 查看：

1. 開啟 <https://developers.line.biz/console/>
2. 選 provider
3. 選 Messaging API channel
4. 在「Basic settings」看 Channel ID

### Channel secret

1. 開啟 <https://developers.line.biz/console/>
2. 選 provider
3. 選 Messaging API channel
4. 在「Basic settings」找到 Channel secret

Channel secret 主要也是 webhook 簽章驗證用的密鑰；若外洩要重新發行。

### Your user ID

1. 開啟 <https://developers.line.biz/console/>
2. 選同一個 provider / Messaging API channel
3. 到「Basic settings」
4. 找「Your user ID」
5. 把官方帳號加為好友，否則 push message 可能送不到

如果看不到 Your user ID，通常是 Business ID 還沒連結你的 LINE 帳號。

## 步驟 1：啟用 Messaging API

1. 到 LINE Official Account Manager: <https://manager.line.biz/>
2. 選官方帳號
3. 「設定」->「Messaging API」
4. 啟用 Messaging API
5. 選 provider 後，LINE Developers Console 會出現 Messaging API channel

注意：現在不能直接在 LINE Developers Console 新建 Messaging API channel；官方流程是先建立 / 選擇 LINE 官方帳號，再啟用 Messaging API。

## 步驟 2：設定本機環境變數

推薦：貼 `Channel ID` / `Channel secret` 到本機私密檔 `~/.stock-quick-pulse.env`，讓程式自動換短效 token。排程腳本會讀這個檔案；不要把這些值寫進 repo。

```bash
# 建立本機私密設定檔
touch ~/.stock-quick-pulse.env
chmod 600 ~/.stock-quick-pulse.env

# 編輯 ~/.stock-quick-pulse.env，填入：
export LINE_CHANNEL_ID="你的_Channel_ID"
export LINE_CHANNEL_SECRET="你的_Channel_secret"
export LINE_MESSAGING_TARGET_ID="你的_Your_user_ID"

# 手動測試前先載入
source ~/.stock-quick-pulse.env
```

可選：如果你在 LINE Developers Console 的 Messaging API tab 產生了 long-lived channel access token，也可以直接貼 token：

```bash
# 寫在 ~/.stock-quick-pulse.env
export LINE_CHANNEL_ACCESS_TOKEN="你的_long_lived_channel_access_token"
export LINE_MESSAGING_TARGET_ID="你的_Your_user_ID"
```

若同時有 `LINE_CHANNEL_ACCESS_TOKEN` 和 `LINE_CHANNEL_ID` / `LINE_CHANNEL_SECRET`，程式會優先使用 `LINE_CHANNEL_ACCESS_TOKEN`。

## 步驟 3：快速驗證 Channel ID / secret

這一步只確認 `Channel ID` + `Channel secret` 能換 token，還不會發 LINE 訊息。

```bash
curl -sS -X POST https://api.line.me/oauth2/v3/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=$LINE_CHANNEL_ID" \
  --data-urlencode "client_secret=$LINE_CHANNEL_SECRET"
```

成功時會回傳類似：

```json
{
  "token_type": "Bearer",
  "access_token": "...",
  "expires_in": 900
}
```

## 步驟 4：完整推播測試

```bash
cd ~/projects/STOCK

# 先跑一次 quick-decision 產生資料
python3 -m src.stock_research quick-decision \
  --ticker 2330 \
  --trigger-description "測試推播" \
  --no-prompt

# 發送 LINE Messaging API 通知
python3 -m src.stock_research.notify_line \
  --verdict-file automation/run/quick-decision.json
```

成功時會顯示：

```text
LINE Messaging API sent OK
```

## 步驟 5：啟用每日自動排程

```bash
# 安裝 launchd（台股開盤前 09:00 TWD / 01:00 UTC 自動跑）
launchctl load ~/projects/STOCK/launchd/com.ro9air.stock-research.quick-pulse.plist

# 確認已載入
launchctl list | grep quick-pulse

# 停用
launchctl unload ~/projects/STOCK/launchd/com.ro9air.stock-research.quick-pulse.plist
```

## 🚀 測試指南：如何讓團隊或好友一起接收推播？

當 Quick Pulse 成功在你的本機運行後，你可能會想邀請其他人一起測試接收股票警報。由於我們已從淘汰的 Notify 升級為企業級的 **Messaging API**，目前的腳本預設是推送給你個人的 `TARGET_ID`。

若要開放其他人進入測試環境，請遵循以下優雅的部署流程：

### 1. 邀請加入官方帳號 (Add as Friend)
這是一切的交互起點。請對方掃描你的 LINE 官方帳號 QR Code，或是搜尋你的 Basic ID（開頭包含 `@`），並將虛擬助理**加入好友**。
> ⚠️ **重要安全機制**：基於反垃圾訊息 (Anti-Spam) 協定，使用者必須主動將官方帳號加為好友且未封鎖，API server 才能成功突破防線，將訊息推送到對方設備。

### 2. 選擇發送策略 (Routing Strategy)

為了在開發期快速驗證，或者在正式上線時精準投放，你可以選擇以下兩種廣播架構：

#### 📡 模式 A：全體廣播（Broadcast）— 適合快速公測
最簡單暴力的測試法，一呼百應。
- **作法**：在環境變數檔 `~/.stock-quick-pulse.env` 中掛載開關 `export LINE_MESSAGING_BROADCAST=true`。
- **效果**：執行推播指令時，只要池子裡有加這隻機器人為好友的用戶，**全部都會在毫秒等級收到最新報價警報**。
- **維運提醒**：廣播就像無差別雷達波，會消耗 LINE 官方帳號的免費 API Quota（每月 500 則上限）。建議僅在跑通開發流程或遭遇重大市場訊號時啟動，以保持極致的專業度與神祕感。

#### 🎯 模式 B：精準狙擊（Target Push）— 適合 VIP 營運
身為專業的量化交易輔助系統，我們更多時候只需要將特定訊號推送給特定的決策者。
- **作法**：你需要精準擷取對方的 **LINE User ID**（一串 `U` 開頭的唯一識別碼，絕對 **不是** 使用者日常加好友的 LINE ID 名稱）。
- **如何取得**：最優雅且駭客感十足的方式是部署一個輕量化的 Webhook 監聽器。當使用者對機器人發送「打開通知」時，你的節點中介軟體便默默攔截並解碼該事件附帶的 `userId`。若想避開伺服器架設成本，亦可請對方利用網路上開源的「User ID 取測器」回傳識別碼。
- **效果**：你可以自由編排 `TARGET_ID` 的清單陣列，輕鬆實現「僅向持股法說會會員發送」或「暗池異動高階訂閱」的差異化推播矩陣。

---

## 💎 進階美學：升級為 Flex Message (專業版型介面)

目前的推播使用的是最底層的 Text Message（純文字傳輸），視覺效果略顯枯燥單調。

**真正的金融科技，必須在第一張圖就震懾眼球。**

利用 LINE 官方提供的 **Flex Message**，我們可以直接套用類似網頁開發中 [CSS Flexbox](https://www.w3.org/TR/css-flexbox-1/) 的排版邏輯，包含 `box`, `layout`, `direction` 與動態比例間距。這代表你可以捨棄單調文字，打造成如同 Bloomberg 終端機般極具科技感、甚至支援深色模式的專業卡片介面。

想像未來的推送：漸層的標題區塊、根據強弱動態變化紅綠漲跌色帶、精算過留白的次級資訊分隔線，底部甚至掛載「查看 TradingView 圖表」的快速互動按鈕。

### Flex Message 實戰結構
以下是將 Quick Pulse 訊號轉換為嚴謹專業卡片的微縮 JSON 載體範例：

```json
{
  "type": "flex",
  "altText": "QUICK PULSE | 最新交易訊號：2330",
  "contents": {
    "type": "bubble",
    "size": "kilo",
    "header": {
      "type": "box",
      "layout": "vertical",
      "backgroundColor": "#1A1A1A",
      "paddingAll": "16px",
      "contents": [
        {
          "type": "text",
          "text": "QUICK PULSE SIGNAL",
          "color": "#00FF9D",
          "weight": "bold",
          "size": "xs",
          "letterSpacing": "2px"
        }
      ]
    },
    "body": {
      "type": "box",
      "layout": "vertical",
      "paddingAll": "20px",
      "contents": [
        {
          "type": "text",
          "text": "🟡 WAIT | 2330",
          "weight": "bold",
          "size": "xl",
          "color": "#333333"
        },
        {
          "type": "separator",
          "margin": "lg",
          "color": "#EEEEEE"
        },
        {
          "type": "text",
          "text": "• ADR premium 12.23%\n• RSI neutral, wait for cleaner entry",
          "wrap": true,
          "color": "#666666",
          "size": "sm",
          "margin": "lg",
          "lineSpacing": "6px"
        }
      ]
    },
    "footer": {
      "type": "box",
      "layout": "horizontal",
      "contents": [
        {
          "type": "text",
          "text": "▍ Confidence Level: 62%",
          "size": "xs",
          "color": "#999999",
          "weight": "bold"
        }
      ]
    }
  }
}
```

*🔥 架構師提示：你可以使用 [LINE Flex Message Simulator](https://developers.line.biz/flex-simulator/) 以所見即所得 (WYSIWYG) 的方式拖曳設計你的動態卡片，完成後將 JSON 匯出並套疊入 Python `notify_line.py` 的 payload 原型中，一次性為你的服務披上專業旗艦的外衣！*

---

## 🚦 資安紅線與踩坑指南

- **控制台迷航**：LINE 官方 AI 聊天機器人（β）介面 **完全不是** 掛載 `Channel ID` / `Channel secret` API 密鑰的地方（那是給運營人員設 FAQ 用的）。請確保你在 Developer Console 進行操作。
- **零信任基礎 (Zero-Trust)**：`Channel ID` / `Channel secret` 等同於你系統的出金密碼，強烈規範只能存放在 `.env`、本機 shell profile 或雲端密鑰庫中，**絕對嚴禁** Commit 進入 Git 儲存庫。
- **幽靈發送假象**：若你的 Python 執行日誌印出 `LINE Messaging API sent OK` (HTTP Status 200)，但目標終端沒收到推播，99.9% 是因為該受眾群體「尚未將官方帳號解除封鎖 / 加為好友」。API 仍然會回報成功，但封包會在最後一哩路被系統捨棄。

## 📚 延伸閱讀與核心技術指南

- [CSS Flexbox 空間佈局模型（W3C）](https://www.w3.org/TR/css-flexbox-1/)  - 掌握 Flex Message 版面的靈魂核心。
- [LINE Messaging API：Sending Flex Messages (Hello World)](https://developers.line.biz/en/docs/messaging-api/using-flex-messages/#sending-hello-world) - 官方 JSON 注入實作演練。
- [IT 邦幫忙：LINE Bot 開發心法實戰](https://ithelp.ithome.com.tw/articles/10229584) - 中文開發生態系的整合心法參考。
- [LINE Notify 結束服務官方公告（時代眼淚）](https://notify-bot.line.me/zh_TW/)
