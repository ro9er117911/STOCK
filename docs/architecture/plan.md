# 股票分析系統 v2 規劃：語氣後處理、來源白名單、通知與 Dashboard

## Summary
- 先把研究產出的語氣校正補上：新增一層 deterministic post-processing，專門把「狀態沒變、只是信心提高」這類機械句改寫成真正像研究筆記的語氣，避免 LLM 摘要看起來像欄位 diff。
- 系統結構要從「pipeline 直接生成多種輸出」整理成「單一 canonical summary -> 多個 delivery surfaces」：PR、email、dashboard 都從同一份標準化摘要生成，避免目前同一資訊在 `current.md`、`review_summary.md`、`pr-body.md`、zh-TW 翻譯之間重複漂移。
- 事件來源改成正式白名單設定，不再讓 `stock_research/config.py` 的 `WATCHLIST` 同時扮演 ticker 設定、來源定義、門檻配置三個角色。
- Dashboard 第一版採 `zh-TW first`、`summary-first`，內容聚焦「現在狀態 / 下一步 / 關鍵動作 / 關鍵事件」，不公開完整研究全文。
- Email 第一版只在 material refresh PR 建立或更新時寄送，樣式走「精簡、優雅、專業、舒適」，並附 dashboard 連結。

## Key Changes
- 資料與流程分層
  - 新增單一 `research digest` 輸出層，從 `state.json + events.jsonl + review_summary.json` 產生每檔標準化摘要。
  - PR body、zh-TW email、dashboard JSON/HTML 全部改吃這個 digest，不再各自拼接內容。
  - `automation/run/*.json` 裡目前混有暫存路徑與 delivery 專用資料，會整理成明確的 run artifact 結構，避免後續 surfaces 直接耦合臨時檔案位置。

- 事件來源白名單
  - 把 ticker universe、來源白名單、門檻設定拆開，建立單一來源真實檔案，例如 `research/system/source_registry.json` 或等價結構。
  - 白名單至少明確列出：`ticker`、`source_id`、`source_type`、`url`、`status(active|disabled)`、`title_keywords`、`allow_patterns`、`priority`、`notes`。
  - `WATCHLIST` 只保留程式執行所需的最小 runtime config；來源與白名單改由 registry 載入，並在 repo 內產出一份人類可讀的來源清單。
  - pipeline summary 要加上「本次實際輪詢了哪些來源、哪些來源失敗、哪些被跳過」的可見輸出，讓你能直接看懂 input 來源。

- 語氣後處理與研究文案品質
  - 在 refresh 完成後、翻譯前新增 `post_process_research_language()` 類型步驟。
  - 這層只處理語氣，不改 thesis 事實：把 `reinforced -> reinforced`、`watch -> watch but confidence +0.08` 這類訊號轉成研究語言，例如「核心假設維持成立，但信心上修，因為...」。
  - 也順手標準化 review summary、assumption change、action delta 的語氣規則，避免不同模型輸出風格差異太大。
  - 這層應該 deterministic 優先；必要時才補小模型潤稿，但不能改變結構化 state。

- 輸出面整理：PR / Email / Dashboard
  - PR 仍保留，但改成 canonical digest 的一個 render target。
  - 新增 email render target：只在 material refresh PR 建立或更新時寄送，不在每次 polling 時寄。
  - Email 內容固定為：總結一句、每檔 3-4 行重點、目前操作、下一次要確認的資料、dashboard 連結、PR 連結。
  - 寄送方案採 `Resend`；新增必要 secrets 與簡單 HTML/text 雙格式模板。
  - 新增靜態 dashboard build 流程：首頁顯示 portfolio cards，個股 detail 頁顯示狀態、關鍵事件、關鍵動作、下次檢查、最新摘要。
  - Dashboard 第一版採 `summary-first`，不直接公開完整 `current.md`；完整研究仍留在 private repo / PR。
  - Dashboard 只顯示 merged `main` 的正式狀態；PR preview 繼續留在 GitHub PR，不讓未審稿內容直接進對外頁面。
  - 目前先以 `private repo first` rollout：先在本 repo 內生成可部署 site artifact 與 Pages-ready 結構；是否公開發佈作為第二階段開關。

- 系統化與冗餘清理
  - 移除或降級 `research/system/watchlist.json` 這類非真實來源檔案，避免 README 寫一套、runtime 用另一套。
  - 讓 `review_summary.json` 成為正式 machine-readable refresh artifact；`review_summary.md`、`pr-body.md`、email、dashboard 都由它衍生。
  - 清掉 `automation/run` 中帶本機暫存絕對路徑的輸出，改成 repo-relative 或 purely logical references。
  - 把 workflow 拆成較清楚的階段：`poll`、`refresh+post-process`、`render surfaces`、`notify/deploy`。
  - 補一份 operator-facing 文檔，直接回答：
    - 事件來源 input 在哪裡
    - 最終輸出有哪些
    - 哪些是正式輸出、哪些只是中間 artifact
    - dashboard / email / PR 各自代表什麼狀態

## Public Interfaces / Types
- 新增 canonical digest 介面
  - 每檔至少包含：`ticker`、`status_label`、`current_action`、`thesis_confidence`、`summary_blurb`、`next_review_at`、`next_must_check_data`、`key_events[]`、`key_action_rules[]`、`changed_assumptions[]`、`source_status[]`
- 新增來源白名單介面
  - 每筆來源至少包含：`ticker`、`source_id`、`source_type`、`url`、`status`、`priority`、`title_keywords[]`、`allow_patterns[]`、`notes`
- 新增通知 payload
  - 至少包含：`run_type`、`material_tickers[]`、`dashboard_url`、`pr_url`、`digest_cards[]`
- 新增 dashboard data layer
  - `portfolio.json`：首頁卡片資料
  - `tickers/<ticker>.json`：個股 detail 資料
  - HTML 頁面只讀這些 JSON，不直接 parse markdown

## Test Plan
- 語氣後處理
  - `status` 未變但 `confidence` 上升時，輸出語氣應改成「維持成立但信心提高」，不能再出現機械式 `reinforced -> reinforced`
  - `status` 真的變化時，仍保留明確升降語意，不被柔化掉

- 來源白名單
  - pipeline 只會輪詢 registry 裡 `active` 的來源
  - registry 缺漏或關閉來源時，run summary 能明確反映被跳過/停用
  - README / operator doc / runtime config 三者對來源清單一致

- Digest 與多輸出一致性
  - PR、email、dashboard 對同一 ticker 的 `current_action / next_review_at / key events` 必須一致
  - dashboard 與 email 不能直接依賴 markdown parsing 才拿到核心欄位
  - `automation/run` 不再產出帶本機 temp path 的正式輸出

- Email
  - 只有 material PR create/update 時才寄送
  - 內容精簡，包含 dashboard 連結與 PR 連結
  - 無 material update 時不寄摘要信
  - 寄送失敗時 workflow 要可見告警，但不應回寫錯誤內容到研究檔

- Dashboard
  - 能從 `main` 生成 portfolio 首頁與 ticker detail 頁
  - 顯示欄位至少包含：現在狀態、後續動作、關鍵動作規則、關鍵事件、下一次檢查
  - 第一版不公開完整研究全文
  - site data 只反映 merged state，不顯示未合併 PR preview

## Assumptions
- `zh-TW first`：對外頁面與 email 以繁中為主，ticker / 專有名詞保留英文。
- `summary-first`：公開 surface 不公開完整 thesis 正文，只顯示操作與決策摘要。
- Email 方案採 `Resend`。
- Email 只在 material refresh PR 建立或更新時寄送。
- Dashboard 先以 `private repo first` 方式實作成 Pages-ready artifact；公開發佈作為下一階段開關。
- `review_summary.json` 將升格為正式 canonical refresh artifact；其餘文字輸出都應從它或 digest 衍生。
