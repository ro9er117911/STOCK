# Light Track — Quick Pulse 輕量決策指南

> 版本：Phase 1 MVP | 更新：2026-04-20

## 什麼是 Light Track？

Light Track 提供即時動能快照，讓你在看到市場訊號時（例如「美國 AI 漲了，TSM ADR 溢價」）快速判斷台股標的是否值得進場，無需跑完整 9 步驟研究工作流。

**適用情境：** 一句話策略確認、ADR 溢價補漲判斷、當日動能入場時機。

## 使用方式

**Track A（技術使用者）：**
```bash
python research_ops.py quick-decision --ticker 2330 --adr-premium 8.0 --local-px 950
```

**Track B（一般使用者）：** 直接執行，系統會引導你輸入：
```bash
python research_ops.py quick-decision
```

## Verdict 說明

| 訊號 | 意義 |
|------|------|
| 🟢 **BUY** | 動能強、ADR 溢價健康、與深度研判一致 |
| 🟡 **WAIT** | 訊號混合或超買（高 RSI），入場時機未到 |
| 🔴 **PASS** | ADR 折價或與核心研判矛盾，觀望 |

> ⚠️ 無深度研判時：本結果僅基於動能快照，不含基本面分析，有效期至當日收盤。

---

## 引導對話腳本

當缺少欄位時，系統會問：

- **ticker：** 「你在看哪支股票？（例如 2330 或 TSM）」
- **adr_premium_pct：** 「ADR 表現如何？請輸入目前的溢價百分比（例如 +5.5）」
- **local_px：** 「你看到的當前本地價格是多少？（例如 950）」
- **trigger_description：** 「什麼訊號讓你想考慮這筆交易？用一句話說說看」

---

## Traffic Light Card 範例

### 範例 1：高溢價 / RSI 中性 → WAIT
| 🟡 **WAIT** | **2330.TW (TSMC)** |
|:---|:---|
| **研判** | ADR 溢價過高（+10%），短線動能可能過熱，RSI 中性但風險報酬比不佳 |
| **信心** | 75%（有效至今日收盤）|
| **ThesisLink** | `2330-thesis-core`（一致）|
| **訊號** | ADR: +10.0% \| RSI: 58 \| FX: 穩定 |

### 範例 2：健康動能 / 研判一致 → BUY
| 🟢 **BUY** | **2330.TW (TSMC)** |
|:---|:---|
| **研判** | ADR 溢價健康（+6%），無超買訊號，與核心研判方向一致 |
| **信心** | 90%（有效至今日收盤）|
| **ThesisLink** | `2330-thesis-core`（一致）|
| **訊號** | ADR: +6.2% \| RSI: 62 \| FX: 順風 |

### 範例 3：ADR 折價 / 研判矛盾 → PASS
| 🔴 **PASS** | **2330.TW (TSMC)** |
|:---|:---|
| **研判** | ADR 折價（-2%），隔夜偏弱，與「2nm 成長回升」核心研判矛盾 |
| **信心** | 85%（有效至今日收盤）|
| **ThesisLink** | `2330-thesis-core`（矛盾⚠️）|
| **訊號** | ADR: -2.1% \| RSI: 45 \| FX: 逆風 |

---

## Phase 2 升級功能：ThesisLink

Phase 2 引入 **ThesisLink** 橋接功能，自動比對 Light Track 訊號與 Heavy Track 的深度研判：
- **Consistent with Deep Thesis（一致）：** 短線動能與中長線基本面方向相同。
- **CONTRADICTS Deep Thesis（矛盾）：** 短線訊號與核心研究相悖（例如基本面已轉弱），警示風險。

### Phase 2 應用範例：2330 研判
當 ADR 溢價 +6%，但 Heavy Thesis 為「進場前觀望 (Watch before entry)」：
- **Status:** 🟡 **WAIT**
- **Thesis Alignment:** `consistent`（雙方皆建議觀望，訊號一致）

### 分軌持有週期
- **Heavy Track (Heavy-T):** 中線佈局，持有週期 **2-3 季**，關注基本面護城河。
- **Light Track (Light-T):** 短線動能，持有週期 **1-4 週**，關注 ADR 價差與流動性。

