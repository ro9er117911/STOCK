from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from .config import RESEARCH_ROOT, WATCHLIST
from .markdown import render_current_report, render_review_summary
from .observation import ensure_observation_system_files
from .research_state import normalize_state_contract, sync_candidate_queue
from .risk import DEFAULT_RISK_POLICY
from .storage import write_json, write_jsonl


BASELINE_PROFILES: dict[str, dict[str, Any]] = {
    "PLTR": {
        "ticker": "PLTR",
        "company_name": "Palantir Technologies",
        "research_topic": "AI commercial monetization with durable government moat",
        "research_type": "事件驅動 / 中線",
        "holding_period": "數季至一年",
        "last_reviewed_at": "2026-03-25",
        "next_review_at": "2026-05-05",
        "current_action": "持有 / 逢回加碼",
        "confidence": 0.72,
        "latest_delta": [
            "Q4 2025 美國商業營收維持三位數成長，商業化假設被強化。",
            "Maven AI 升級為 Program of Record，政府訂單黏著度提升。",
            "短線估值仍高，必須持續監控商業增速是否掉到 50% 以下。",
        ],
        "primary_observation_variables": [
            "US Commercial revenue growth",
            "Government contract durability",
            "Operating margin expansion",
        ],
        "secondary_observation_variables": [
            "International commercial conversion",
            "Federal budget cadence",
            "Stock-based compensation discipline",
        ],
        "noise_filters": [
            "Insider selling headlines without demand change",
            "Single-session tech selloff",
            "Unverified channel checks",
        ],
        "thresholds": {
            "price_gap_pct": 10.0,
            "volume_ratio": 2.2,
            "deep_refresh_days": 7,
            "material_sec_forms": ["8-K", "10-Q", "10-K"],
            "earnings_keywords": ["earnings", "results", "guidance", "quarter", "contract"],
            "positive_keywords": ["record", "expands", "wins", "growth", "program of record", "award"],
            "negative_keywords": ["cut", "miss", "delay", "probe", "lawsuit", "budget"],
        },
        "thesis": {
            "thesis_id": "pltr-thesis-core",
            "statement": "市場仍低估 Palantir 在美國商業 AI 與國防軟體的雙引擎飛輪，只要商業營收維持高成長且政府專案升級為常態預算，估值雖高仍可被更高品質的成長證明支持。",
            "core_catalyst": "美國商業營收續強與大型政府專案正式預算化。",
            "market_blind_spot": "市場把 PLTR 視為敘事股，但近兩季已證明商業化與政府續約可同時成立。",
            "verification_date": "2026-05-05",
            "expiry_condition": "US Commercial growth 掉到 50% 以下或核心政府專案預算被削弱。",
        },
        "assumptions": [
            {
                "assumption_id": "pltr-a1",
                "statement": "US Commercial AI demand can sustain hyper-growth above 80%.",
                "type": "demand",
                "verification_method": "Quarterly US Commercial revenue growth and customer count.",
                "update_frequency": "quarterly",
                "invalidation_condition": "US Commercial revenue growth falls below 50% for one full quarter.",
                "status": "reinforced",
                "confidence": 0.78,
                "keywords": ["commercial", "customer", "growth", "ai", "earnings"],
            },
            {
                "assumption_id": "pltr-a2",
                "statement": "Government contracts remain sticky and budget-backed.",
                "type": "government",
                "verification_method": "Maven/DoD contract status and budget mentions in filings.",
                "update_frequency": "monthly",
                "invalidation_condition": "Program of Record gets delayed or defense funding is cut.",
                "status": "reinforced",
                "confidence": 0.74,
                "keywords": ["government", "defense", "contract", "maven", "budget"],
            },
            {
                "assumption_id": "pltr-a3",
                "statement": "Margin expansion can accompany revenue acceleration.",
                "type": "profitability",
                "verification_method": "Operating margin and SBC ratio.",
                "update_frequency": "quarterly",
                "invalidation_condition": "Revenue beats but operating leverage stops improving for two quarters.",
                "status": "watch",
                "confidence": 0.63,
                "keywords": ["margin", "profit", "operating", "sbc"],
            },
        ],
        "risks": [
            {
                "risk_id": "pltr-r1",
                "statement": "Commercial growth normalizes faster than narrative assumes.",
                "tier": "thesis weakener",
                "leading_indicator": "US Commercial growth slope",
                "response": "Pause adds and re-rate to lower EV/Sales.",
            },
            {
                "risk_id": "pltr-r2",
                "statement": "Government procurement slows with defense budget reprioritization.",
                "tier": "thesis breaker",
                "leading_indicator": "DoD program funding language",
                "response": "Exit if budget-backed programs lose priority.",
            },
            {
                "risk_id": "pltr-r3",
                "statement": "Valuation compresses even while fundamentals stay good.",
                "tier": "noise",
                "leading_indicator": "Peer multiple compression",
                "response": "Only act if accompanied by demand deterioration.",
            },
        ],
        "valuation_regime": {
            "current_yardstick": "High-growth AI software EV/Sales",
            "better_yardstick": "Growth plus FCF durability premium",
            "switch_trigger": "Commercial growth remains above 80% while margins expand.",
            "re_rating_logic": "The market starts paying for compounding rather than story optionality.",
            "associated_risk": "Any deceleration in commercial growth brings multiple compression first.",
        },
        "scenarios": [
            {
                "scenario_id": "pltr-s-base",
                "trigger": "US Commercial stays above 80% and government renewals remain intact.",
                "logic": "Original thesis holds with both engines contributing.",
                "action": "Hold core and add on controlled pullbacks.",
            },
            {
                "scenario_id": "pltr-s-bull",
                "trigger": "Commercial growth remains above 100% with margin expansion.",
                "logic": "Narrative shifts from government-heavy to enterprise platform winner.",
                "action": "Add if valuation expansion is backed by margin improvement.",
            },
            {
                "scenario_id": "pltr-s-bear",
                "trigger": "Commercial growth slows but government stays intact.",
                "logic": "Multiple compresses before earnings catch up.",
                "action": "Trim tactical size, keep only high-conviction core.",
            },
            {
                "scenario_id": "pltr-s-break",
                "trigger": "Defense budget or flagship programs deteriorate materially.",
                "logic": "The moat claim fails and valuation has little support.",
                "action": "Exit.",
            },
        ],
        "action_rules": [
            {
                "action_rule_id": "pltr-ar-add",
                "kind": "add",
                "condition": "US Commercial revenue grows above 100% for two straight quarters and margin expands.",
                "action": "Add up to max position size.",
            },
            {
                "action_rule_id": "pltr-ar-trim",
                "kind": "trim",
                "condition": "Commercial growth falls below 70% without offsetting government upside.",
                "action": "Trim tactical adds and revisit valuation regime.",
            },
            {
                "action_rule_id": "pltr-ar-exit",
                "kind": "exit",
                "condition": "Program of Record is downgraded or core defense budget support weakens.",
                "action": "Exit regardless of price action.",
            },
        ],
        "next_must_check_data": "Q1 2026 earnings: US Commercial growth, margins, major government renewal cadence.",
        "research_debt": [
            "Need cleaner read on UK/FCA contribution size.",
            "Need scenario work on commercial deal concentration.",
        ],
        "source_manifest": [
            {
                "source_id": "legacy-market-update",
                "type": "local_markdown",
                "label": "Legacy March 2026 market update",
                "url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
            },
            {
                "source_id": "sec",
                "type": "sec",
                "label": "SEC company submissions",
                "url": "https://data.sec.gov/submissions/CIK0001321655.json",
            },
            {
                "source_id": "investor_news",
                "type": "html",
                "label": "Palantir investor news releases",
                "url": "https://investors.palantir.com/news-events/news-releases/",
            },
            {
                "source_id": "price",
                "type": "market_data",
                "label": "Yahoo Finance chart",
                "url": "https://query1.finance.yahoo.com/v8/finance/chart/PLTR?range=1mo&interval=1d",
            },
        ],
        "last_seen_event_cursors": {"sec": "", "investor_news": "", "price": ""},
        "version_log": [
            {
                "version": "v0",
                "date": "2026-03-25",
                "reason": "Baseline migration from legacy March update.",
                "impact": "Established living thesis and machine-readable state.",
            }
        ],
        "seed_events": [
            {
                "event_id": "pltr-seed-2026-q4-results",
                "ticker": "PLTR",
                "source_type": "legacy_seed",
                "occurred_at": "2026-03-25",
                "title": "Q4 2025 results showed 137% US commercial growth.",
                "source_url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
                "affected_assumption_ids": ["pltr-a1", "pltr-a3"],
                "marginal_impact": "+",
                "threshold_breach": True,
                "requires_refresh": True,
                "decision": "refresh",
                "metadata": {"seed": True},
            },
            {
                "event_id": "pltr-seed-2026-maven",
                "ticker": "PLTR",
                "source_type": "legacy_seed",
                "occurred_at": "2026-03-25",
                "title": "Maven AI became a Program of Record.",
                "source_url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
                "affected_assumption_ids": ["pltr-a2"],
                "marginal_impact": "+",
                "threshold_breach": True,
                "requires_refresh": True,
                "decision": "refresh",
                "metadata": {"seed": True},
            },
        ],
    },
    "MSFT": {
        "ticker": "MSFT",
        "company_name": "Microsoft",
        "research_topic": "AI monetization reset and model-agnostic platform hedge",
        "research_type": "事件驅動 / 中線",
        "holding_period": "數季至一年",
        "last_reviewed_at": "2026-03-25",
        "next_review_at": "2026-04-29",
        "current_action": "持有 / 觀望，等待下一次驗證點",
        "confidence": 0.63,
        "latest_delta": [
            "市場開始把 MSFT 從 AI 敘事龍頭重估為高 CapEx 的基礎設施股。",
            "M365 2026-07-01 漲價與 model-agnostic Copilot 仍可能修復 EPS 與估值尺。",
            "短線 Thesis 已轉成需要財報驗證的 watch state，不適合在資訊未確認前追價。",
        ],
        "primary_observation_variables": [
            "Azure growth and AI contribution",
            "Copilot enterprise adoption",
            "CapEx payback versus margin pressure",
        ],
        "secondary_observation_variables": [
            "Government cloud contract status",
            "M365 pricing realization",
            "Oil / rates driven valuation pressure",
        ],
        "noise_filters": [
            "單一功能 rollback 未連到企業端 adoption",
            "Macro headline without Azure or Copilot impact",
            "Short-term price weakness without revision in demand",
        ],
        "thresholds": {
            "price_gap_pct": 8.0,
            "volume_ratio": 2.0,
            "deep_refresh_days": 7,
            "material_sec_forms": ["8-K", "10-Q", "10-K"],
            "earnings_keywords": ["earnings", "results", "guidance", "quarter", "investor relations", "price"],
            "positive_keywords": ["raise", "growth", "copilot", "azure", "expands", "pricing"],
            "negative_keywords": ["cuts", "delay", "lawsuit", "probe", "rollback", "decline", "miss"],
        },
        "thesis": {
            "thesis_id": "msft-thesis-core",
            "statement": "微軟仍是 AI 基礎設施與企業分發的核心受益者，但要讓股價脫離 CapEx 懷疑，必須用 Copilot adoption、M365 漲價與 Azure AI 需求證明其估值可以重新從成熟雲端股回到高品質 AI 平台股。",
            "core_catalyst": "Copilot adoption、M365 pricing pass-through、Azure AI demand.",
            "market_blind_spot": "市場短線聚焦高 CapEx，低估 model-agnostic Copilot 與商業訂價權恢復帶來的 EPS 扭轉。",
            "verification_date": "2026-04-29",
            "expiry_condition": "Azure growth falls below 30%, Copilot adoption remains stalled, or flagship government cloud access materially weakens.",
        },
        "assumptions": [
            {
                "assumption_id": "msft-a1",
                "statement": "Azure AI demand can keep total Azure growth above 30%.",
                "type": "demand",
                "verification_method": "Quarterly Azure growth and AI contribution disclosures.",
                "update_frequency": "quarterly",
                "invalidation_condition": "Azure growth drops below 30% or AI contribution decelerates materially.",
                "status": "watch",
                "confidence": 0.68,
                "keywords": ["azure", "cloud", "ai contribution", "earnings"],
            },
            {
                "assumption_id": "msft-a2",
                "statement": "Copilot adoption can improve enough to justify the AI distribution premium.",
                "type": "product",
                "verification_method": "Enterprise adoption commentary, seat growth, and attach rates.",
                "update_frequency": "quarterly",
                "invalidation_condition": "Copilot stays below 10% enterprise penetration through the next earnings cycle.",
                "status": "pressured",
                "confidence": 0.54,
                "keywords": ["copilot", "adoption", "seat", "productivity"],
            },
            {
                "assumption_id": "msft-a3",
                "statement": "CapEx growth will translate into durable revenue and margin support rather than pure cost drag.",
                "type": "capital_allocation",
                "verification_method": "CapEx trend, gross margin trend, and monetization updates.",
                "update_frequency": "quarterly",
                "invalidation_condition": "CapEx keeps accelerating while margin and monetization do not improve for two quarters.",
                "status": "watch",
                "confidence": 0.56,
                "keywords": ["capex", "margin", "profit", "investment"],
            },
        ],
        "risks": [
            {
                "risk_id": "msft-r1",
                "statement": "CapEx remains a black hole and the market strips out the AI premium.",
                "tier": "thesis weakener",
                "leading_indicator": "CapEx acceleration without monetization proof",
                "response": "Reduce tactical exposure and re-rate on mature-software multiples.",
            },
            {
                "risk_id": "msft-r2",
                "statement": "Copilot remains productively underwhelming and adoption stalls.",
                "tier": "thesis breaker",
                "leading_indicator": "Enterprise penetration and renewal commentary",
                "response": "Exit the AI monetization thesis and keep only core cloud exposure if needed.",
            },
            {
                "risk_id": "msft-r3",
                "statement": "Government or regulatory friction hurts model-neutral cloud strategy.",
                "tier": "thesis weakener",
                "leading_indicator": "Contract disputes and supply-chain restrictions",
                "response": "Trim if government cloud narrative weakens the platform hedge.",
            },
        ],
        "valuation_regime": {
            "current_yardstick": "Mature cloud P/E plus AI premium",
            "better_yardstick": "AI platform and enterprise distribution premium",
            "switch_trigger": "Copilot monetization shows real seat growth and CapEx intensity stabilizes.",
            "re_rating_logic": "The market pays again for AI distribution and pricing power instead of just infrastructure spend.",
            "associated_risk": "If monetization lags, the premium disappears faster than fundamentals deteriorate.",
        },
        "scenarios": [
            {
                "scenario_id": "msft-s-base",
                "trigger": "Azure stays strong and Copilot improves modestly by next earnings.",
                "logic": "The thesis stays alive but valuation remains range-bound until proof arrives.",
                "action": "Hold and wait for earnings confirmation before adding.",
            },
            {
                "scenario_id": "msft-s-bull",
                "trigger": "Copilot adoption inflects and M365 pricing flows through cleanly.",
                "logic": "MSFT is re-rated from capex-heavy cloud operator to AI productivity platform.",
                "action": "Add after confirmation on numbers, not before.",
            },
            {
                "scenario_id": "msft-s-bear",
                "trigger": "CapEx keeps rising while Copilot remains stuck.",
                "logic": "AI premium compresses and the market defaults to mature-software multiples.",
                "action": "Trim into strength and protect capital.",
            },
            {
                "scenario_id": "msft-s-break",
                "trigger": "Azure growth breaks below 30% or Copilot monetization clearly fails.",
                "logic": "The core causal chain is broken.",
                "action": "Exit the active thesis.",
            },
        ],
        "action_rules": [
            {
                "action_rule_id": "msft-ar-add",
                "kind": "add",
                "condition": "Copilot enterprise penetration breaks above 10% and CapEx growth moderates.",
                "action": "Add after earnings confirmation.",
            },
            {
                "action_rule_id": "msft-ar-trim",
                "kind": "trim",
                "condition": "CapEx rises again while Copilot monetization does not improve.",
                "action": "Trim into strength and lower conviction.",
            },
            {
                "action_rule_id": "msft-ar-exit",
                "kind": "exit",
                "condition": "Azure growth falls below 30% or flagship cloud access is materially impaired.",
                "action": "Exit active thesis and rotate to better risk/reward.",
            },
        ],
        "next_must_check_data": "FY2026 Q3 earnings: Azure growth, AI contribution, Copilot monetization, margin trend, and CapEx guidance.",
        "research_debt": [
            "Need a cleaner measure of paid Copilot seats versus trial activity.",
            "Need a better read on government cloud exposure to model-sourcing disputes.",
        ],
        "source_manifest": [
            {
                "source_id": "legacy-msft-note",
                "type": "local_markdown",
                "label": "Legacy MSFT AI market judgment",
                "url": "/Users/ro9air/STOCK/research/msft_ai_market_judgment.md",
            },
            {
                "source_id": "legacy-market-update",
                "type": "local_markdown",
                "label": "Legacy March 2026 market update",
                "url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
            },
            {
                "source_id": "sec",
                "type": "sec",
                "label": "SEC company submissions",
                "url": "https://data.sec.gov/submissions/CIK0000789019.json",
            },
            {
                "source_id": "investor_news",
                "type": "rss",
                "label": "Microsoft official news feed",
                "url": "https://news.microsoft.com/feed/",
            },
            {
                "source_id": "price",
                "type": "market_data",
                "label": "Yahoo Finance chart",
                "url": "https://query1.finance.yahoo.com/v8/finance/chart/MSFT?range=1mo&interval=1d",
            },
        ],
        "last_seen_event_cursors": {"sec": "", "investor_news": "", "price": ""},
        "version_log": [
            {
                "version": "v0",
                "date": "2026-03-25",
                "reason": "Baseline migration from legacy MSFT notes and March update.",
                "impact": "Established living thesis and machine-readable state.",
            }
        ],
        "seed_events": [
            {
                "event_id": "msft-seed-2026-azure-capex",
                "ticker": "MSFT",
                "source_type": "legacy_seed",
                "occurred_at": "2026-03-25",
                "title": "Q2 FY2026 Azure stayed strong but CapEx nearly reached $30B.",
                "source_url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
                "affected_assumption_ids": ["msft-a1", "msft-a3"],
                "marginal_impact": "-",
                "threshold_breach": True,
                "requires_refresh": True,
                "decision": "refresh",
                "metadata": {"seed": True},
            },
            {
                "event_id": "msft-seed-2026-copilot-adoption",
                "ticker": "MSFT",
                "source_type": "legacy_seed",
                "occurred_at": "2026-03-25",
                "title": "Copilot enterprise penetration remained near 3%, below expectations.",
                "source_url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
                "affected_assumption_ids": ["msft-a2"],
                "marginal_impact": "-",
                "threshold_breach": True,
                "requires_refresh": True,
                "decision": "refresh",
                "metadata": {"seed": True},
            },
        ],
    },
    "MAR": {
        "ticker": "MAR",
        "company_name": "Marriott International",
        "research_topic": "Light-asset travel compounder with business travel recovery optionality",
        "research_type": "中線 / 防禦配置",
        "holding_period": "數季至一年",
        "last_reviewed_at": "2026-03-25",
        "next_review_at": "2026-05-05",
        "current_action": "穩健持有",
        "confidence": 0.67,
        "latest_delta": [
            "Q4 2025 EPS 小幅 miss，但全年指引與高端/國際需求仍穩健。",
            "MAR 的 thesis 從疫情後修復轉成高品質現金流與商旅回溫的防禦型持有。",
            "若總經衰退擴散到高端與商務需求，才會進入 thesis breaker。",
        ],
        "primary_observation_variables": [
            "RevPAR by segment and geography",
            "Business travel recovery",
            "Capital-light cash return profile",
        ],
        "secondary_observation_variables": [
            "Forward bookings",
            "High-end leisure mix",
            "Macro slowdown risk",
        ],
        "noise_filters": [
            "Single-quarter EPS miss without RevPAR weakness",
            "Short-lived consumer sentiment noise",
            "Headline volatility in lower-end domestic travel",
        ],
        "thresholds": {
            "price_gap_pct": 8.0,
            "volume_ratio": 2.0,
            "deep_refresh_days": 10,
            "material_sec_forms": ["8-K", "10-Q", "10-K"],
            "earnings_keywords": ["earnings", "results", "guidance", "revpar", "dividend"],
            "positive_keywords": ["raises", "growth", "recovery", "booking", "revpar"],
            "negative_keywords": ["miss", "decline", "slowdown", "recession", "cut"],
        },
        "thesis": {
            "thesis_id": "mar-thesis-core",
            "statement": "Marriott 受惠於輕資產模式、高端與國際旅遊韌性，以及企業差旅回溫，因此在景氣不確定環境下仍能維持穩定現金流與較佳下行保護。",
            "core_catalyst": "Business travel recovery and stable international/high-end RevPAR.",
            "market_blind_spot": "市場容易把 MAR 當純週期股，但其資本輕、品牌強與回購能力提供了更好的防禦質地。",
            "verification_date": "2026-05-05",
            "expiry_condition": "High-end and business travel demand crack together in a deeper macro slowdown.",
        },
        "assumptions": [
            {
                "assumption_id": "mar-a1",
                "statement": "High-end and international travel remain resilient enough to offset weaker low-end domestic demand.",
                "type": "demand",
                "verification_method": "RevPAR mix and management commentary by segment.",
                "update_frequency": "quarterly",
                "invalidation_condition": "High-end and international RevPAR both roll over materially.",
                "status": "reinforced",
                "confidence": 0.70,
                "keywords": ["revpar", "luxury", "international", "travel"],
            },
            {
                "assumption_id": "mar-a2",
                "statement": "Business travel improves through 2026 and supports occupancy and pricing.",
                "type": "demand",
                "verification_method": "Corporate booking and occupancy commentary.",
                "update_frequency": "quarterly",
                "invalidation_condition": "Corporate travel recovery stalls for another full cycle.",
                "status": "watch",
                "confidence": 0.61,
                "keywords": ["business", "corporate", "booking", "conference"],
            },
            {
                "assumption_id": "mar-a3",
                "statement": "The asset-light model preserves downside protection and cash return flexibility.",
                "type": "capital_allocation",
                "verification_method": "Cash return guidance, leverage, and fee-based earnings mix.",
                "update_frequency": "quarterly",
                "invalidation_condition": "Fee earnings weaken materially and leverage rises without demand support.",
                "status": "reinforced",
                "confidence": 0.69,
                "keywords": ["cash", "buyback", "dividend", "asset-light", "fee"],
            },
        ],
        "risks": [
            {
                "risk_id": "mar-r1",
                "statement": "Macro recession broadens from budget travel to high-end and business travel.",
                "tier": "thesis breaker",
                "leading_indicator": "Forward bookings and corporate travel commentary",
                "response": "Exit if premium segments crack together.",
            },
            {
                "risk_id": "mar-r2",
                "statement": "International travel momentum fades as FX or geopolitics worsen.",
                "tier": "thesis weakener",
                "leading_indicator": "International RevPAR mix",
                "response": "Trim and lower the valuation range.",
            },
            {
                "risk_id": "mar-r3",
                "statement": "Market rotates away from quality defensives even if fundamentals hold.",
                "tier": "noise",
                "leading_indicator": "Factor rotation and bond-yield shocks",
                "response": "Ignore unless fundamentals deteriorate.",
            },
        ],
        "valuation_regime": {
            "current_yardstick": "Hotel-cycle P/E plus RevPAR outlook",
            "better_yardstick": "Quality fee-based travel compounder",
            "switch_trigger": "Business travel recovery becomes visible while premium segments stay resilient.",
            "re_rating_logic": "The market pays for durable fee earnings and cash returns rather than pure cycle recovery.",
            "associated_risk": "If the cycle weakens across all segments, the quality premium disappears.",
        },
        "scenarios": [
            {
                "scenario_id": "mar-s-base",
                "trigger": "Premium and international demand remain healthy and business travel improves gradually.",
                "logic": "MAR compounds through a quality earnings profile rather than a hot cycle.",
                "action": "Hold as defensive quality exposure.",
            },
            {
                "scenario_id": "mar-s-bull",
                "trigger": "Corporate travel snaps back and forward bookings beat expectations.",
                "logic": "The market re-rates MAR from cycle recovery to durable compounding.",
                "action": "Add on confirmation from RevPAR and bookings.",
            },
            {
                "scenario_id": "mar-s-bear",
                "trigger": "Budget weakness starts leaking into premium segments.",
                "logic": "The thesis weakens but cash-return quality still matters.",
                "action": "Trim, but do not exit until premium demand clearly breaks.",
            },
            {
                "scenario_id": "mar-s-break",
                "trigger": "Deep recession hits business and premium travel together.",
                "logic": "Downside protection is no longer enough to support the valuation.",
                "action": "Exit.",
            },
        ],
        "action_rules": [
            {
                "action_rule_id": "mar-ar-add",
                "kind": "add",
                "condition": "Corporate travel and forward bookings improve while international RevPAR remains strong.",
                "action": "Add selectively after management confirms trend persistence.",
            },
            {
                "action_rule_id": "mar-ar-trim",
                "kind": "trim",
                "condition": "Premium segment demand softens without offsetting business-travel recovery.",
                "action": "Trim and keep only defensive core size.",
            },
            {
                "action_rule_id": "mar-ar-exit",
                "kind": "exit",
                "condition": "High-end and business travel weaken together in a deeper recession.",
                "action": "Exit the active thesis.",
            },
        ],
        "next_must_check_data": "Next earnings: RevPAR mix, corporate travel commentary, forward bookings, and cash return guidance.",
        "research_debt": [
            "Need a cleaner framework for group and convention demand sensitivity.",
            "Need cross-check on Europe and Asia RevPAR versus US softness.",
        ],
        "source_manifest": [
            {
                "source_id": "legacy-market-update",
                "type": "local_markdown",
                "label": "Legacy March 2026 market update",
                "url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
            },
            {
                "source_id": "sec",
                "type": "sec",
                "label": "SEC company submissions",
                "url": "https://data.sec.gov/submissions/CIK0001048286.json",
            },
            {
                "source_id": "investor_news",
                "type": "html",
                "label": "Marriott investor news releases",
                "url": "https://news.marriott.com/news/",
            },
            {
                "source_id": "price",
                "type": "market_data",
                "label": "Yahoo Finance chart",
                "url": "https://query1.finance.yahoo.com/v8/finance/chart/MAR?range=1mo&interval=1d",
            },
        ],
        "last_seen_event_cursors": {"sec": "", "investor_news": "", "price": ""},
        "version_log": [
            {
                "version": "v0",
                "date": "2026-03-25",
                "reason": "Baseline migration from legacy March update.",
                "impact": "Established living thesis and machine-readable state.",
            }
        ],
        "seed_events": [
            {
                "event_id": "mar-seed-2026-guidance",
                "ticker": "MAR",
                "source_type": "legacy_seed",
                "occurred_at": "2026-03-25",
                "title": "2026 guidance stayed intact despite a small EPS miss.",
                "source_url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
                "affected_assumption_ids": ["mar-a1", "mar-a3"],
                "marginal_impact": "+",
                "threshold_breach": False,
                "requires_refresh": False,
                "decision": "watch",
                "metadata": {"seed": True},
            },
            {
                "event_id": "mar-seed-2026-travel-mix",
                "ticker": "MAR",
                "source_type": "legacy_seed",
                "occurred_at": "2026-03-25",
                "title": "High-end and international travel stayed firm while lower-end US demand softened.",
                "source_url": "/Users/ro9air/STOCK/research/market_update_mar2026.md",
                "affected_assumption_ids": ["mar-a1", "mar-a2"],
                "marginal_impact": "0",
                "threshold_breach": False,
                "requires_refresh": False,
                "decision": "watch",
                "metadata": {"seed": True},
            },
        ],
    },
}


def _ticker_dir(research_root: Path, ticker: str) -> Path:
    return research_root / ticker


def bootstrap_baselines(research_root: Path = RESEARCH_ROOT, force: bool = False) -> list[str]:
    created: list[str] = []
    for ticker, profile in BASELINE_PROFILES.items():
        state = normalize_state_contract(deepcopy(profile), default_stage="active", default_origin="manual_watchlist")
        ticker_dir = _ticker_dir(research_root, ticker)
        state_path = ticker_dir / "state.json"
        current_path = ticker_dir / "current.md"
        events_path = ticker_dir / "events.jsonl"
        artifacts_dir = ticker_dir / "artifacts"
        if not force and state_path.exists():
            continue
        ticker_dir.mkdir(parents=True, exist_ok=True)
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        recent_events = deepcopy(profile["seed_events"])
        write_json(state_path, state)
        current_path.write_text(render_current_report(state, recent_events), encoding="utf-8")
        (ticker_dir / "current.zh-tw.md").write_text(
            render_current_report(state, recent_events),
            encoding="utf-8",
        )
        write_jsonl(events_path, recent_events)
        write_json(
            artifacts_dir / "review_summary.json",
            {
                "ticker": ticker,
                "reviewed_at": state["last_reviewed_at"],
                "review_summary": "Baseline migration from legacy notes.",
                "changed_assumptions": [],
                "action_rule_delta": [],
            },
        )
        review_summary_markdown = render_review_summary(
            state,
            "Baseline migration from legacy notes.",
            [],
            [],
        )
        (artifacts_dir / "review_summary.md").write_text(
            review_summary_markdown,
            encoding="utf-8",
        )
        (artifacts_dir / "review_summary.zh-tw.md").write_text(
            review_summary_markdown,
            encoding="utf-8",
        )
        created.append(ticker)

    system_root = research_root / "system"
    system_root.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Source Registry",
        "",
        "This file is generated for operators. The runtime source-of-truth stays in `source_registry.json`.",
        "",
    ]
    for ticker, config in WATCHLIST.items():
        lines.extend([f"## {ticker}", ""])
        for source in config.sources:
            lines.append(
                f"- `{source.source_id}` ({source.kind}, {source.status}) priority {source.priority}: {source.url}"
            )
        lines.append("")
    (system_root / "source_registry.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    risk_policy_path = system_root / "risk_policy.json"
    if force or not risk_policy_path.exists():
        write_json(risk_policy_path, DEFAULT_RISK_POLICY)
    ensure_observation_system_files(research_root, force=force)
    sync_candidate_queue(research_root)
    return created
