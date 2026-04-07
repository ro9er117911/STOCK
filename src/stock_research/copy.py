from __future__ import annotations

import re
from datetime import date
from typing import Any


def public_url(url: str) -> bool:
    return url.startswith(("http://", "https://"))


def format_percent(value: float | int) -> str:
    return f"{value:.0f}%"


def format_currency(value: float | int) -> str:
    return f"${value:,.2f}"


def _replace_case_insensitive(text: str, needle: str, replacement: str) -> str:
    return re.sub(re.escape(needle), replacement, text, flags=re.IGNORECASE)


EXACT_REPLACEMENTS = {
    "AI commercial monetization with durable government moat": "AI 商業化變現，外加持久的政府護城河。",
    "AI monetization reset and model-agnostic platform hedge": "AI 變現重估，加上 model-agnostic 平台對沖。",
    "Add up to max position size.": "可加碼至目標上限倉位。",
    "Add after earnings confirmation.": "等財報確認後再加碼。",
    "Add selectively after management confirms trend persistence.": "等管理層確認趨勢延續後，再選擇性加碼。",
    "Advanced last_reviewed_at to today and set a sensible next_review_at on the prior review cadence.": "這次把 last_reviewed_at 更新到今天，並依既有節奏安排下一次檢查。",
    "Azure AI demand can keep total Azure growth above 30%.": "Azure 的 AI 需求有機會把整體 Azure 成長維持在 30% 以上。",
    "Azure growth drops below 30% or AI contribution decelerates materially.": "如果 Azure 成長跌到 30% 以下，或 AI 貢獻明顯放緩，這個假設就要重估。",
    "Azure growth falls below 30% or flagship cloud access is materially impaired.": "若 Azure 成長跌破 30%，或核心雲端能力出現實質受損，就要退出這個 thesis。",
    "Business travel improves through 2026 and supports occupancy and pricing.": "商務旅遊在 2026 年持續改善，支撐入住率與定價。",
    "Business travel recovery and stable international/high-end RevPAR.": "商務旅遊回溫，加上國際與高端 RevPAR 維持穩定。",
    "CapEx growth will translate into durable revenue and margin support rather than pure cost drag.": "CapEx 成長最終要轉成可持續的營收與利潤率支撐，而不是單純的成本拖累。",
    "CapEx keeps accelerating while margin and monetization do not improve for two quarters.": "如果 CapEx 持續加速，但利潤率與變現連兩季都沒有改善，這個假設就要降級。",
    "CapEx remains a black hole and the market strips out the AI premium.": "如果 CapEx 仍像黑洞一樣吞資本，市場就可能把 AI 溢價拿掉。",
    "CapEx rises again while Copilot monetization does not improve.": "如果 CapEx 再往上走、而 Copilot 變現還是沒改善，就要減碼。",
    "CapEx trend, gross margin trend, and monetization updates.": "CapEx 趨勢、毛利率趨勢與變現更新。",
    "Cash return guidance, leverage, and fee-based earnings mix.": "資本回饋指引、槓桿水位，以及 fee-based earnings 結構。",
    "Commercial growth falls below 70% without offsetting government upside.": "若商業業務成長掉到 70% 以下，且沒有政府業務補上，就要減碼。",
    "Commercial growth normalizes faster than narrative assumes.": "商業成長若比市場敘事更快正常化，估值就要下修。",
    "Copilot adoption can improve enough to justify the AI distribution premium.": "Copilot adoption 若能明顯改善，就足以支撐 AI 分發溢價。",
    "Copilot adoption、M365 pricing pass-through、Azure AI demand.": "Copilot adoption、M365 漲價傳導，以及 Azure AI 需求。",
    "Copilot enterprise penetration breaks above 10% and CapEx growth moderates.": "當 Copilot 企業滲透率突破 10%，且 CapEx 成長放緩時，就可以考慮加碼。",
    "Copilot remains productively underwhelming and adoption stalls.": "如果 Copilot 實際效益仍偏弱、採用率停滯，這個假設就會受壓。",
    "Copilot stays below 10% enterprise penetration through the next earnings cycle.": "若 Copilot 到下一輪財報仍低於 10% 企業滲透率，就要保守看待。",
    "Core thesis remains supported by prior evidence: strong US commercial growth and Program of Record status for Maven AI.": "核心 thesis 仍由前一版證據支撐：包括強勁的美國商業成長，以及 Maven AI 升格為正式預算項目。",
    "Corporate booking and occupancy commentary.": "企業訂房與入住率評論。",
    "Corporate travel and forward bookings improve while international RevPAR remains strong.": "如果商務旅遊與前瞻訂房改善，且國際 RevPAR 依舊強勁，就可考慮加碼。",
    "Corporate travel recovery stalls for another full cycle.": "若商務旅遊再停滯一整個循環，就要下修期待。",
    "Enterprise adoption commentary, seat growth, and attach rates.": "企業採用評論、席次成長，以及 attach rate。",
    "Exit active thesis and rotate to better risk/reward.": "退出目前 thesis，轉往風險報酬更佳的標的。",
    "Exit if budget-backed programs lose priority.": "若有預算支持的專案失去優先順序，就應退出。",
    "Exit if premium segments crack together.": "若高端客群也開始同步轉弱，就應退出。",
    "Exit regardless of price action.": "不管股價走勢，直接退出。",
    "Exit the AI monetization thesis and keep only core cloud exposure if needed.": "退出 AI 變現 thesis；若有需要，只保留核心雲端曝險。",
    "Exit the active thesis.": "退出目前 thesis。",
    "FY2026 Q3 earnings: Azure growth, AI contribution, Copilot monetization, margin trend, and CapEx guidance.": "FY2026 Q3 財報：Azure 成長、AI 貢獻、Copilot 變現、利潤率趨勢，以及 CapEx 財測。",
    "Fee earnings weaken materially and leverage rises without demand support.": "若 fee earnings 明顯轉弱，且在需求沒有撐住時槓桿又上升，就要轉保守。",
    "Government contracts remain sticky and budget-backed.": "政府合約仍具黏性，且有正式預算支持。",
    "Government or regulatory friction hurts model-neutral cloud strategy.": "若政府或監管摩擦傷到 model-neutral 雲端策略，這個 thesis 就會受壓。",
    "Government procurement slows with defense budget reprioritization.": "如果國防預算重排導致政府採購放慢，就要調整判斷。",
    "High-end and business travel weaken together in a deeper recession.": "若景氣更深度下行，高端與商務旅遊同步轉弱，就要退出。",
    "High-end and international RevPAR both roll over materially.": "如果高端與國際 RevPAR 都明顯轉弱，這個假設就失效。",
    "High-end and international travel remain resilient enough to offset weaker low-end domestic demand.": "高端與國際旅遊仍夠有韌性，足以抵消低端美國內需偏弱。",
    "Ignore unless fundamentals deteriorate.": "除非基本面惡化，否則先忽略。",
    "International travel momentum fades as FX or geopolitics worsen.": "若匯率或地緣政治惡化，國際旅遊動能可能會轉弱。",
    "Legacy MSFT AI market judgment": "舊版 MSFT AI 市場判斷筆記",
    "Legacy March 2026 market update": "2026 年 3 月市場更新舊筆記",
    "Light-asset travel compounder with business travel recovery optionality": "資本輕、可複利的旅遊平台，外加商務旅遊回溫的選擇權。",
    "Maintained hold/observe stance pending the next earnings verification point.": "目前維持持有 / 觀望，等下一個財報驗證點。",
    "Maintained the defensive quality / business-travel-recovery framing without changing confidence.": "防守型品質股加商務旅遊回溫的敘事先維持，信心不變。",
    "Margin expansion can accompany revenue acceleration.": "營收加速時，利潤率也有機會同步擴張。",
    "Market rotates away from quality defensives even if fundamentals hold.": "就算基本面沒壞，市場也可能先從防守型品質股撤出。",
    "Marriott investor news releases": "Marriott 投資人新聞稿",
    "Maven/DoD contract status and budget mentions in filings.": "Maven / DoD 合約狀態，以及揭露文件中的預算訊號。",
    "Microsoft official news feed": "Microsoft 官方新聞來源",
    "Next earnings: RevPAR mix, corporate travel commentary, forward bookings, and cash return guidance.": "下一次財報：RevPAR 結構、商務旅遊評論、前瞻訂房，以及資本回饋指引。",
    "No assumption status changes; valuation and growth-monitoring thresholds remain the same.": "假設狀態沒有變動，估值與成長監控門檻先維持不變。",
    "No material evidence delta versus the prior state; thesis, assumptions, and action remain intact.": "和前一版相比，沒有新的重大證據差異；thesis、假設與操作都先維持。",
    "No material new events or filings were supplied beyond the existing state.": "除了既有研究內容之外，沒有新增需要重估的重大事件或揭露。",
    "No new events were provided in the refresh bundle, so the MAR thesis remains unchanged. Confidence and action stay stable; only the review timestamps are advanced to today with the next check pushed out on the existing cadence.": "本輪沒有新增需要重估的事件，因此 MAR 的 thesis 維持不變。信心與操作都先延續，只是把檢查時間更新到今天，並依原本節奏往後安排下一次檢查。",
    "No new evidence beyond the existing state; no thesis or assumption re-rating required.": "這輪沒有超出既有研究框架的新證據，因此不需要重新評等 thesis 或假設。",
    "No new evidence bundle was provided in this refresh, so the PLTR thesis state is unchanged. Confidence, thesis framing, and action posture remain intact; only the review timestamp is advanced.": "這次更新沒有新增足以重寫 thesis 的證據，所以 PLTR 的 thesis 狀態不變。信心、論述框架與操作姿態都先延續，只更新檢查時間。",
    "No new material events were provided in the refresh bundle, so the MSFT thesis state remains unchanged aside from the routine review timestamp update. Confidence, assumptions, and action rules are preserved.": "本輪沒有新增足以改寫 thesis 的重大事件，所以 MSFT 除了例行更新檢查時間之外，主判斷不變。信心、關鍵假設與操作規則都先維持。",
    "No rule text changed; review whether the trigger still matches the thesis.": "規則文字沒有調整，但仍要確認觸發條件是否還對得上 thesis。",
    "No review summary has been generated yet.": "目前還沒有新的更新摘要。",
    "Only act if accompanied by demand deterioration.": "只有在需求惡化同時出現時才採取動作。",
    "Operating margin and SBC ratio.": "營業利潤率與 SBC 比例。",
    "Official Microsoft newsroom RSS feed.": "Microsoft 官方新聞室 RSS。",
    "Official Marriott newsroom archive.": "Marriott 官方新聞室頁面。",
    "Official Palantir investor news release archive.": "Palantir 投資人新聞稿頁面。",
    "Official SEC filings. Material forms are filtered by each ticker state threshold.": "官方 SEC 揭露來源；是否算重大事件，依各 ticker 的門檻設定判斷。",
    "Daily Yahoo Finance chart data for gap and abnormal volume detection.": "Yahoo Finance 日線資料，用來抓跳空與異常成交量。",
    "Palantir investor news releases": "Palantir 投資人新聞稿",
    "Pause adds and re-rate to lower EV/Sales.": "先停止加碼，並把估值重心下修到更低的 EV/Sales 區間。",
    "Premium segment demand softens without offsetting business-travel recovery.": "如果高端客群需求轉弱，且沒有商務旅遊回溫來抵消，就要減碼。",
    "Program of Record gets delayed or defense funding is cut.": "若 Program of Record 延後，或國防資金被砍，這個 thesis 就要重估。",
    "Program of Record is downgraded or core defense budget support weakens.": "若 Program of Record 被降級，或核心國防預算支持轉弱，就應退出。",
    "Q1 2026 earnings: US Commercial growth, margins, major government renewal cadence.": "2026 Q1 財報：美國商業業務成長、利潤率，以及主要政府合約續約節奏。",
    "Quarterly Azure growth and AI contribution disclosures.": "每季 Azure 成長與 AI 貢獻揭露。",
    "Quarterly US Commercial revenue growth and customer count.": "每季美國商業營收成長與客戶數變化。",
    "Reduce tactical exposure and re-rate on mature-software multiples.": "降低戰術性曝險，並用成熟軟體股估值重新定價。",
    "RevPAR mix and management commentary by segment.": "各分部的 RevPAR 結構與管理層評論。",
    "Revenue beats but operating leverage stops improving for two quarters.": "若營收雖然超預期，但營運槓桿連兩季都不再改善，就要重新評估。",
    "Review metadata updated to today with a later next review date.": "這次主要是把 review metadata 更新到今天，並順延下次檢查日期。",
    "SEC company submissions": "SEC 公司揭露檔案",
    "Selectively add after management confirms trend persistence.": "等管理層確認趨勢延續後，再選擇性加碼。",
    "The asset-light model preserves downside protection and cash return flexibility.": "資本輕模式能保住下檔保護，也讓資本回饋更有彈性。",
    "Trim and keep only defensive core size.": "先減碼，只保留防守型核心倉位。",
    "Trim and lower the valuation range.": "先減碼，並下修估值區間。",
    "Trim if government cloud narrative weakens the platform hedge.": "若政府雲敘事削弱了平台對沖，就要減碼。",
    "Trim into strength and lower conviction.": "趁強勢減碼，並下調信心。",
    "Trim tactical adds and revisit valuation regime.": "先減掉戰術性加碼部位，並重新檢查估值框架。",
    "US Commercial AI demand can sustain hyper-growth above 80%.": "美國商業 AI 需求有機會把超高速成長維持在 80% 以上。",
    "US Commercial revenue grows above 100% for two straight quarters and margin expands.": "如果美國商業營收連兩季都高於 100%，且利潤率同步擴張，就可以加碼。",
    "US Commercial revenue growth falls below 50% for one full quarter.": "若美國商業營收成長有一整季跌破 50%，這個假設就要失效。",
    "Updated review timing to reflect a fresh check today and a near-term follow-up cadence.": "這次把檢查時間更新成今天已完成複盤，並維持近期待追蹤節奏。",
    "Valuation compresses even while fundamentals stay good.": "就算基本面還好，估值也可能先被壓縮。",
    "Yahoo Finance chart": "Yahoo Finance 圖表資料",
    "Automatic fallback refresh used. Review the generated diff before merging.": "這次使用規則式 fallback 更新；合併前仍要人工檢查差異。",
    "investor news": "官方新聞",
    "legacy seed": "既有研究節點",
    "research page": "研究頁面",
    "research note": "內部研究筆記",
    "review summary": "更新摘要",
    "add": "加碼",
    "trim": "減碼",
    "exit": "退出",
    "capital_allocation": "資本配置",
    "demand": "需求",
    "government": "政府",
    "product": "產品",
    "profitability": "獲利",
    "quarterly": "每季",
    "monthly": "每月",
    "html": "官網頁面",
    "rss": "RSS",
    "market_data": "市場資料",
    "local_markdown": "本機研究筆記",
    "sec": "SEC",
    "noise": "雜訊",
    "thesis weakener": "削弱 thesis 的風險",
    "thesis breaker": "可能打斷 thesis 的風險",
}

PHRASE_REPLACEMENTS = [
    ("RevPAR mix", "RevPAR 結構"),
    ("gross margin trend", "毛利率趨勢"),
    ("seat growth", "席次成長"),
    ("attach rates", "attach rate"),
    ("major government renewal cadence", "主要政府合約續約節奏"),
    ("forward bookings", "前瞻訂房"),
    ("cash return guidance", "資本回饋指引"),
    ("corporate travel commentary", "管理層對商務旅遊的評論"),
    ("international RevPAR", "國際 RevPAR"),
    ("premium segment demand", "高端客群需求"),
    ("business travel", "商務旅遊"),
    ("high-end and international travel", "高端與國際旅遊需求"),
    ("Copilot enterprise penetration", "Copilot 企業滲透率"),
    ("Copilot monetization", "Copilot 變現"),
    ("AI contribution", "AI 貢獻"),
    ("margin trend", "利潤率趨勢"),
    ("CapEx guidance", "CapEx 財測"),
    ("CapEx growth", "CapEx 成長"),
    ("AI demand", "AI 需求"),
    ("Azure growth", "Azure 成長"),
    ("US Commercial growth", "美國商業業務成長"),
    ("government renewal cadence", "政府續約節奏"),
    ("quarterly earnings release date", "季度財報公布日期"),
    ("quarterly earnings", "季度財報"),
    ("earnings", "財報"),
    ("guidance", "指引"),
    ("margins", "利潤率"),
    ("margin", "利潤率"),
    ("revenue", "營收"),
    ("growth", "成長"),
    ("demand", "需求"),
    ("customer count", "客戶數"),
    ("management commentary", "管理層評論"),
    ("review timestamp", "檢查時間"),
    ("thesis state", "thesis 狀態"),
    ("review date", "檢查日期"),
    ("review timing", "檢查時間"),
    ("next review date", "下次檢查日期"),
    ("review cadence", "檢查節奏"),
    ("valuation regime", "估值框架"),
    ("hold/observe stance", "持有 / 觀望立場"),
    ("core thesis", "核心 thesis"),
    ("refresh bundle", "更新事件包"),
    ("material events", "重大事件"),
    ("material event", "重大事件"),
    ("evidence bundle", "證據包"),
]

REGEX_REPLACEMENTS = [
    (r"\bFY(\d{4}) Q([1-4]) earnings\b", r"FY\1 Q\2 財報"),
    (r"\bQ([1-4]) (\d{4}) earnings\b", r"\2 Q\1 財報"),
    (r"\bNext earnings\b", "下一次財報"),
    (r"\bNo new material events were provided in the refresh bundle\b", "本輪沒有新增足以改寫 thesis 的重大事件"),
    (r"\bNo new events were provided in the refresh bundle\b", "本輪沒有新增需要重估 thesis 的事件"),
    (r"\bNo new evidence bundle was provided in this refresh\b", "這次更新沒有新增足以重寫 thesis 的證據"),
    (r"\bNo new evidence beyond the existing state\b", "沒有超出既有研究框架的新證據"),
    (r"\bNo material evidence delta versus the prior state\b", "和前一版相比，沒有新的重大證據差異"),
    (r"\bstate remains unchanged\b", "目前判斷維持不變"),
    (r"\bthesis remains unchanged\b", "thesis 維持不變"),
    (r"\baction rules are preserved\b", "操作規則維持不變"),
    (r"\baction stay stable\b", "操作方向維持穩定"),
    (r"\bon the existing cadence\b", "依原本節奏"),
    (r"\bwith a later next review date\b", "並把下次檢查日期往後推進"),
    (r"\bwith the next check pushed out\b", "並把下一次檢查往後排"),
    (r"\bAdvanced last_reviewed_at to today\b", "把 last_reviewed_at 更新到今天"),
    (r"\bUpdated review timing to reflect a fresh check today\b", "把檢查時間更新為今天已完成複盤"),
    (r"\bMaintained\b", "維持"),
    (r"\bremains supported by prior evidence\b", "仍由前一版證據支撐"),
]

ASSUMPTION_STATUS_LABELS = {
    "reinforced": "已強化",
    "watch": "持續觀察",
    "pressured": "受壓",
    "broken": "失效",
}

DECISION_LABELS = {
    "refresh": "需要重估",
    "watch": "持續追蹤",
    "ignore": "暫不動作",
}

SOURCE_STATUS_LABELS = {
    "active": "啟用",
    "polled": "已輪詢",
    "failed": "失敗",
    "skipped": "略過",
    "fixture_override": "fixture 模式略過",
    "disabled": "停用",
}

RISK_TIER_LABELS = {
    "thesis weakener": "削弱 thesis 的風險",
    "thesis breaker": "可能打斷 thesis 的風險",
    "noise": "雜訊",
}

RISK_LEVEL_LABELS = {
    "core": "核心倉位",
    "satellite": "衛星倉位",
    "high-conviction": "高信念倉位",
    "trading": "交易倉位",
}


def localize_text(text: str) -> str:
    if not text:
        return ""
    localized = text.strip()
    if localized in EXACT_REPLACEMENTS:
        return EXACT_REPLACEMENTS[localized]
    for needle, replacement in EXACT_REPLACEMENTS.items():
        if needle in localized:
            localized = localized.replace(needle, replacement)
    for needle, replacement in PHRASE_REPLACEMENTS:
        localized = _replace_case_insensitive(localized, needle, replacement)
    for pattern, replacement in REGEX_REPLACEMENTS:
        localized = re.sub(pattern, replacement, localized, flags=re.IGNORECASE)
    localized = localized.replace("  ", " ").replace(" .", ".").replace(" ,", ",")
    return localized


def localize_status(status: str) -> str:
    return ASSUMPTION_STATUS_LABELS.get(status, localize_text(status))


def localize_decision(decision: str) -> str:
    return DECISION_LABELS.get(decision, localize_text(decision))


def localize_source_status(status: str) -> str:
    return SOURCE_STATUS_LABELS.get(status, localize_text(status))


def localize_risk_tier(tier: str) -> str:
    return RISK_TIER_LABELS.get(tier, localize_text(tier))


def localize_risk_level(level: str) -> str:
    return RISK_LEVEL_LABELS.get(level, level or "尚未設定")


def split_checklist(text: str) -> list[str]:
    if not text:
        return []
    _, separator, tail = text.partition(":")
    working = tail if separator else text
    working = working.replace(" and ", ", ")
    parts = [part.strip(" .") for part in re.split(r"[;,]", working) if part.strip(" .")]
    return [localize_text(part) for part in parts]


def thesis_health_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    assumption_scores = {
        "reinforced": 1.0,
        "watch": 0.6,
        "pressured": 0.35,
        "broken": 0.0,
    }
    assumptions = state.get("assumptions", [])
    assumption_score = (
        sum(assumption_scores.get(item.get("status", "watch"), 0.5) for item in assumptions) / len(assumptions)
        if assumptions
        else state.get("confidence", 0.0)
    )
    score = round((state.get("confidence", 0.0) * 0.65) + (assumption_score * 0.35), 2)
    if score >= 0.75:
        label = "健康穩定"
    elif score >= 0.6:
        label = "穩定監控"
    elif score >= 0.45:
        label = "需要追蹤"
    else:
        label = "高風險"
    return {
        "score": score,
        "label": label,
        "reinforced_count": sum(1 for item in assumptions if item.get("status") == "reinforced"),
        "watch_count": sum(1 for item in assumptions if item.get("status") == "watch"),
        "pressured_count": sum(1 for item in assumptions if item.get("status") == "pressured"),
    }


def compute_priority(
    *,
    current_action: str,
    next_review_at: str,
    risk_level: str,
    confidence_delta: float,
    event_timeline: list[dict[str, Any]],
    risk_alert_count: int = 0,
    macro_regime: str = "",
) -> dict[str, Any]:
    action_weight = 40
    lowered = current_action.lower()
    if "exit" in lowered or "退出" in current_action:
        action_weight = 100
    elif "trim" in lowered or "減碼" in current_action:
        action_weight = 85
    elif "add" in lowered or "加碼" in current_action:
        action_weight = 72
    elif "觀望" in current_action:
        action_weight = 55

    days_until = max((date.fromisoformat(next_review_at) - date.today()).days, 0)
    review_weight = max(0, 30 - days_until)
    risk_weight = {
        "high-conviction": 25,
        "core": 18,
        "satellite": 12,
        "trading": 10,
    }.get(risk_level, 8)
    event_weight = sum(8 for item in event_timeline[:3] if item.get("decision") == "refresh")
    event_weight += sum(4 for item in event_timeline[:3] if item.get("decision") == "watch")
    confidence_weight = 8 if confidence_delta > 0.04 else (-4 if confidence_delta < -0.04 else 0)
    alert_weight = min(risk_alert_count, 3) * 8
    macro_weight = 12 if macro_regime in {"stress", "panic"} else (6 if macro_regime == "elevated" else 0)
    score = action_weight + review_weight + risk_weight + event_weight + confidence_weight + alert_weight + macro_weight
    if score >= 110:
        label = "最高優先"
    elif score >= 85:
        label = "優先追蹤"
    elif score >= 60:
        label = "例行檢查"
    else:
        label = "低優先"
    return {"score": score, "label": label}


def compose_summary_blurb(
    *,
    ticker: str,
    current_action: str,
    changed_assumptions: list[dict[str, Any]],
    event_timeline: list[dict[str, Any]],
    next_checklist: list[str],
) -> str:
    if changed_assumptions:
        lead = f"{ticker} 這輪有 {len(changed_assumptions)} 個假設被重新校準，研究重點不再只是例行更新。"
    elif any(item.get("decision") == "refresh" for item in event_timeline[:3]):
        lead = f"{ticker} 這輪有足以觸發重新檢查的事件，但目前主判斷沒有被推翻。"
    else:
        lead = f"{ticker} 本輪沒有新增足以改寫 thesis 的重大事件，研究主軸先延續前一版。"
    next_focus = next_checklist[0] if next_checklist else "下一次例行複盤"
    return f"{lead} 目前先維持「{current_action}」，下一個驗證點先盯 {next_focus}。"
