function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function currentPage() {
  return document.body.dataset.dashboardPage;
}

const dashboardRuntime = {
  portfolioPayload: null,
  currentPayload: null,
  observationWorkspace: null,
};

function siteHref(path) {
  if (!path) return "#";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  const prefix = currentPage() === "portfolio" ? "./" : "../";
  return `${prefix}${path}`;
}

function linkMarkup(path, label, className = "inline-link") {
  if (!path) return "";
  return `<a class="${className}" href="${escapeHtml(siteHref(path))}">${escapeHtml(label)}</a>`;
}

function emptyState(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function pill(label, value) {
  return `<div class="pill"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function badgeClass(label = "") {
  const text = String(label);
  if (/(退出|高風險|失敗|critical|恐慌|Missing)/i.test(text)) return "badge badge-alert";
  if (/(壓力|De-risk|Prototype|Basic|偏緊|高於上限)/i.test(text)) return "badge badge-warning";
  if (/(平穩|健康|穩定|偏多|Complete|接近目標)/i.test(text)) return "badge badge-calm";
  if (/(觀察|追蹤|N\/A|Private only)/i.test(text)) return "badge badge-info";
  return "badge";
}

function alertClass(level = "") {
  const normalized = String(level).toLowerCase();
  if (normalized === "critical") return "badge badge-alert";
  if (normalized === "high") return "badge badge-warning";
  if (normalized === "medium") return "badge badge-info";
  return "badge";
}

function formatMaybe(value, fallback = "N/A") {
  return value == null || value === "" ? fallback : String(value);
}

function limitItems(items, limit) {
  return Array.isArray(items) ? items.slice(0, limit) : [];
}

function hasPrivateOverlay(payload) {
  return Boolean(payload?.portfolio_totals?.has_private_positions);
}

function collectRiskAlerts(payload) {
  const alerts = [];
  for (const card of payload.tickers ?? []) {
    for (const alert of card.position?.risk_alerts ?? []) {
      alerts.push({ ...alert, ticker: card.ticker, company_name: card.company_name });
    }
  }
  return alerts;
}

function collectExceptions(tickers) {
  const exceptions = [];
  for (const ticker of tickers ?? []) {
    for (const event of ticker.key_events ?? []) {
      if (event.metadata?.is_exception) {
        exceptions.push({
          ticker: ticker.ticker,
          title: event.title,
          occurred_at: event.occurred_at,
          type: event.metadata.exception_type,
          severity: event.metadata.severity ?? "high",
        });
      }
    }
  }
  return exceptions;
}

function supportsObservationActions(payload) {
  return Boolean(payload?.observation_actions_enabled);
}

function observationApiBaseUrl(payload) {
  if (payload?.api_base_url) return payload.api_base_url;
  const url = new URL(window.location.href);
  const host = url.hostname || "127.0.0.1";
  if (url.port === "8000" || url.port === "3000") {
    return `${url.protocol}//${host}:8001`;
  }
  return `http://${host}:8001`;
}

function emptyObservationWorkspace() {
  return {
    summary: {
      total_count: 0,
      open_count: 0,
      ready_count: 0,
      promoted_count: 0,
      dismissed_count: 0,
      average_score: 0,
    },
    items: [],
    watchlist_recommendations: [],
  };
}

async function loadObservationWorkspace(payload) {
  if (!supportsObservationActions(payload)) {
    dashboardRuntime.observationWorkspace = emptyObservationWorkspace();
    return dashboardRuntime.observationWorkspace;
  }
  const response = await fetch(`${observationApiBaseUrl(payload)}/api/observations`);
  if (!response.ok) {
    throw new Error(`Observation API HTTP ${response.status}`);
  }
  const workspace = await response.json();
  dashboardRuntime.observationWorkspace = workspace;
  return workspace;
}

async function postObservationCommand(payload, route, body) {
  const response = await fetch(`${observationApiBaseUrl(payload)}${route}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Observation API HTTP ${response.status}`);
  }
  dashboardRuntime.observationWorkspace = data.workspace || emptyObservationWorkspace();
  return data;
}

function observationForTicker(workspace, ticker) {
  return (workspace?.items ?? []).find((item) => item.ticker === ticker && /^(open|ready_for_candidate)$/.test(item.status));
}

function reportObservationError(error) {
  console.error(error);
  window.alert(`Observation command failed: ${error.message}`);
}

function renderPortfolioStrip(payload) {
  const strip = document.getElementById("portfolio-summary-strip");
  if (!strip) return;
  const summary = payload.portfolio_summary;
  const totals = payload.portfolio_totals;
  const macro = payload.macro_regime;
  strip.innerHTML = [
    pill("更新時間", payload.generated_at),
    pill("追蹤標的", `${summary.tracked_ticker_count} 檔`),
    pill("真實部位", hasPrivateOverlay(payload) ? `${totals.held_ticker_count} 檔` : "Private off"),
    pill("VIX regime", `${macro.label} ${macro.value_label}`),
    pill("風險警報", `${totals.active_alert_count ?? 0} 則`),
  ].join("");
}

function renderPortfolioTotals(payload) {
  const root = document.getElementById("portfolio-totals-panel");
  if (!root) return;
  const totals = payload.portfolio_totals;
  const privateNote = hasPrivateOverlay(payload)
    ? "本機 private overlay 已啟用，以下 metrics 以你的真實成本與持股數為準。"
    : "目前顯示的是 sanitized public 視圖；啟用 private overlay 後才會看到成本、P/L 與 sizing。";
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Portfolio Totals</p>
        <h2>真實組合總覽</h2>
      </div>
      <span class="${badgeClass(hasPrivateOverlay(payload) ? "Private on" : "Private off")}">${hasPrivateOverlay(payload) ? "Private on" : "Private off"}</span>
    </div>
    <div class="hero-grid">
      <div class="metric-tile">
        <p class="metric-label">Cost Basis</p>
        <div class="metric-figure">${escapeHtml(formatMaybe(totals.cost_basis_label, "Private only"))}</div>
        <p class="metric-caption">${escapeHtml(privateNote)}</p>
      </div>
      <div class="metric-tile">
        <p class="metric-label">Market Value</p>
        <div class="metric-figure">${escapeHtml(formatMaybe(totals.market_value_label, "Private only"))}</div>
        <p class="metric-caption">As of ${escapeHtml(formatMaybe(totals.as_of, "N/A"))}</p>
      </div>
      <div class="metric-tile">
        <p class="metric-label">Unrealized P/L</p>
        <div class="metric-figure">${escapeHtml(formatMaybe(totals.unrealized_pnl_label, "Private only"))}</div>
        <p class="metric-caption">${escapeHtml(formatMaybe(totals.unrealized_pnl_pct_label, "N/A"))}</p>
      </div>
      <div class="metric-tile">
        <p class="metric-label">Largest Position</p>
        <div class="metric-figure">${escapeHtml(formatMaybe(totals.largest_position_ticker, "N/A"))}</div>
        <p class="metric-caption">${escapeHtml(formatMaybe(totals.largest_position_weight_pct != null ? `${totals.largest_position_weight_pct.toFixed(2)}%` : null, "N/A"))}</p>
      </div>
    </div>
  `;
}

function renderMacroRegime(payload) {
  const root = document.getElementById("macro-regime-panel");
  if (!root) return;
  const macro = payload.macro_regime;
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Macro Regime</p>
        <h2>VIX 風險閥</h2>
      </div>
      <span class="${badgeClass(macro.label)}">${escapeHtml(macro.label)}</span>
    </div>
    <div class="overview-list">
      <div class="data-point"><span>VIX</span><strong>${escapeHtml(macro.value_label)}</strong></div>
      <div class="data-point"><span>Size Multiplier</span><strong>${escapeHtml(`${(macro.size_multiplier ?? 1).toFixed(2)}x`)}</strong></div>
      <div class="data-point"><span>Review Urgency</span><strong>${escapeHtml(formatMaybe(macro.review_urgency, "normal"))}</strong></div>
    </div>
    <p class="footer-note">${escapeHtml(macro.summary || "Macro regime unavailable.")}</p>
  `;
}

function renderRiskRadar(payload) {
  const root = document.getElementById("risk-radar-panel");
  if (!root) return;
  const alerts = collectRiskAlerts(payload);
  if (!alerts.length) {
    root.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="panel-kicker">Risk Radar</p>
          <h2>當前警報</h2>
        </div>
      </div>
      ${emptyState("目前沒有 active risk alerts。")}
    `;
    return;
  }
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Risk Radar</p>
        <h2>當前警報</h2>
      </div>
      <span class="badge badge-alert">${alerts.length} 則</span>
    </div>
    <div class="alert-list">
      ${alerts.slice(0, 4).map((alert) => `
        <article class="alert-card" data-level="${escapeHtml(alert.level)}">
          <div class="row-between">
            <h3>${escapeHtml(alert.ticker)}｜${escapeHtml(alert.title)}</h3>
            <span class="${alertClass(alert.level)}">${escapeHtml(alert.level)}</span>
          </div>
          <p>${escapeHtml(alert.message)}</p>
          <p class="footer-note">${escapeHtml(alert.action)}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function renderRecentProgress(payload) {
  const root = document.getElementById("recent-progress-panel");
  if (!root) return;
  const items = limitItems(payload.recent_progress ?? [], 4);
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Recent Progress</p>
        <h2>最近成果</h2>
      </div>
    </div>
    <div class="progress-list">
      ${items.map((item) => `
        <article class="summary-metric">
          <div class="metric-label">${escapeHtml(item.label)}</div>
          <div class="metric-value">${escapeHtml(item.value)}</div>
          <p>${escapeHtml(item.detail)}</p>
        </article>
      `).join("") || emptyState("目前沒有 recent progress 資料。")}
    </div>
  `;
}

function renderGapMap(payload) {
  const root = document.getElementById("gap-map-panel");
  if (!root) return;
  const items = limitItems(payload.project_maturity ?? [], 4);
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Gap Map</p>
        <h2>Institutional Gap Map</h2>
      </div>
    </div>
    <div class="maturity-grid">
      ${items.map((item) => `
        <article class="maturity-card" data-status="${escapeHtml(item.status)}">
          <div class="row-between">
            <h3>${escapeHtml(item.label)}</h3>
            <span class="${badgeClass(item.status_label)}">${escapeHtml(item.status_label)}</span>
          </div>
          <p>${escapeHtml(item.summary)}</p>
        </article>
      `).join("")}
    </div>
    <p class="footer-note">首頁先顯示最關鍵的 4 個能力節點；其餘缺口留在總覽摘要。</p>
  `;
}

function renderDotRow(count, maxDots = 10) {
  const safe = Math.max(0, Math.min(maxDots, parseInt(count, 10) || 0));
  const w = maxDots * 12;
  return `<svg width="${w}" height="12" style="margin-bottom:8px; display:block;">${
    Array.from({ length: maxDots }, (_, i) =>
      `<circle cx="${6 + i * 12}" cy="6" r="4.5" fill="${i < safe ? "var(--accent-amber, #e8a837)" : "#1a2332"}" />`
    ).join("")
  }</svg>`;
}

function renderAnalytics(payload) {
  const root = document.getElementById("analytics-panel");
  if (!root) return;
  const analytics = payload.post_mortem_analytics ?? {};

  const safeRate = Math.min(100, Math.max(0, Number(analytics.hit_rate_pct) || 0));

  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Review Performance</p>
        <h2>決策回測</h2>
      </div>
    </div>
    <div class="analytics-metrics">
      <article class="summary-metric">
        <div class="metric-label">Assumption Hit Rate</div>
        <svg width="100%" height="8" style="margin-bottom:8px; display:block;">
          <rect width="100%" height="8" rx="4" fill="#1a2332" />
          <rect width="${safeRate}%" height="8" rx="4" fill="var(--accent-amber, #e8a837)" />
        </svg>
        <div class="metric-value">${escapeHtml(formatMaybe(analytics.hit_rate_pct != null ? `${analytics.hit_rate_pct}%` : null, "0%"))}</div>
        <p>${escapeHtml(`${analytics.assumptions_correct ?? 0}/${analytics.assumptions_resolved ?? 0} resolved assumptions`)}</p>
      </article>
      <article class="summary-metric">
        <div class="metric-label">Regime Drifts</div>
        ${renderDotRow(analytics.regime_drift_events)}
        <div class="metric-value">${escapeHtml(formatMaybe(analytics.regime_drift_events, "0"))}</div>
        <p>估值體系與判斷 yardstick 發生位移的事件數。</p>
      </article>
      <article class="summary-metric">
        <div class="metric-label">Expectation Gaps</div>
        ${renderDotRow(analytics.expectation_gap_events)}
        <div class="metric-value">${escapeHtml(formatMaybe(analytics.expectation_gap_events, "0"))}</div>
        <p>基本面與價格反應之間已被記錄的預期差事件。</p>
      </article>
    </div>
  `;
}

function renderSummaryCards(payload) {
  const summary = payload.portfolio_summary;
  const totals = payload.portfolio_totals;
  const root = document.getElementById("summary-cards");
  if (!root) return;
  root.innerHTML = `
    <article class="stat-card">
      <p>投資邏輯狀態</p>
      <strong>${escapeHtml(summary.thesis_health_label)}</strong>
      <p>平均健康度 ${Math.round(summary.thesis_health_score * 100)}%，平均信心 ${Math.round(summary.average_confidence * 100)}%。</p>
    </article>
    <article class="stat-card">
      <p>待追蹤事件</p>
      <strong>${escapeHtml(summary.pending_event_count)}</strong>
      <p>近一輪需要 watch / refresh 的事件總數。</p>
    </article>
    <article class="stat-card">
      <p>一週內需檢查</p>
      <strong>${escapeHtml(summary.review_due_count)}</strong>
      <p>${escapeHtml(summary.upcoming_tickers.join("、") || "目前沒有迫近的例行複盤。")}</p>
    </article>
    <article class="stat-card">
      <p>持倉覆蓋</p>
      <strong>${escapeHtml(hasPrivateOverlay(payload) ? `${totals.held_ticker_count} / ${summary.tracked_ticker_count}` : `0 / ${summary.tracked_ticker_count}`)}</strong>
      <p>${escapeHtml(hasPrivateOverlay(payload) ? "真實部位已接上 private overlay。" : "目前仍是 sanitized public 視圖。")}</p>
    </article>
  `;
}

function renderPriorityQueue(payload) {
  const root = document.getElementById("priority-queue");
  if (!root) return;
  if (!payload.priority_queue?.length) {
    root.innerHTML = emptyState("目前沒有需要優先處理的標的。");
    return;
  }
  root.innerHTML = payload.priority_queue.map((item) => `
    <article class="priority-item">
      <div class="row-between">
        <div>
          <h3>${escapeHtml(item.ticker)}｜${escapeHtml(item.company_name)}</h3>
          <p>${escapeHtml(item.reason)}</p>
        </div>
        <span class="${badgeClass(item.priority_label)}">${escapeHtml(item.priority_label)}</span>
      </div>
      <div class="timeline-meta">
        ${linkMarkup(item.detail_path, "打開決策頁")}
        ${linkMarkup(item.research_path, "打開研究內頁")}
      </div>
    </article>
  `).join("");
}

function renderExceptionQueue(payload) {
  const container = document.getElementById("exception-queue");
  const board = document.getElementById("exception-board");
  if (!container || !board) return;
  const exceptions = collectExceptions(payload.tickers);
  if (!exceptions.length) {
    board.style.display = "none";
    return;
  }
  board.style.display = "block";
  container.innerHTML = exceptions.map((item) => `
    <a class="priority-item" href="${escapeHtml(siteHref(`tickers/${item.ticker}.html`))}">
      <div class="row-between">
        <div>
          <h3>${escapeHtml(item.ticker)}｜${escapeHtml(item.type)}</h3>
          <p>${escapeHtml(item.title)}</p>
        </div>
        <span class="${alertClass(item.severity)}">${escapeHtml(item.severity)}</span>
      </div>
      <div class="timeline-meta">
        <span class="sub-badge">${escapeHtml(item.occurred_at)}</span>
      </div>
    </a>
  `).join("");
}

function renderGapSummary(payload) {
  const root = document.getElementById("gap-summary-panel");
  if (!root) return;
  const items = payload.project_maturity ?? [];
  const counts = {
    complete: items.filter((item) => item.status === "complete").length,
    prototype: items.filter((item) => item.status === "prototype").length,
    basic: items.filter((item) => item.status === "basic").length,
    missing: items.filter((item) => item.status === "missing").length,
  };
  root.innerHTML = `
    <article class="stat-card">
      <p>Complete</p>
      <strong>${counts.complete}</strong>
      <p>基礎研究作業系統與輸出面已能穩定運作。</p>
    </article>
    <article class="stat-card">
      <p>Prototype / Basic</p>
      <strong>${counts.prototype + counts.basic}</strong>
      <p>已有原型，但尚未達到機構級穩定度。</p>
    </article>
    <article class="stat-card">
      <p>Missing</p>
      <strong>${counts.missing}</strong>
      <p>風控熔斷、sizing engine、VIX macro overlay 都屬於本輪補強重點。</p>
    </article>
  `;
}

function parseListInput(value) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function ensureObservationModal(payload) {
  if (!supportsObservationActions(payload)) return null;
  const root = document.getElementById("observation-modal-root");
  if (!root || root.dataset.ready === "true") return root;
  root.innerHTML = `
    <div class="observation-modal-shell" id="observation-modal" hidden>
      <div class="observation-modal-backdrop" data-close-modal="true"></div>
      <div class="observation-modal-card">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Observation Intake</p>
            <h2>開啟觀察</h2>
          </div>
          <button type="button" class="action-button action-button-ghost" data-close-modal="true">關閉</button>
        </div>
        <form id="observation-form" class="observation-form">
          <label class="field">
            <span>Ticker</span>
            <input id="observation-ticker" name="ticker" required>
          </label>
          <label class="field">
            <span>Company</span>
            <input id="observation-company" name="company_name" required>
          </label>
          <label class="field">
            <span>持有期</span>
            <input id="observation-horizon" name="intended_horizon" value="3-12 months" required>
          </label>
          <label class="field">
            <span>來源關係</span>
            <select id="observation-opened-from" name="opened_from">
              <option value="manual">manual</option>
              <option value="company">company</option>
              <option value="peer">peer</option>
              <option value="supply_chain">supply_chain</option>
            </select>
          </label>
          <label class="field">
            <span>Theme IDs</span>
            <input id="observation-theme-ids" name="theme_ids" placeholder="ai-platforms, decision-os">
          </label>
          <label class="field">
            <span>Peer Refs</span>
            <input id="observation-peer-refs" name="peer_refs" placeholder="MSFT, GOOGL">
          </label>
          <label class="field">
            <span>Chain Refs</span>
            <input id="observation-chain-refs" name="chain_refs" placeholder="NVDA, SABR">
          </label>
          <label class="field field-wide">
            <span>Why now</span>
            <textarea id="observation-why-now" name="why_now" rows="4" required></textarea>
          </label>
          <p class="footer-note" id="observation-selected-events-note">目前未選擇事件，會建立純手動 observation item。</p>
          <div class="timeline-meta">
            <button type="submit" class="action-button">建立觀察</button>
            <button type="button" class="action-button action-button-ghost" data-close-modal="true">取消</button>
          </div>
        </form>
      </div>
    </div>
  `;
  root.dataset.ready = "true";
  root.dataset.selectedEvents = "[]";
  root.querySelectorAll("[data-close-modal='true']").forEach((element) => {
    element.addEventListener("click", () => closeObservationModal());
  });
  root.querySelector("#observation-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const basePayload = dashboardRuntime.currentPayload || dashboardRuntime.portfolioPayload;
    if (!basePayload) return;
    const selectedEvents = JSON.parse(root.dataset.selectedEvents || "[]");
    const form = event.currentTarget;
    const command = {
      ticker: form.querySelector("#observation-ticker").value.trim().toUpperCase(),
      company_name: form.querySelector("#observation-company").value.trim(),
      intended_horizon: form.querySelector("#observation-horizon").value.trim(),
      opened_from: form.querySelector("#observation-opened-from").value,
      theme_ids: parseListInput(form.querySelector("#observation-theme-ids").value),
      peer_refs: parseListInput(form.querySelector("#observation-peer-refs").value),
      chain_refs: parseListInput(form.querySelector("#observation-chain-refs").value),
      why_now: form.querySelector("#observation-why-now").value.trim(),
      selected_events: selectedEvents,
    };
    try {
      await postObservationCommand(basePayload, "/api/observations/open", command);
      closeObservationModal();
      await refreshObservationViews(basePayload);
    } catch (error) {
      reportObservationError(error);
    }
  });
  return root;
}

function closeObservationModal() {
  const modal = document.getElementById("observation-modal");
  const root = document.getElementById("observation-modal-root");
  if (!modal || !root) return;
  modal.hidden = true;
  root.dataset.selectedEvents = "[]";
}

function openObservationModal(payload, prefill = {}) {
  const root = ensureObservationModal(payload);
  if (!root) return;
  const modal = document.getElementById("observation-modal");
  const selectedEvents = prefill.selectedEvents || [];
  root.dataset.selectedEvents = JSON.stringify(selectedEvents);
  root.querySelector("#observation-ticker").value = prefill.ticker || "";
  root.querySelector("#observation-company").value = prefill.company_name || "";
  root.querySelector("#observation-horizon").value = prefill.intended_horizon || "3-12 months";
  root.querySelector("#observation-opened-from").value = prefill.opened_from || "manual";
  root.querySelector("#observation-theme-ids").value = (prefill.theme_ids || []).join(", ");
  root.querySelector("#observation-peer-refs").value = (prefill.peer_refs || []).join(", ");
  root.querySelector("#observation-chain-refs").value = (prefill.chain_refs || []).join(", ");
  root.querySelector("#observation-why-now").value = prefill.why_now || "";
  root.querySelector("#observation-selected-events-note").textContent = selectedEvents.length
    ? `這次會一起納入 ${selectedEvents.length} 筆事件。`
    : "目前未選擇事件，會建立純手動 observation item。";
  modal.hidden = false;
}

function recommendationById(workspace, suggestionId) {
  return (workspace?.watchlist_recommendations ?? []).find((item) => item.suggestion_id === suggestionId);
}

function renderObservationCommandPanel(payload, workspace) {
  const root = document.getElementById("observation-command-panel");
  if (!root) return;
  if (!supportsObservationActions(payload)) {
    root.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="panel-kicker">Observation Intake</p>
          <h2>開啟觀察</h2>
        </div>
      </div>
      ${emptyState("Observation controls 只在 local cockpit 開放。")}
    `;
    return;
  }
  const summary = workspace?.summary ?? emptyObservationWorkspace().summary;
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Observation Intake</p>
        <h2>觀察湖控制台</h2>
      </div>
      <button type="button" class="action-button" data-action="open-observation">開啟觀察</button>
    </div>
    <div class="analytics-metrics">
      <article class="summary-metric">
        <div class="metric-label">Open</div>
        <div class="metric-value">${escapeHtml(summary.open_count)}</div>
        <p>目前仍在累積事件的 observation items。</p>
      </article>
      <article class="summary-metric">
        <div class="metric-label">Ready</div>
        <div class="metric-value">${escapeHtml(summary.ready_count)}</div>
        <p>已達建議升級門檻，但仍需你手動確認。</p>
      </article>
      <article class="summary-metric">
        <div class="metric-label">Avg Score</div>
        <div class="metric-value">${escapeHtml(Number(summary.average_score || 0).toFixed(2))}</div>
        <p>Observation lake 當前平均分數。</p>
      </article>
    </div>
    <p class="footer-note">本區只寫入 local cockpit；public site 不會暴露觀察池內容。</p>
  `;
  root.onclick = (event) => {
    const trigger = event.target.closest("[data-action='open-observation']");
    if (!trigger) return;
    openObservationModal(payload, {});
  };
}

function renderObservationLakePanel(payload, workspace) {
  const root = document.getElementById("observation-lake-panel");
  if (!root) return;
  if (!supportsObservationActions(payload)) {
    root.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="panel-kicker">Observation Lake</p>
          <h2>Observation Lake</h2>
        </div>
      </div>
      ${emptyState("Observation lake 僅在 local cockpit 顯示。")}
    `;
    return;
  }
  const items = limitItems(workspace?.items ?? [], 5);
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Observation Lake</p>
        <h2>新觀察名單池</h2>
      </div>
    </div>
    <div class="observation-list">
      ${items.map((item) => `
        <article class="observation-card">
          <div class="row-between">
            <h3>${escapeHtml(item.ticker)}｜${escapeHtml(item.company_name)}</h3>
            <span class="${badgeClass(item.score_label)}">${escapeHtml(item.score_label)}</span>
          </div>
          <p>${escapeHtml(item.why_now || "尚未補充 why now。")}</p>
          <div class="timeline-meta">
            <span class="sub-badge">Score ${escapeHtml(Number(item.score || 0).toFixed(2))}</span>
            <span class="${badgeClass(item.status)}">${escapeHtml(item.status)}</span>
            <span class="sub-badge">${escapeHtml(item.event_count)} events</span>
          </div>
          <p class="footer-note">${escapeHtml(item.promotion_recommendation?.reason || "")}</p>
          <div class="timeline-meta">
            ${item.promotion_recommendation?.eligible ? `<button type="button" class="action-button" data-action="promote-observation" data-observation-id="${escapeHtml(item.observation_id)}">升級成候選</button>` : ""}
            <button type="button" class="action-button action-button-ghost" data-action="dismiss-observation" data-observation-id="${escapeHtml(item.observation_id)}">Dismiss</button>
          </div>
        </article>
      `).join("") || emptyState("目前 observation lake 還沒有項目。")}
    </div>
  `;
  root.onclick = async (event) => {
    const promote = event.target.closest("[data-action='promote-observation']");
    const dismiss = event.target.closest("[data-action='dismiss-observation']");
    if (promote) {
      try {
        await postObservationCommand(payload, "/api/observations/promote", {
          observation_id: promote.dataset.observationId,
        });
        await refreshObservationViews(payload);
      } catch (error) {
        reportObservationError(error);
      }
      return;
    }
    if (dismiss) {
      try {
        await postObservationCommand(payload, "/api/observations/dismiss", {
          observation_id: dismiss.dataset.observationId,
        });
        await refreshObservationViews(payload);
      } catch (error) {
        reportObservationError(error);
      }
    }
  };
}

function renderWatchlistRecommendationsPanel(payload, workspace) {
  const root = document.getElementById("watchlist-recommendations-panel");
  if (!root) return;
  if (!supportsObservationActions(payload)) {
    root.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="panel-kicker">Watchlist Radar</p>
          <h2>New Watchlist Recommendations</h2>
        </div>
      </div>
      ${emptyState("Recommendations 只在 local cockpit 顯示。")}
    `;
    return;
  }
  const items = limitItems(workspace?.watchlist_recommendations ?? [], 6);
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Watchlist Radar</p>
        <h2>New Watchlist Recommendations</h2>
      </div>
    </div>
    <div class="observation-list">
      ${items.map((item) => `
        <article class="observation-card observation-card-compact">
          <div class="row-between">
            <h3>${escapeHtml(item.ticker)}｜${escapeHtml(item.company_name)}</h3>
            <span class="${badgeClass(item.relation_type)}">${escapeHtml(item.relation_type)}</span>
          </div>
          <p>${escapeHtml(item.why_now)}</p>
          <div class="timeline-meta">
            <span class="sub-badge">From ${escapeHtml(item.source_ticker)}</span>
            <span class="sub-badge">${escapeHtml(item.theme_ids.join(", "))}</span>
          </div>
          <div class="timeline-meta">
            <button type="button" class="action-button" data-action="open-suggestion" data-suggestion-id="${escapeHtml(item.suggestion_id)}">開啟觀察</button>
            ${item.existing_observation_id ? `<button type="button" class="action-button action-button-ghost" data-action="include-suggestion" data-suggestion-id="${escapeHtml(item.suggestion_id)}" data-observation-id="${escapeHtml(item.existing_observation_id)}">納入事件</button>` : ""}
          </div>
        </article>
      `).join("") || emptyState("目前沒有新的 observation 推薦。")}
    </div>
  `;
  root.onclick = async (event) => {
    const openTrigger = event.target.closest("[data-action='open-suggestion']");
    const includeTrigger = event.target.closest("[data-action='include-suggestion']");
    const workspaceNow = dashboardRuntime.observationWorkspace || workspace || emptyObservationWorkspace();
    if (openTrigger) {
      const suggestion = recommendationById(workspaceNow, openTrigger.dataset.suggestionId);
      if (!suggestion) return;
      openObservationModal(payload, {
        ticker: suggestion.ticker,
        company_name: suggestion.company_name,
        intended_horizon: suggestion.intended_horizon,
        opened_from: suggestion.opened_from,
        theme_ids: suggestion.theme_ids,
        why_now: suggestion.why_now,
        selectedEvents: suggestion.event_drafts,
      });
      return;
    }
    if (includeTrigger) {
      const suggestion = recommendationById(workspaceNow, includeTrigger.dataset.suggestionId);
      if (!suggestion) return;
      try {
        await postObservationCommand(payload, "/api/observations/include-events", {
          observation_id: includeTrigger.dataset.observationId,
          selected_events: suggestion.event_drafts,
        });
        await refreshObservationViews(payload);
      } catch (error) {
        reportObservationError(error);
      }
    }
  };
}

function relatedDraftFromTickerPayload(payload, relation) {
  const seed = payload.key_events?.[0];
  return {
    related_ticker: payload.ticker,
    relation_type: relation.relation_type,
    event_family: relation.relation_type === "supply_chain" ? "supply_chain_readthrough" : "peer_readthrough",
    occurred_at: seed?.occurred_at || payload.last_reviewed_at,
    title: seed?.title || `${payload.ticker} 投資邏輯需要延伸觀察 ${relation.ticker}`,
    summary: `${payload.ticker} 的最新事件與投資邏輯狀態，值得延伸觀察 ${relation.ticker}。`,
    signal_strength: seed?.metadata?.severity === "critical" ? "high" : "medium",
    source_url: seed?.href || payload.internal_research_path,
    is_primary_source: true,
    selected_for_watch: true,
    source_event_id: seed?.event_id || "",
    source_theme_id: payload.observation_context?.theme_id || "",
  };
}

function renderObservationRelatedPanel(payload, workspace) {
  const root = document.getElementById("observation-related-panel");
  if (!root) return;
  if (!supportsObservationActions(payload)) {
    root.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="panel-kicker">Observation Graph</p>
          <h2>相關觀察</h2>
        </div>
      </div>
      ${emptyState("Related observation actions 只在 local cockpit 顯示。")}
    `;
    return;
  }
  const context = payload.observation_context;
  if (!context) {
    root.innerHTML = `
      <div class="panel-head">
        <div>
          <p class="panel-kicker">Observation Graph</p>
          <h2>相關觀察</h2>
        </div>
      </div>
      ${emptyState("目前沒有 observation graph 設定。")}
    `;
    return;
  }
  const groups = [
    { label: "Peers", items: context.peers || [] },
    { label: "Upstream", items: context.upstream || [] },
    { label: "Downstream", items: context.downstream || [] },
  ];
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Observation Graph</p>
        <h2>相關觀察</h2>
      </div>
      <span class="badge badge-info">${escapeHtml(context.theme_id)}</span>
    </div>
    <div class="observation-groups">
      ${groups.map((group) => `
        <section class="observation-group">
          <h3>${escapeHtml(group.label)}</h3>
          <div class="compact-grid">
            ${group.items.map((item) => {
              const existing = observationForTicker(workspace, item.ticker);
              return `
                <article class="compact-card">
                  <div class="row-between">
                    <h3>${escapeHtml(item.ticker)}</h3>
                    <span class="${badgeClass(item.relation_type)}">${escapeHtml(item.relation_type)}</span>
                  </div>
                  <p>${escapeHtml(item.company_name)}</p>
                  <div class="timeline-meta">
                    <button type="button" class="action-button" data-action="open-related" data-ticker="${escapeHtml(item.ticker)}" data-company-name="${escapeHtml(item.company_name)}" data-relation-type="${escapeHtml(item.relation_type)}">開啟觀察</button>
                    ${existing ? `<button type="button" class="action-button action-button-ghost" data-action="include-related" data-observation-id="${escapeHtml(existing.observation_id)}" data-ticker="${escapeHtml(item.ticker)}" data-company-name="${escapeHtml(item.company_name)}" data-relation-type="${escapeHtml(item.relation_type)}">納入事件</button>` : ""}
                  </div>
                </article>
              `;
            }).join("") || emptyState("目前沒有相關標的。")}
          </div>
        </section>
      `).join("")}
    </div>
  `;
  root.onclick = async (event) => {
    const openTrigger = event.target.closest("[data-action='open-related']");
    const includeTrigger = event.target.closest("[data-action='include-related']");
    if (openTrigger) {
      const relation = {
        ticker: openTrigger.dataset.ticker,
        company_name: openTrigger.dataset.companyName,
        relation_type: openTrigger.dataset.relationType,
      };
      openObservationModal(payload, {
        ticker: relation.ticker,
        company_name: relation.company_name,
        intended_horizon: payload.observation_context?.default_horizon || "3-12 months",
        opened_from: relation.relation_type,
        theme_ids: [payload.observation_context?.theme_id].filter(Boolean),
        why_now: `${payload.ticker} 的關鍵事件值得延伸觀察 ${relation.ticker}。`,
        selectedEvents: [relatedDraftFromTickerPayload(payload, relation)],
      });
      return;
    }
    if (includeTrigger) {
      const relation = {
        ticker: includeTrigger.dataset.ticker,
        company_name: includeTrigger.dataset.companyName,
        relation_type: includeTrigger.dataset.relationType,
      };
      try {
        await postObservationCommand(payload, "/api/observations/include-events", {
          observation_id: includeTrigger.dataset.observationId,
          selected_events: [relatedDraftFromTickerPayload(payload, relation)],
        });
        await refreshObservationViews(payload);
      } catch (error) {
        reportObservationError(error);
      }
    }
  };
}

async function refreshObservationViews(basePayload) {
  await loadObservationWorkspace(basePayload);
  if (currentPage() === "portfolio") {
    const fresh = injectSharedPayload(await loadJson(`./data/portfolio.json?ts=${Date.now()}`));
    dashboardRuntime.portfolioPayload = fresh;
    renderPortfolio(fresh);
    return;
  }
  const fresh = injectSharedPayload(await loadJson(`${document.body.dataset.digestPath}?ts=${Date.now()}`));
  dashboardRuntime.currentPayload = fresh;
  renderDetailPage(fresh);
}

function cardRiskValue(card) {
  return {
    "high-conviction": 4,
    "core": 3,
    "satellite": 2,
    "trading": 1,
    "": 0,
  }[card.risk_level ?? ""] ?? 0;
}

function sortCards(cards, mode) {
  const cloned = [...cards];
  if (mode === "review") {
    return cloned.sort((a, b) => a.next_review_at.localeCompare(b.next_review_at));
  }
  if (mode === "risk") {
    return cloned.sort((a, b) => {
      const aAlerts = a.position?.risk_alert_count ?? 0;
      const bAlerts = b.position?.risk_alert_count ?? 0;
      return bAlerts - aAlerts || cardRiskValue(b) - cardRiskValue(a) || b.priority_score - a.priority_score;
    });
  }
  if (mode === "confidence") {
    return cloned.sort((a, b) => b.thesis_health.score - a.thesis_health.score || b.priority_score - a.priority_score);
  }
  return cloned.sort((a, b) => b.priority_score - a.priority_score || a.next_review_at.localeCompare(b.next_review_at));
}

function filterCards(cards) {
  const positionFilter = document.getElementById("position-filter")?.value ?? "all";
  const riskFilter = document.getElementById("risk-filter")?.value ?? "all";
  return cards.filter((card) => {
    if (positionFilter === "has-position" && !card.position.has_position) return false;
    if (positionFilter === "missing-position" && card.position.has_position) return false;
    if (riskFilter === "unset" && card.risk_level) return false;
    if (riskFilter !== "all" && riskFilter !== "unset" && card.risk_level !== riskFilter) return false;
    return true;
  });
}

function renderPortfolioCards(payload) {
  const grid = document.getElementById("portfolio-grid");
  const meta = document.getElementById("portfolio-grid-meta");
  if (!grid || !meta) return;
  const sortMode = document.getElementById("sort-select")?.value ?? "priority";
  const cards = sortCards(filterCards(payload.tickers), sortMode);
  meta.textContent = `目前顯示 ${cards.length} / ${payload.tickers.length} 檔。`;
  if (!cards.length) {
    grid.innerHTML = emptyState("目前沒有符合篩選條件的標的。");
    return;
  }
  grid.innerHTML = cards.map((card) => `
    <article class="card">
      <div class="card-top">
        <div>
          <h3 class="ticker">${escapeHtml(card.ticker)}</h3>
          <p class="company">${escapeHtml(card.company_name)}</p>
        </div>
        <span class="${badgeClass(card.status_label)}">${escapeHtml(card.status_label)}</span>
      </div>
      <p class="card-copy">${escapeHtml(card.summary_blurb)}</p>
      <div class="card-meta">
        <div class="meta-row"><span>部位摘要</span><strong>${escapeHtml(card.position.summary)}</strong></div>
        <div class="meta-row"><span>未實現 P/L</span><strong>${escapeHtml(card.position.unrealized_pnl_label || "Private only")} / ${escapeHtml(card.position.unrealized_pnl_pct_label || "N/A")}</strong></div>
        <div class="meta-row"><span>權重 / 調整後目標</span><strong>${escapeHtml(card.position.portfolio_weight_label || "N/A")} / ${escapeHtml(card.position.adjusted_target_weight_label || "N/A")}</strong></div>
        <div class="meta-row"><span>Sizing 狀態</span><strong>${escapeHtml(card.position.sizing_status?.label || "N/A")}</strong></div>
        <div class="meta-row"><span>風險警報</span><strong>${escapeHtml(`${card.position.risk_alert_count ?? 0} 則`)}</strong></div>
        <div class="meta-row"><span>下次檢查</span><strong>${escapeHtml(card.next_review_at)}</strong></div>
      </div>
      <div class="timeline-meta">
        <span class="sub-badge">${escapeHtml(card.recommended_next_action || card.current_action)}</span>
        <span class="${badgeClass(card.priority_label)}">${escapeHtml(card.priority_label)}</span>
        <span class="${badgeClass(card.risk_level_label)}">${escapeHtml(card.risk_level_label)}</span>
        <span class="${badgeClass(card.position.sizing_status?.label || "")}">${escapeHtml(card.position.sizing_status?.label || "N/A")}</span>
      </div>
      <div class="timeline-meta">
        ${linkMarkup(card.detail_path, "打開決策頁")}
        ${linkMarkup(card.internal_research_path, "研究內頁")}
      </div>
    </article>
  `).join("");
}

function bindPortfolioControls(payload) {
  ["sort-select", "position-filter", "risk-filter"].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.addEventListener("change", () => renderPortfolioCards(payload));
  });
}

function renderPortfolio(payload) {
  const workspace = dashboardRuntime.observationWorkspace || emptyObservationWorkspace();
  renderPortfolioStrip(payload);
  renderPortfolioTotals(payload);
  renderMacroRegime(payload);
  renderRiskRadar(payload);
  renderRecentProgress(payload);
  renderGapMap(payload);
  renderAnalytics(payload);
  renderPriorityQueue(payload);
  renderSummaryCards(payload);
  renderExceptionQueue(payload);
  renderGapSummary(payload);
  renderObservationCommandPanel(payload, workspace);
  renderObservationLakePanel(payload, workspace);
  renderWatchlistRecommendationsPanel(payload, workspace);
  bindPortfolioControls(payload);
  renderPortfolioCards(payload);
}

function renderPositionPanel(payload) {
  const root = document.getElementById("position-panel");
  if (!root) return;
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Position</p>
        <h2>部位與風控</h2>
      </div>
      <span class="${badgeClass(payload.position.risk_level_label)}">${escapeHtml(payload.position.risk_level_label)}</span>
    </div>
    <div class="info-grid">
      <div class="info-row"><span>持股數</span><strong>${escapeHtml(payload.position.shares_label)}</strong></div>
      <div class="info-row"><span>平均成本</span><strong>${escapeHtml(payload.position.avg_cost_label)}</strong></div>
      <div class="info-row"><span>Current Price</span><strong>${escapeHtml(payload.position.current_price_label)}</strong></div>
      <div class="info-row"><span>Market Value</span><strong>${escapeHtml(payload.position.market_value_label)}</strong></div>
      <div class="info-row"><span>未實現 P/L</span><strong>${escapeHtml(payload.position.unrealized_pnl_label)}</strong></div>
      <div class="info-row"><span>未實現 P/L %</span><strong>${escapeHtml(payload.position.unrealized_pnl_pct_label)}</strong></div>
      <div class="info-row"><span>目前權重</span><strong>${escapeHtml(payload.position.portfolio_weight_label)}</strong></div>
      <div class="info-row"><span>調整後目標 / 上限</span><strong>${escapeHtml(payload.position.adjusted_target_weight_label)} / ${escapeHtml(payload.position.adjusted_max_weight_label)}</strong></div>
    </div>
    <p class="footer-note">${escapeHtml(payload.position.notes || "若尚未填入私有持倉，這裡只會顯示研究層資料。")}</p>
  `;
}

function renderHealthPanel(payload) {
  const root = document.getElementById("health-panel");
  if (!root) return;
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Logic Health</p>
        <h2>邏輯健康度</h2>
      </div>
      <span class="${badgeClass(payload.thesis_health.label)}">${escapeHtml(payload.thesis_health.label)}</span>
    </div>
    <div class="metric-grid">
      <div class="stat-card">
        <p>整體健康度</p>
        <strong>${Math.round(payload.thesis_health.score * 100)}%</strong>
        <div class="status-bar"><span style="width:${Math.round(payload.thesis_health.score * 100)}%"></span></div>
      </div>
      <div class="stat-card">
        <p>假設分布</p>
        <strong>${escapeHtml(`${payload.thesis_health.reinforced_count} / ${payload.assumptions.length}`)}</strong>
        <p>已強化 ${payload.thesis_health.reinforced_count}、觀察 ${payload.thesis_health.watch_count}、受壓 ${payload.thesis_health.pressured_count}</p>
      </div>
    </div>
    <p class="footer-note">目前邏輯信心 ${Math.round(payload.thesis_confidence * 100)}%，本輪信心變化 ${payload.confidence_delta >= 0 ? "+" : ""}${Math.round(payload.confidence_delta * 100)}%。</p>
  `;
}

function renderAlertsPanel(payload) {
  const root = document.getElementById("alerts-panel");
  if (!root) return;
  const alerts = limitItems(payload.position.risk_alerts ?? [], 3);
  root.innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Risk Alerts</p>
        <h2>熔斷與警報</h2>
      </div>
      <span class="${badgeClass(`${payload.position.risk_alerts?.length ?? 0} alerts`)}">${payload.position.risk_alerts?.length ?? 0} 則</span>
    </div>
    <div class="alert-list">
      ${alerts.map((alert) => `
        <article class="alert-card" data-level="${escapeHtml(alert.level)}">
          <div class="row-between">
            <h3>${escapeHtml(alert.title)}</h3>
            <span class="${alertClass(alert.level)}">${escapeHtml(alert.level)}</span>
          </div>
          <p>${escapeHtml(alert.message)}</p>
          <p class="footer-note">${escapeHtml(alert.action)}</p>
        </article>
      `).join("") || emptyState("目前沒有 active risk alerts。")}
    </div>
  `;
}

function renderAssumptionsPanel(payload) {
  const assumptions = limitItems(payload.assumptions, 2);
  const items = assumptions.map((item) => `
    <article class="compact-card">
      <div class="row-between">
        <h3>${escapeHtml(item.assumption_id)}</h3>
        <span class="${badgeClass(item.status_label)}">${escapeHtml(item.status_label)}</span>
      </div>
      <p>${escapeHtml(item.statement)}</p>
      <p class="compact-note">先看：${escapeHtml(item.verification_method)}</p>
      <p class="compact-note">失效條件：${escapeHtml(item.invalidation_condition)}</p>
    </article>
  `).join("");
  document.getElementById("assumptions-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Core Assumptions</p>
        <h2>關鍵假設</h2>
      </div>
    </div>
    <div class="compact-grid">${items || emptyState("目前沒有假設資料。")}</div>
    ${payload.assumptions?.length > 2 ? `<p class="footer-note">決策頁只保留最重要的 2 個假設，完整版本在 ${linkMarkup(payload.internal_research_path, "研究內頁")}。</p>` : ""}
  `;
}

function renderTimelinePanel(payload) {
  const items = limitItems(payload.event_timeline, 4).map((event) => `
    <article class="timeline-item">
      <div class="row-between">
        <h3>${escapeHtml(event.occurred_at)}｜${escapeHtml(event.source_label)}</h3>
        <span class="${badgeClass(event.decision_label)}">${escapeHtml(event.decision_label)}</span>
      </div>
      <p>${escapeHtml(event.title)}</p>
      <div class="timeline-meta">
        <span class="sub-badge">${escapeHtml(event.impact_label)}</span>
        ${event.metadata?.is_exception ? `<span class="${alertClass(event.metadata.severity)}">${escapeHtml(event.metadata.exception_type)}</span>` : ""}
        ${event.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(event.href))}" target="${event.link_kind === "external" ? "_blank" : "_self"}" rel="noreferrer">${escapeHtml(event.link_label)}</a>` : ""}
      </div>
    </article>
  `).join("");
  document.getElementById("timeline-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Event Timeline</p>
        <h2>關鍵事件時間線</h2>
      </div>
    </div>
    <div class="timeline-list">${items || emptyState("目前沒有需要顯示的關鍵事件。")}</div>
    <p class="footer-note">決策頁只保留最近 4 筆；完整事件線放在 ${linkMarkup(payload.internal_research_path, "研究內頁")}。</p>
  `;
}

function renderChecklistPanel(payload) {
  const items = limitItems(payload.next_checklist, 3).map((item, index) => `
    <article class="check-item">
      <h3>Step ${index + 1}</h3>
      <p>${escapeHtml(item)}</p>
    </article>
  `).join("");
  document.getElementById("checklist-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Next Checks</p>
        <h2>下一步檢查清單</h2>
      </div>
    </div>
    <div class="checklist">${items || emptyState("目前沒有待辦清單。")}</div>
    ${payload.next_checklist?.length > 3 ? '<p class="footer-note">僅顯示最關鍵的 3 個檢查點。</p>' : ""}
  `;
}

function renderRulesPanel(payload) {
  const items = payload.action_rules.map((rule) => `
    <article class="rule-card">
      <div class="row-between">
        <h3>${escapeHtml(rule.action_rule_id)}</h3>
        <span class="sub-badge">${escapeHtml(rule.kind_label)}</span>
      </div>
      <p><strong>條件：</strong>${escapeHtml(rule.condition)}</p>
      <p><strong>動作：</strong>${escapeHtml(rule.action)}</p>
    </article>
  `).join("");
  document.getElementById("rules-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Rulebook</p>
        <h2>動作規則</h2>
      </div>
    </div>
    <div class="rule-grid">${items || emptyState("目前沒有操作規則。")}</div>
  `;
}

function renderSourcesPanel(payload) {
  const items = limitItems(payload.source_status, 2).map((source) => `
    <article class="compact-card">
      <div class="row-between">
        <h3>${escapeHtml(source.source_id)}</h3>
        <span class="${badgeClass(source.status_label)}">${escapeHtml(source.status_label)}</span>
      </div>
      <p>${escapeHtml(source.notes || "沒有補充說明。")}</p>
      <div class="timeline-meta">
        ${source.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(source.url))}" target="_blank" rel="noreferrer">來源網址</a>` : '<span class="muted">這個來源沒有公開外連。</span>'}
      </div>
    </article>
  `).join("");
  document.getElementById("sources-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Whitelisted Sources</p>
        <h2>來源與引用</h2>
      </div>
    </div>
    <div class="compact-grid">${items || emptyState("目前沒有來源白名單資料。")}</div>
    <p class="footer-note">決策頁只保留最常用的 2 個來源。需要完整脈絡可直接看 ${linkMarkup(payload.internal_research_path, "研究內頁")}。</p>
  `;
}

function renderDecisionRail(payload) {
  document.getElementById("decision-rail").innerHTML = `
    <div class="decision-block">
      <p class="panel-kicker">Action Rail</p>
      <h2>現在該怎麼做</h2>
      <p class="muted">${escapeHtml(payload.recommended_next_action || payload.current_action)}</p>
    </div>
    <div class="decision-block">
      <div class="row-between">
        <span class="muted">研究操作</span>
        <strong>${escapeHtml(payload.current_action)}</strong>
      </div>
      <div class="row-between">
        <span class="muted">VIX regime</span>
        <strong>${escapeHtml(payload.macro_regime?.label || "N/A")}</strong>
      </div>
      <div class="row-between">
        <span class="muted">Sizing 狀態</span>
        <strong>${escapeHtml(payload.position.sizing_status?.label || "N/A")}</strong>
      </div>
      <div class="row-between">
        <span class="muted">下次檢查</span>
        <strong>${escapeHtml(payload.next_review_at)}</strong>
      </div>
    </div>
    <div class="decision-block">
      <h3>這輪先看什麼</h3>
      <p class="muted">${escapeHtml(payload.next_checklist[0] || payload.next_must_check_data)}</p>
      <div class="timeline-meta">
        ${linkMarkup(payload.internal_research_path, "研究內頁")}
      </div>
    </div>
  `;
}

function renderTicker(payload) {
  const workspace = dashboardRuntime.observationWorkspace || emptyObservationWorkspace();
  document.title = `${payload.ticker}｜投資駕駛艙`;
  document.getElementById("ticker-title").textContent = `${payload.ticker}｜${payload.company_name}`;
  document.getElementById("ticker-summary").textContent = payload.summary_blurb;
  document.getElementById("ticker-meta").innerHTML = [
    pill("狀態", payload.status_label),
    pill("VIX regime", payload.macro_regime?.label || "載入中"),
    pill("未實現 P/L", payload.position.unrealized_pnl_pct_label || "N/A"),
    pill("下次檢查", payload.next_review_at),
  ].join("");
  renderDecisionRail(payload);
  renderPositionPanel(payload);
  renderHealthPanel(payload);
  renderAlertsPanel(payload);
  renderAssumptionsPanel(payload);
  renderTimelinePanel(payload);
  renderChecklistPanel(payload);
  renderRulesPanel(payload);
  renderSourcesPanel(payload);
  renderObservationRelatedPanel(payload, workspace);
}

function renderResearchBriefPanel(payload) {
  document.getElementById("research-brief-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Research Brief</p>
        <h2>先看結論，再看證據</h2>
      </div>
      <span class="${badgeClass(payload.status_label)}">${escapeHtml(payload.status_label)}</span>
    </div>
    <div class="brief-grid">
      <article class="compact-card">
        <h3>目前操作</h3>
        <p>${escapeHtml(payload.current_action)}</p>
      </article>
      <article class="compact-card">
        <h3>下一個動作</h3>
        <p>${escapeHtml(payload.recommended_next_action || payload.current_action)}</p>
      </article>
      <article class="compact-card">
        <h3>這輪先看什麼</h3>
        <p>${escapeHtml(payload.next_checklist?.[0] || payload.next_must_check_data || "N/A")}</p>
      </article>
      <article class="compact-card">
        <h3>風險 / 健康度</h3>
        <p>${escapeHtml(`VIX ${payload.macro_regime?.label || "載入中"}｜邏輯 ${Math.round((payload.thesis_health?.score ?? 0) * 100)}%`)}</p>
      </article>
    </div>
  `;
}

function renderThesisPanel(payload) {
  document.getElementById("thesis-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Logic Snapshot</p>
        <h2>核心邏輯</h2>
      </div>
      <span class="${badgeClass(payload.thesis_health.label)}">${escapeHtml(payload.thesis_health.label)}</span>
    </div>
    <blockquote class="thesis-quote">${escapeHtml(payload.research_state.thesis_statement)}</blockquote>
    <div class="info-grid">
      <div class="info-row"><span>研究主題</span><strong>${escapeHtml(payload.research_state.research_topic)}</strong></div>
      <div class="info-row"><span>核心催化</span><strong>${escapeHtml(payload.research_state.core_catalyst)}</strong></div>
      <div class="info-row"><span>市場盲點</span><strong>${escapeHtml(payload.research_state.market_blind_spot)}</strong></div>
      <div class="info-row"><span>持有期間</span><strong>${escapeHtml(payload.research_state.holding_period)}</strong></div>
    </div>
  `;
}

function renderDeltaPanel(payload) {
  const deltaItems = payload.research_state.latest_delta.map((item) => `<article class="list-card"><p>${escapeHtml(item)}</p></article>`).join("");
  document.getElementById("delta-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Delta</p>
        <h2>與前版差異</h2>
      </div>
    </div>
    <div class="delta-list">${deltaItems || emptyState("這一版沒有額外的 delta 說明。")}</div>
  `;
}

function renderReviewSummaryPanel(payload) {
  const changed = payload.changed_assumptions.map((item) => `<article class="list-card"><p><strong>${escapeHtml(item.assumption_id)}</strong>｜${escapeHtml(item.summary)}</p></article>`).join("");
  document.getElementById("review-summary-panel").innerHTML = `
    <div class="panel-head" id="review-summary">
      <div>
        <p class="panel-kicker">Review Summary</p>
        <h2>本輪更新摘要</h2>
      </div>
    </div>
    <article class="list-card">
      <p>${escapeHtml(payload.review_summary || payload.summary_blurb)}</p>
    </article>
    <div class="delta-list">${changed || emptyState("本輪沒有額外的假設變更。")}</div>
  `;
}

function renderResearchAssumptions(payload) {
  const items = payload.assumptions.map((item) => `
    <article class="assumption-card">
      <div class="row-between">
        <h3>${escapeHtml(item.assumption_id)}</h3>
        <span class="${badgeClass(item.status_label)}">${escapeHtml(item.status_label)}</span>
      </div>
      <p>${escapeHtml(item.statement)}</p>
      <p><strong>驗證方式：</strong>${escapeHtml(item.verification_method)}</p>
      <p><strong>失效條件：</strong>${escapeHtml(item.invalidation_condition)}</p>
    </article>
  `).join("");
  document.getElementById("research-assumptions-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Assumption Map</p>
        <h2>假設地圖</h2>
      </div>
    </div>
    <div class="assumption-grid">${items || emptyState("目前沒有假設資料。")}</div>
  `;
}

function renderResearchEvents(payload) {
  const items = limitItems(payload.event_timeline, 5).map((event) => `
    <article class="timeline-item">
      <div class="row-between">
        <h3>${escapeHtml(event.occurred_at)}｜${escapeHtml(event.source_label)}</h3>
        <span class="${badgeClass(event.decision_label)}">${escapeHtml(event.decision_label)}</span>
      </div>
      <p>${escapeHtml(event.title)}</p>
      <div class="timeline-meta">
        <span class="sub-badge">${escapeHtml(event.impact_label)}</span>
        ${event.metadata?.is_exception ? `<span class="${alertClass(event.metadata.severity)}">${escapeHtml(event.metadata.exception_type)}</span>` : ""}
        ${event.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(event.href))}" target="${event.link_kind === "external" ? "_blank" : "_self"}" rel="noreferrer">${escapeHtml(event.link_label)}</a>` : ""}
      </div>
    </article>
  `).join("");
  document.getElementById("research-events-panel").innerHTML = `
    <div class="panel-head" id="event-timeline">
      <div>
        <p class="panel-kicker">Timeline</p>
        <h2>事件時間線</h2>
      </div>
    </div>
    <div class="timeline-list">${items || emptyState("目前沒有事件時間線資料。")}</div>
    ${payload.event_timeline?.length > 5 ? '<p class="footer-note">僅顯示最近 5 筆事件，避免研究頁過度擁擠。</p>' : ""}
  `;
}

function renderResearchCitations(payload) {
  const items = limitItems(payload.citations, 6).map((citation) => `
    <article class="citation-item">
      <div class="row-between">
        <h3>${escapeHtml(citation.label)}</h3>
        <span class="sub-badge">${escapeHtml(citation.kind === "external" ? "外部來源" : "內部節點")}</span>
      </div>
      <p>${escapeHtml(citation.source_type)}｜${escapeHtml(citation.occurred_at)}</p>
      <div class="timeline-meta">
        ${citation.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(citation.href))}" target="${citation.kind === "external" ? "_blank" : "_self"}" rel="noreferrer">打開引用</a>` : '<span class="muted">這個引用沒有可點擊網址。</span>'}
      </div>
    </article>
  `).join("");
  document.getElementById("research-citations-panel").innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Citations</p>
        <h2>來源與引用</h2>
      </div>
    </div>
    <div class="citation-list">${items || emptyState("目前沒有可顯示的引用。")}</div>
    ${payload.citations?.length > 6 ? '<p class="footer-note">僅顯示前 6 個引用，保留研究頁的閱讀節奏。</p>' : ""}
  `;
}

function renderResearch(payload) {
  document.title = `${payload.ticker}｜研究內頁`;
  document.getElementById("research-title").textContent = `${payload.ticker}｜${payload.company_name}`;
  document.getElementById("research-summary").textContent = payload.summary_blurb;
  document.getElementById("research-meta").innerHTML = [
    pill("目前操作", payload.current_action),
    pill("VIX regime", payload.macro_regime?.label || "載入中"),
    pill("邏輯健康度", `${Math.round(payload.thesis_health.score * 100)}%`),
    pill("下次檢查", payload.next_review_at),
  ].join("");
  renderResearchBriefPanel(payload);
  renderThesisPanel(payload);
  renderDeltaPanel(payload);
  renderReviewSummaryPanel(payload);
  renderResearchAssumptions(payload);
  renderResearchEvents(payload);
  renderResearchCitations(payload);
}

function injectSharedPayload(payload) {
  if (!payload) return payload;
  return {
    ...payload,
    tickers: payload.tickers ?? [],
    macro_regime: payload.macro_regime ?? {},
    portfolio_totals: payload.portfolio_totals ?? {},
  };
}

function renderError(error) {
  const main = document.querySelector("main");
  if (!main) return;
  const box = document.createElement("div");
  box.className = "error-state";
  box.textContent = `無法載入 dashboard 資料：${error.message}`;
  main.appendChild(box);
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

function renderDetailPage(payload) {
  if (currentPage() === "ticker") {
    renderTicker(payload);
    return;
  }
  if (currentPage() === "research") {
    renderResearch(payload);
  }
}

async function boot() {
  try {
    if (currentPage() === "portfolio") {
      const payload = injectSharedPayload(await loadJson("./data/portfolio.json"));
      dashboardRuntime.portfolioPayload = payload;
      try {
        await loadObservationWorkspace(payload);
      } catch (observationError) {
        console.warn("Unable to load observation workspace.", observationError);
        dashboardRuntime.observationWorkspace = emptyObservationWorkspace();
      }
      renderPortfolio(payload);
      return;
    }
    const digestPath = document.body.dataset.digestPath;
    const payload = injectSharedPayload(await loadJson(digestPath));
    dashboardRuntime.currentPayload = payload;
    try {
      await loadObservationWorkspace(payload);
    } catch (observationError) {
      console.warn("Unable to load observation workspace.", observationError);
      dashboardRuntime.observationWorkspace = emptyObservationWorkspace();
    }
    renderDetailPage(payload);
    if (!payload.macro_regime?.label) {
      try {
        const portfolioPayload = injectSharedPayload(await loadJson("../data/portfolio.json"));
        if (portfolioPayload.macro_regime) {
          payload.macro_regime = portfolioPayload.macro_regime;
          renderDetailPage(payload);
        }
      } catch (portfolioError) {
        console.warn("Unable to refresh macro regime from portfolio payload.", portfolioError);
      }
    }
  } catch (error) {
    console.error(error);
    renderError(error);
  }
}

document.addEventListener("DOMContentLoaded", boot);
