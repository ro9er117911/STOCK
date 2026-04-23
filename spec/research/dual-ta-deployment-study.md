# 雙 TA 網頁應用部署方案研究

## Executive Summary

結論先講：這個專案最適合走 `雙軌產品`，並以 `Vercel 部署公開輕量產品`、`私有研究工作台維持 local-first` 作為 v1 預設路線；若未來真的要加入登入、雲端同步、背景任務與資料持久化，再把 Python API / jobs 拆到 `Railway` 或 `Render`，而不是一開始就把整套系統硬塞成單一 full-stack SaaS。

這個判斷不是抽象偏好，而是來自目前 repo 的實際形狀：

- 目前核心是 `Python research engine + generated static site + local cockpit API`。
- 公開輸出已經清楚對應到 `/Users/ro9air/projects/STOCK/site`。
- 私有研究模式已經清楚對應到 `/Users/ro9air/projects/STOCK/automation/run/dashboard-local`、`/Users/ro9air/projects/STOCK/research/system/portfolio.private.json`，以及本機 `127.0.0.1:8001` 的 cockpit API。

因此，對你目前的需求來說，最好的策略不是「把現有研究系統重寫成一個萬能網站」，而是：

1. 把公開面產品化，服務一般使用者。
2. 保留研究者工作台的深度、私密性與本機寫回能力。
3. 等一般用戶需求被驗證後，再決定是否引入雲端 backend。

---

## Two TA Personas

### Persona A: 深入研究者 TA

這個 TA 就是你自己。核心不是「看幾個訊號就下判斷」，而是建立、維護、修正 thesis，並讓研究流程可持續迭代。

**目標**

- 追蹤少數持股或高優先觀察名單，做深度研究而不是大範圍掃描。
- 把 thesis、風險、觀察事件、部位與行動規則放進同一個研究系統。
- 保留 private positions、成本、部位權重與風險規則，不外流到公開站。
- 讓研究更新、digest、dashboard、observation workflow 可以持續寫回。

**關鍵任務**

- 維護每檔股票的 `current.md`、`state.json`、events 與 artifacts。
- 用本機 dashboard 檢查 portfolio totals、macro regime、risk alerts、factor analysis。
- 透過 local API 更新 observation lake 與研究候選流程。
- 用私有部位檔做成本、倉位、風險閾值與 sizing 決策。

**功能期待**

- 完整 thesis 結構與 evidence chain。
- 私有部位、成本、target/max weight、risk policy。
- observation workflow 與 local writeback。
- 可從 Python pipeline 直接產生 site / local dashboard。
- sanitized public output 與 private overlay 明確分離。

**痛點**

- 一般 consumer app 的資訊密度太低，不足以支持深度研究。
- 若把私有研究與公開產品混在一起，權限、資料分層與部署複雜度會急速上升。
- 若過早上雲，會把大量時間花在 auth、DB、multi-tenant、同步與資料邊界管理，而不是研究能力本身。

**複雜度容忍度**

- 高。可以接受多層資訊架構、複雜 workflow 與本機工具鏈。

**信任 / 隱私要求**

- 高。部位、成本、個人研究脈絡、觀察紀錄不應預設進入公開雲端。

**成功標準**

- 能快速更新 thesis，並在本機看到完整的 private cockpit。
- 公開站可以對外展示研究成果，但不暴露 private overlay。
- 研究流程維持高密度、高可控、可寫回，而不是退化成內容展示頁。

**為什麼目前 repo 已經很適合這個 TA**

- `src/stock_research/dashboard.py` 已經區分 public site 與 local dashboard bundle。
- `src/stock_research/cockpit_api.py` 已經提供本機寫回 API。
- `research/system/portfolio.private.json` 與 `risk_policy.json` 已經在模型上支持 private overlay。

### Persona B: 一般使用者 TA

這個 TA 不是要成為 buy-side analyst，而是想要一套「好理解、能上手、能客製」的投資框架工具。

**目標**

- 快速得到一個可操作的投資框架，而不是讀完整 thesis。
- 使用通用策略或自定投資風格，例如：
  - 巴菲特型
  - 題材 / 敘事型
  - 因子型
  - 穩健 ETF / 長期配置型
- 用簡化界面理解某檔股票「能不能看、該看什麼、目前屬於哪種型態」。

**關鍵任務**

- 選擇或建立自己的投資框架。
- 看到簡化後的個股研究卡與策略建議。
- 理解買進條件、風險提醒、適用持有期。
- 用少量輸入得到可持續使用的 watchlist 與研究視圖。

**功能期待**

- `通用策略` 模板庫。
- `客製化投資框架` 建立器。
- 簡化後的研究頁與摘要卡。
- 清楚的 onboarding 與預設範本。
- sanitized data，不要求私有部位或本機 API。

**痛點**

- 現有 repo 對這類使用者來說資訊密度過高、概念太多、學習門檻偏高。
- 若直接暴露 thesis state、observation lake、portfolio private overlay，使用者會不知從何開始。
- 太像研究作業系統，而不像「上手快、可訂製」的產品。

**複雜度容忍度**

- 中低。可以接受一點設定，但不接受研究操作系統級別的流程。

**信任 / 隱私要求**

- 中。願意保存自己的策略偏好，但不一定要上傳完整交易成本、持股明細或研究筆記。

**願意付出的學習 / 使用成本**

- 願意花時間設定框架，但不想學一套 analyst workflow。
- 更適合 template-driven、guided flow，而不是 expert-first UI。

**成功標準**

- 10 至 20 分鐘內能建立自己的框架。
- 能看懂一檔股票屬於哪種投資語境。
- 能持續回來用，而不是第一次進站就被複雜度勸退。

**為什麼目前 repo 對這個 TA 顯得過重**

- 目前產品語言偏向研究 OS，而非 beginner-facing product。
- 目前的 public site 雖然已是靜態輸出，但資訊架構仍帶有研究者視角。
- 一般使用者真正需要的是「簡化殼層 + 框架配置器 + 乾淨摘要視圖」，不是完整研究後台。

---

## Deployment Options Comparison

### 先講判斷原則

評估部署方案時，這裡不是在問「哪個平台最強」，而是在問：

- 哪個平台最適合目前的 repo 形狀。
- 哪個平台最方便把 `/site` 產品化。
- 哪個平台最少引入不必要的 backend 負擔。
- 哪個平台保留未來擴張餘地，但不把 v1 變複雜。

### 比較矩陣

| 平台 | Static hosting fit | Preview workflow | Custom domain ease | Python / background job fit | Private mode fit | Cost predictability | Future auth / DB extensibility | Operational burden | 評語 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Vercel** | 很高 | 很高 | 高 | 中 | 低 | 中高 | 中 | **低** | 最適合先把 public `site/` 上線 |
| **Cloudflare Workers / Pages** | 很高 | 中高 | 中高 | 中 | 低 | 高 | 中高 | 中 | 很強，但比你現在需要的多一點平台形狀決策 |
| **Netlify** | 高 | 高 | 高 | 中 | 低 | 中 | 中 | 中低 | 穩定好用，但對這個 repo 不比 Vercel 更簡單 |
| **Render** | 中高 | 中 | 高 | **高** | 中 | 中 | **高** | 中高 | 適合未來 Python API / worker 真的成型之後 |
| **Railway** | 中 | 中 | 中高 | **高** | 中 | 中 | **高** | 中 | 很適合 app/backend 成形後，但不是 public-static-first 的最省事起點 |

### 各平台分析

#### 1. Vercel

**適合你的原因**

- 你現在最需要部署的是已生成的靜態 public surface，而不是一個需要大量 server logic 的系統。
- Vercel 對 Git-based deployment 與 preview flow 很成熟，適合快速迭代 public app。
- Preview deployment 對未來做 beginner-facing IA 調整很方便，能快速看 branch 版本。
- 如果之後需要少量 server function，Vercel Functions 也能先補，但不必一開始就以 backend 為中心設計。

**限制**

- 它不是最自然的 Python research backend / long-running jobs 平台。
- Vercel Cron 在 Hobby 有明顯限制，不適合把重度排程工作直接當核心基礎設施。

**適合的定位**

- `Public lightweight product` 的首選。
- 不適合作為 private researcher workstation 的雲端替代。

**官方依據**

- Vercel 支援 Git-based deployments 與多種 Git provider：[Deploying Git Repositories with Vercel](https://vercel.com/docs/deployments/git)
- Vercel 的 Preview Environment 會在非 production branch、PR 或 CLI 非 `-prod` 部署時建立 preview：[Environments](https://vercel.com/docs/deployments/custom-environments)
- Vercel Functions 支援多種 runtime，文件列出 `Node.js`、`Python` 等 runtime 類型：[Vercel Functions](https://vercel.com/docs/functions/)
- Cron jobs 可用於所有 plans，但 Hobby 只允許每天一次，且準時性有限：[Usage & Pricing for Cron Jobs](https://vercel.com/docs/cron-jobs/usage-and-pricing)

#### 2. Cloudflare Workers / Pages

**適合你的原因**

- 靜態資產與邏輯可以一起部署，對全球分發與 caching 很強。
- 若未來你想把 public app 做成「static + edge logic + lightweight personalization」，Cloudflare 很有吸引力。
- Cron Triggers、KV、D1、Durable Objects 等生態對之後擴展有彈性。

**限制**

- 對現在這個 repo 而言，Cloudflare 的平台組件雖然強，但你還沒需要那麼多原生平台原語。
- 相對 Vercel，進場時你會更早碰到 Worker / assets / bindings / route shape 的設計決策。

**適合的定位**

- `Strong second`。
- 如果你特別在意全球邊緣網路與 price/perf，它很有吸引力。
- 但以「最省事」為優先時，我仍排在 Vercel 之後。

**官方依據**

- Cloudflare 可在單次部署中一起部署 Worker code 與 static assets：[Static Assets](https://developers.cloudflare.com/workers/static-assets/)
- Cron Triggers 可以用 `scheduled()` handler 跑定時任務，也可結合 Workflows：[Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
- Workers 提供 Free plan 與 Paid plan，pricing 文件明確列出不同資源限制：[Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- Custom Domains 可由 Cloudflare 建立 DNS records 與 certificates：[Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)

#### 3. Netlify

**適合你的原因**

- 也是成熟的靜態站與 preview 工作流平台。
- 對 marketing-style site、preview review 與 branch/deploy preview 也很好用。
- 若你希望 public site 偏內容與協作 review，Netlify 的 DX 很穩。

**限制**

- 對這個 repo 來說，Netlify 沒有明顯比 Vercel 更省事。
- 當你需要 Python-centric backend、研究排程與資料處理時，Netlify 不是最自然的中心平台。

**適合的定位**

- `Good if you want one vendor with broader site tooling`。
- 是合格選項，但不是我對這個 repo 的第一推薦。

**官方依據**

- Netlify 有 production deploy、branch deploy 與 Deploy Preview，PR / merge request 可自動產生 preview：[Deploy overview](https://docs.netlify.com/deploy/deploy-overview)
- Netlify Functions 文件列出 synchronous、scheduled 與 background functions，background functions 最長可到 15 分鐘：[Functions overview](https://docs.netlify.com/build/functions/overview/)
- Netlify 支援 production site、Deploy Previews 與 branch deploy 的 custom domains：[Understand domains](https://docs.netlify.com/domains/domains-fundamentals/understand-domains/)

#### 4. Render

**適合你的原因**

- 如果你未來把 Python API、worker、queue 與持久化服務真正搬上雲，Render 會比 Vercel / Netlify 更自然。
- 它同時涵蓋 static site 與 background worker，很適合「public site + backend service」組合。

**限制**

- 對 v1 來說，它的能力有點超前於你目前最急迫的需求。
- 如果 public 面只是 `/site`，先上 Render 並不比 Vercel 更輕。

**適合的定位**

- `Use when backend becomes real`。
- 適合作為未來 Python API / background jobs 的落腳點之一。

**官方依據**

- Render static sites 連接 Git repo 後會在每次 push 自動更新，並可加 custom domains：[Static Sites](https://render.com/docs/static-sites)
- Render background workers 是持續執行但不接收外部流量的 services：[Background Workers](https://render.com/docs/background-workers)
- Render custom domains 支援自動 TLS，web services 與 static sites 都能綁定：[Custom Domains](https://render.com/docs/custom-domains)

#### 5. Railway

**適合你的原因**

- 當你需要真實的 app/backend、GitHub autodeploys、service-level domains、volumes、databases 時，Railway 很順手。
- 它對「把 Python API 與 app service 直接丟上去」非常友好。

**限制**

- 你現在主要要上線的是 public static product，不是多服務雲端架構。
- Railway 雖然不難用，但它更像「backend/app platform」，而不是你現在這一步最輕的 public deployment answer。
- Hobby plan 不是免費，對還在驗證一般用戶需求的早期 public product 來說，起手就不是最精簡路線。

**適合的定位**

- 與 Render 並列為未來 backend 階段的主要候選。
- 不建議當你現在 public v1 的第一步。

**官方依據**

- Railway 的 build/deploy 文件涵蓋 builds、Dockerfiles、Railpack、GitHub autodeploys、domains、volumes 等能力：[Build & Deploy](https://docs.railway.com/build-deploy)
- Railway docs 明確提到 `GitHub Autodeploys` 與 deployments lifecycle：[Build & Deploy](https://docs.railway.com/build-deploy)
- Railway Hobby plan 為每月 `$5`，不是免費方案：[Pricing Plans](https://docs.railway.com/reference/pricing/plans)
- Railway domain CLI 文件也支援 service domain 與 custom domain 設定：[railway domain](https://docs.railway.com/cli/domain)

### 關於 Fly.io

Fly.io 很有能力，特別是你要更細緻掌控 VM / region / always-on service 時會很強；但以這個 repo 目前的形狀與你「最省事」的優先序來看，它不是 convenience-first winner。你現在不是在尋找最可塑的 infra，而是在尋找最少摩擦地把 public product 上線、同時保留 private local workstation 的方案。

### 為什麼不是其他平台

如果只看「能不能做」，這五個平台都做得到。但如果看「和目前 repo 的貼合度」與「最小部署阻力」，Vercel 最合理，因為你現在的 public 面幾乎就是標準的 Git-driven static deployment 問題。Cloudflare 很強，但會讓你更早碰到 Worker 模型與平台 primitives 的設計。Netlify 很穩，但對這個 repo 沒有壓倒性優勢。Render 與 Railway 在 backend 真的成形後會變得很有價值，但目前先用它們承接整個產品，等於提早為還不存在的複雜度付費。

---

## Recommended Product / Deployment Architecture

### 核心決策

這個產品不應該從一開始就被設計成「一個站，同時承載一般使用者、研究者私有資料、登入、同步、研究寫回、背景任務」。正確做法是定義兩個產品面：

1. `Public lightweight product`
2. `Private research workstation`

### Public lightweight product

**部署方式**

- 直接把 `/Users/ro9air/projects/STOCK/site` 作為 public deploy artifact。
- 首選部署平台：`Vercel`。

**面向的一般使用者功能**

- `通用策略` 模板。
- `客製化自己的投資框架`，例如巴菲特型、題材型、因子型、穩健長投型。
- 簡化研究頁與摘要卡。
- sanitized data，不包含 private positions、成本、私有 observation 狀態。

**產品原則**

- public app 是「易上手產品殼層」，不是研究 OS 全量暴露。
- 預設應從框架選擇與 guided flow 進入，而不是從研究物件模型進入。
- public 頁面應保留研究質感，但降低操作與概念密度。

### Private research workstation

**部署方式**

- 先維持 local-first，不上公有雲。
- 使用既有 local dashboard bundle 與本機 API。

**目前已存在的系統邊界**

- Public generated site root: `/Users/ro9air/projects/STOCK/site`
- Private portfolio source: `/Users/ro9air/projects/STOCK/research/system/portfolio.private.json`
- Private/local dashboard target: `/Users/ro9air/projects/STOCK/automation/run/dashboard-local`
- Local cockpit API: `127.0.0.1:8001`

**保留 local-first 的原因**

- private positions、avg cost、target / max weight、observation writeback 都是高敏感資料。
- 這部分目前與 Python pipeline、local dashboard、private overlay 的耦合本來就合理。
- 若現在就搬上雲，主要增加的是 auth、storage、multi-user state 與隱私邊界成本，而不是研究能力。

### Future optional phase

如果未來出現以下需求，再考慮引入真正的 backend：

- 使用者登入與帳號系統
- 雲端保存個人框架與 watchlist
- 多裝置同步
- shared watchlists
- server-side scheduled jobs
- account-based personalization

那時候建議：

- public frontend 仍可維持在 `Vercel`。
- Python API / jobs 獨立部署到 `Railway` 或 `Render`。
- 也就是把 architecture 從「靜態產品 + local workstation」升級成「public frontend + backend services」，而不是反過來。

---

## Decision and Roadmap

### 最終排名

1. **Best fit now: Vercel**
2. **Strong second: Cloudflare**
3. **Good if you want one vendor with broader site tooling: Netlify**
4. **Use when backend becomes real: Railway or Render**
5. **Not my convenience-first pick: Fly.io**

### 決策

**現在**

- 用 `Vercel` 部署 public `site/`。
- private researcher cockpit 維持本機：`automation/run/dashboard-local` + `127.0.0.1:8001`。
- 不在 v1 把 private positions / cost basis 放上雲端。

**下一步**

- 從既有 public site 抽出 beginner-facing app shell。
- 重新整理資訊架構，讓一般使用者優先看到：
  - 通用策略
  - 自訂投資框架
  - 簡化研究摘要
  - 行動規則與風險說明

**再下一步**

- 只有在一般用戶需求被驗證之後，才加入 auth、DB、雲端 sync 與 background jobs。
- 一旦走到這步，backend 首選考慮 `Railway` 或 `Render`，而不是先把所有動態能力塞進 Vercel。

### 為什麼這條路最合理

- 它最大化利用你已經有的 repo 結構，而不是否定它。
- 它尊重兩種 TA 的差異，而不是強迫一個介面同時滿足兩種不同心智模型。
- 它把最昂貴的工程問題延後到真正需要時才處理。
- 它讓你可以先驗證「一般使用者是否真的需要這個產品」，而不是先投資一套重量級 SaaS 架構。

---

## Source Links

### Vercel

- [Deploying Git Repositories with Vercel](https://vercel.com/docs/deployments/git)
- [Environments / Preview deployments](https://vercel.com/docs/deployments/custom-environments)
- [Vercel Functions](https://vercel.com/docs/functions/)
- [Usage & Pricing for Cron Jobs](https://vercel.com/docs/cron-jobs/usage-and-pricing)

### Cloudflare

- [Static Assets](https://developers.cloudflare.com/workers/static-assets/)
- [Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
- [Workers Pricing](https://developers.cloudflare.com/workers/platform/pricing/)
- [Custom Domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/)

### Netlify

- [Deploy overview](https://docs.netlify.com/deploy/deploy-overview)
- [Functions overview](https://docs.netlify.com/build/functions/overview/)
- [Understand domains](https://docs.netlify.com/domains/domains-fundamentals/understand-domains/)

### Render

- [Static Sites](https://render.com/docs/static-sites)
- [Background Workers](https://render.com/docs/background-workers)
- [Custom Domains](https://render.com/docs/custom-domains)

### Railway

- [Build & Deploy](https://docs.railway.com/build-deploy)
- [Pricing Plans](https://docs.railway.com/reference/pricing/plans)
- [railway domain](https://docs.railway.com/cli/domain)
