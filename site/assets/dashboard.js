function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function currentPage() {
  return document.body.dataset.dashboardPage;
}

function siteHref(path) {
  if (!path) return '#';
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  const prefix = currentPage() === 'portfolio' ? './' : '../';
  return `${prefix}${path}`;
}

function linkMarkup(path, label, className = 'inline-link') {
  if (!path) return '';
  return `<a class="${className}" href="${escapeHtml(siteHref(path))}">${escapeHtml(label)}</a>`;
}

function badgeClass(label) {
  if (label.includes('退出') || label.includes('高風險') || label.includes('失敗')) return 'badge badge-alert';
  if (label.includes('穩定') || label.includes('偏多') || label.includes('健康')) return 'badge badge-calm';
  return 'badge';
}

function pill(label, value) {
  return `<div class="pill"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function emptyState(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function renderPortfolioStrip(payload) {
  const strip = document.getElementById('portfolio-summary-strip');
  const summary = payload.portfolio_summary;
  strip.innerHTML = [
    pill('更新時間', payload.generated_at),
    pill('追蹤標的', `${summary.tracked_ticker_count} 檔`),
    pill('已填部位', `${summary.positioned_ticker_count} 檔`),
    pill('整體健康度', `${Math.round(summary.thesis_health_score * 100)}%`),
  ].join('');
}

function renderSummaryCards(payload) {
  const summary = payload.portfolio_summary;
  const root = document.getElementById('summary-cards');
  root.innerHTML = `
    <article class="stat-card">
      <p>整體 thesis 狀態</p>
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
      <p>${escapeHtml(summary.upcoming_tickers.join('、') || '目前沒有迫近的例行複盤。')}</p>
    </article>
    <article class="stat-card">
      <p>本機部位覆蓋</p>
      <strong>${escapeHtml(summary.positioned_ticker_count)} / ${escapeHtml(summary.tracked_ticker_count)}</strong>
      <p>若要顯示成本與目標倉位，請填入 `portfolio.private.json`。</p>
    </article>
  `;
}

function renderPriorityQueue(payload) {
  const root = document.getElementById('priority-queue');
  if (!payload.priority_queue.length) {
    root.innerHTML = emptyState('目前沒有需要優先處理的標的。');
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
        ${linkMarkup(item.detail_path, '打開決策頁')}
        ${linkMarkup(item.research_path, '打開研究內頁')}
      </div>
    </article>
  `).join('');
}

function cardRiskValue(card) {
  return {
    'high-conviction': 4,
    core: 3,
    satellite: 2,
    trading: 1,
    '': 0,
  }[card.risk_level ?? ''] ?? 0;
}

function sortCards(cards, mode) {
  const cloned = [...cards];
  if (mode === 'review') {
    return cloned.sort((a, b) => a.next_review_at.localeCompare(b.next_review_at));
  }
  if (mode === 'risk') {
    return cloned.sort((a, b) => cardRiskValue(b) - cardRiskValue(a) || b.priority_score - a.priority_score);
  }
  if (mode === 'confidence') {
    return cloned.sort((a, b) => b.thesis_health.score - a.thesis_health.score || b.priority_score - a.priority_score);
  }
  return cloned.sort((a, b) => b.priority_score - a.priority_score || a.next_review_at.localeCompare(b.next_review_at));
}

function filterCards(cards) {
  const positionFilter = document.getElementById('position-filter')?.value ?? 'all';
  const riskFilter = document.getElementById('risk-filter')?.value ?? 'all';
  return cards.filter((card) => {
    if (positionFilter === 'has-position' && !card.position.has_position) return false;
    if (positionFilter === 'missing-position' && card.position.has_position) return false;
    if (riskFilter === 'unset' && card.risk_level) return false;
    if (riskFilter !== 'all' && riskFilter !== 'unset' && card.risk_level !== riskFilter) return false;
    return true;
  });
}

function renderPortfolioCards(payload) {
  const grid = document.getElementById('portfolio-grid');
  const meta = document.getElementById('portfolio-grid-meta');
  const sortMode = document.getElementById('sort-select')?.value ?? 'priority';
  const cards = sortCards(filterCards(payload.tickers), sortMode);
  meta.textContent = `目前顯示 ${cards.length} / ${payload.tickers.length} 檔。`;
  if (!cards.length) {
    grid.innerHTML = emptyState('目前沒有符合篩選條件的標的。');
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
        <div class="meta-row"><span>目前操作</span><strong>${escapeHtml(card.current_action)}</strong></div>
        <div class="meta-row"><span>部位摘要</span><strong>${escapeHtml(card.position.summary)}</strong></div>
        <div class="meta-row"><span>風險等級</span><strong>${escapeHtml(card.risk_level_label)}</strong></div>
        <div class="meta-row"><span>下次檢查</span><strong>${escapeHtml(card.next_review_at)}</strong></div>
        <div class="meta-row"><span>信心 / 健康度</span><strong>${Math.round(card.thesis_confidence * 100)}% / ${Math.round(card.thesis_health.score * 100)}%</strong></div>
        <div class="meta-row"><span>最近事件狀態</span><strong>${escapeHtml(card.last_event_status)}</strong></div>
      </div>
      <div class="timeline-meta">
        ${linkMarkup(card.detail_path, '打開決策頁')}
        ${linkMarkup(card.internal_research_path, '研究內頁')}
      </div>
    </article>
  `).join('');
}

function bindPortfolioControls(payload) {
  ['sort-select', 'position-filter', 'risk-filter'].forEach((id) => {
    const element = document.getElementById(id);
    if (!element) return;
    element.addEventListener('change', () => renderPortfolioCards(payload));
  });
}

function renderPortfolio(payload) {
  renderPortfolioStrip(payload);
  renderPriorityQueue(payload);
  renderSummaryCards(payload);
  bindPortfolioControls(payload);
  renderPortfolioCards(payload);
}

function renderPositionPanel(payload) {
  document.getElementById('position-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Position</p>
        <h2>部位與風險</h2>
      </div>
      <span class="${badgeClass(payload.position.risk_level_label)}">${escapeHtml(payload.position.risk_level_label)}</span>
    </div>
    <div class="info-grid">
      <div class="info-row"><span>持股數</span><strong>${escapeHtml(payload.position.shares_label)}</strong></div>
      <div class="info-row"><span>平均成本</span><strong>${escapeHtml(payload.position.avg_cost_label)}</strong></div>
      <div class="info-row"><span>目標倉位</span><strong>${escapeHtml(payload.position.target_weight_label)}</strong></div>
      <div class="info-row"><span>上限倉位</span><strong>${escapeHtml(payload.position.max_weight_label)}</strong></div>
    </div>
    <p class="footer-note">${escapeHtml(payload.position.notes || '若尚未填入私有持倉，這裡只會顯示研究層資料。')}</p>
  `;
}

function renderHealthPanel(payload) {
  document.getElementById('health-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Thesis Health</p>
        <h2>thesis 健康度</h2>
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
        <strong>${escapeHtml(payload.thesis_health.reinforced_count)} / ${escapeHtml(payload.assumptions.length)}</strong>
        <p>已強化 ${payload.thesis_health.reinforced_count}、觀察 ${payload.thesis_health.watch_count}、受壓 ${payload.thesis_health.pressured_count}</p>
      </div>
    </div>
    <p class="footer-note">目前 thesis 信心 ${Math.round(payload.thesis_confidence * 100)}%，本輪信心變化 ${payload.confidence_delta >= 0 ? '+' : ''}${Math.round(payload.confidence_delta * 100)}%。</p>
  `;
}

function renderAssumptionsPanel(payload) {
  const items = payload.assumptions.map((item) => `
    <article class="assumption-card">
      <div class="row-between">
        <h3>${escapeHtml(item.assumption_id)}</h3>
        <span class="${badgeClass(item.status_label)}">${escapeHtml(item.status_label)}</span>
      </div>
      <p>${escapeHtml(item.statement)}</p>
      <p><strong>驗證方式：</strong>${escapeHtml(item.verification_method)}</p>
      <p><strong>失效條件：</strong>${escapeHtml(item.invalidation_condition)}</p>
      <p><strong>信心：</strong>${Math.round(item.confidence * 100)}%</p>
    </article>
  `).join('');
  document.getElementById('assumptions-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Core Assumptions</p>
        <h2>關鍵假設</h2>
      </div>
    </div>
    <div class="assumption-grid">${items || emptyState('目前沒有假設資料。')}</div>
  `;
}

function renderTimelinePanel(payload) {
  const items = payload.event_timeline.map((event) => `
    <article class="timeline-item">
      <div class="row-between">
        <h3>${escapeHtml(event.occurred_at)}｜${escapeHtml(event.source_label)}</h3>
        <span class="${badgeClass(event.decision_label)}">${escapeHtml(event.decision_label)}</span>
      </div>
      <p>${escapeHtml(event.title)}</p>
      <div class="timeline-meta">
        <span class="sub-badge">${escapeHtml(event.impact_label)}</span>
        ${event.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(event.href))}" target="${event.link_kind === 'external' ? '_blank' : '_self'}" rel="noreferrer">${escapeHtml(event.link_label)}</a>` : ''}
      </div>
    </article>
  `).join('');
  document.getElementById('timeline-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Event Timeline</p>
        <h2>關鍵事件時間線</h2>
      </div>
    </div>
    <div class="timeline-list">${items || emptyState('目前沒有需要顯示的關鍵事件。')}</div>
  `;
}

function renderChecklistPanel(payload) {
  const items = payload.next_checklist.map((item, index) => `
    <article class="check-item">
      <h3>Step ${index + 1}</h3>
      <p>${escapeHtml(item)}</p>
    </article>
  `).join('');
  document.getElementById('checklist-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Next Checks</p>
        <h2>下一步檢查清單</h2>
      </div>
    </div>
    <div class="checklist">${items || emptyState('目前沒有待辦清單。')}</div>
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
  `).join('');
  document.getElementById('rules-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Rulebook</p>
        <h2>動作規則</h2>
      </div>
    </div>
    <div class="rule-grid">${items || emptyState('目前沒有操作規則。')}</div>
  `;
}

function renderSourcesPanel(payload) {
  const items = payload.source_status.map((source) => `
    <article class="source-card">
      <div class="row-between">
        <h3>${escapeHtml(source.source_id)}</h3>
        <span class="${badgeClass(source.status_label)}">${escapeHtml(source.status_label)}</span>
      </div>
      <p>${escapeHtml(source.notes || '沒有補充說明。')}</p>
      <div class="timeline-meta">
        ${source.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(source.url))}" target="_blank" rel="noreferrer">來源網址</a>` : '<span class="muted">這個來源沒有公開外連。</span>'}
      </div>
    </article>
  `).join('');
  document.getElementById('sources-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Whitelisted Sources</p>
        <h2>來源與引用</h2>
      </div>
    </div>
    <div class="source-grid">${items || emptyState('目前沒有來源白名單資料。')}</div>
  `;
}

function renderResearchEntryPanel(payload) {
  document.getElementById('research-entry-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Deep Dive</p>
        <h2>研究內頁入口</h2>
      </div>
    </div>
    <div class="list-card">
      <p>如果你要看 thesis 脈絡、與前版差異、事件時間線與內部研究節點，這裡是正式入口。</p>
      <div class="timeline-meta">
        ${linkMarkup(payload.internal_research_path, '打開研究內頁')}
        ${linkMarkup(payload.detail_path, '留在決策頁')}
      </div>
      <p class="footer-note">目前共有 ${payload.citations.length} 個可用引用，其中外部來源 ${payload.citation_links.external.length} 個。</p>
    </div>
  `;
}

function renderDecisionRail(payload) {
  document.getElementById('decision-rail').innerHTML = `
    <div class="decision-block" id="decision-rail-anchor">
      <p class="panel-kicker">Action Rail</p>
      <h2>現在該怎麼做</h2>
      <p class="muted">${escapeHtml(payload.current_action)}</p>
    </div>
    <div class="decision-block">
      <div class="row-between">
        <span class="muted">優先級</span>
        <span class="${badgeClass(payload.priority_label)}">${escapeHtml(payload.priority_label)}</span>
      </div>
      <div class="row-between">
        <span class="muted">下次檢查</span>
        <strong>${escapeHtml(payload.next_review_at)}</strong>
      </div>
      <div class="row-between">
        <span class="muted">最近事件狀態</span>
        <strong>${escapeHtml(payload.last_event_status)}</strong>
      </div>
      <div class="row-between">
        <span class="muted">風險等級</span>
        <strong>${escapeHtml(payload.risk_level_label)}</strong>
      </div>
    </div>
    <div class="decision-block">
      <h3>這輪先看什麼</h3>
      <p class="muted">${escapeHtml(payload.next_checklist[0] || payload.next_must_check_data)}</p>
      <div class="timeline-meta">
        ${linkMarkup(payload.internal_research_path, '研究內頁')}
      </div>
    </div>
  `;
}

function renderTicker(payload) {
  document.title = `${payload.ticker}｜投資駕駛艙`;
  document.getElementById('ticker-title').textContent = `${payload.ticker}｜${payload.company_name}`;
  document.getElementById('ticker-summary').textContent = payload.summary_blurb;
  document.getElementById('ticker-meta').innerHTML = [
    pill('狀態', payload.status_label),
    pill('thesis 健康度', `${Math.round(payload.thesis_health.score * 100)}%`),
    pill('下次檢查', payload.next_review_at),
    pill('最近事件', payload.last_event_status),
  ].join('');
  renderDecisionRail(payload);
  renderPositionPanel(payload);
  renderHealthPanel(payload);
  renderAssumptionsPanel(payload);
  renderTimelinePanel(payload);
  renderChecklistPanel(payload);
  renderRulesPanel(payload);
  renderSourcesPanel(payload);
  renderResearchEntryPanel(payload);
}

function renderThesisPanel(payload) {
  document.getElementById('thesis-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Thesis Snapshot</p>
        <h2>thesis 摘要</h2>
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
  const deltaItems = payload.research_state.latest_delta.map((item) => `<article class="list-card"><p>${escapeHtml(item)}</p></article>`).join('');
  document.getElementById('delta-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Delta</p>
        <h2>與前版差異</h2>
      </div>
    </div>
    <div class="delta-list">${deltaItems || emptyState('這一版沒有額外的 delta 說明。')}</div>
  `;
}

function renderReviewSummaryPanel(payload) {
  const changed = payload.changed_assumptions.map((item) => `<article class="list-card"><p><strong>${escapeHtml(item.assumption_id)}</strong>｜${escapeHtml(item.summary)}</p></article>`).join('');
  document.getElementById('review-summary-panel').innerHTML = `
    <div class="panel-head" id="review-summary">
      <div>
        <p class="panel-kicker">Review Summary</p>
        <h2>本輪更新摘要</h2>
      </div>
    </div>
    <article class="list-card">
      <p>${escapeHtml(payload.review_summary || payload.summary_blurb)}</p>
    </article>
    <div class="delta-list">${changed || emptyState('本輪沒有額外的假設變更。')}</div>
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
  `).join('');
  document.getElementById('research-assumptions-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Assumption Map</p>
        <h2>假設地圖</h2>
      </div>
    </div>
    <div class="assumption-grid">${items || emptyState('目前沒有假設資料。')}</div>
  `;
}

function renderResearchEvents(payload) {
  const items = payload.event_timeline.map((event) => `
    <article class="timeline-item">
      <div class="row-between">
        <h3>${escapeHtml(event.occurred_at)}｜${escapeHtml(event.source_label)}</h3>
        <span class="${badgeClass(event.decision_label)}">${escapeHtml(event.decision_label)}</span>
      </div>
      <p>${escapeHtml(event.title)}</p>
      <div class="timeline-meta">
        <span class="sub-badge">${escapeHtml(event.impact_label)}</span>
        ${event.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(event.href))}" target="${event.link_kind === 'external' ? '_blank' : '_self'}" rel="noreferrer">${escapeHtml(event.link_label)}</a>` : ''}
      </div>
    </article>
  `).join('');
  document.getElementById('research-events-panel').innerHTML = `
    <div class="panel-head" id="event-timeline">
      <div>
        <p class="panel-kicker">Timeline</p>
        <h2>事件時間線</h2>
      </div>
    </div>
    <div class="timeline-list">${items || emptyState('目前沒有事件時間線資料。')}</div>
  `;
}

function renderResearchCitations(payload) {
  const items = payload.citations.map((citation) => `
    <article class="citation-item">
      <div class="row-between">
        <h3>${escapeHtml(citation.label)}</h3>
        <span class="sub-badge">${escapeHtml(citation.kind === 'external' ? '外部來源' : '內部節點')}</span>
      </div>
      <p>${escapeHtml(citation.source_type)}｜${escapeHtml(citation.occurred_at)}</p>
      <div class="timeline-meta">
        ${citation.is_clickable ? `<a class="citation-link" href="${escapeHtml(siteHref(citation.href))}" target="${citation.kind === 'external' ? '_blank' : '_self'}" rel="noreferrer">打開引用</a>` : '<span class="muted">這個引用沒有可點擊網址。</span>'}
      </div>
    </article>
  `).join('');
  document.getElementById('research-citations-panel').innerHTML = `
    <div class="panel-head">
      <div>
        <p class="panel-kicker">Citations</p>
        <h2>來源與引用</h2>
      </div>
    </div>
    <div class="citation-list">${items || emptyState('目前沒有可顯示的引用。')}</div>
  `;
}

function renderResearch(payload) {
  document.title = `${payload.ticker}｜研究內頁`;
  document.getElementById('research-title').textContent = `${payload.ticker}｜${payload.company_name}`;
  document.getElementById('research-summary').textContent = payload.summary_blurb;
  document.getElementById('research-meta').innerHTML = [
    pill('目前操作', payload.current_action),
    pill('thesis 健康度', `${Math.round(payload.thesis_health.score * 100)}%`),
    pill('下次檢查', payload.next_review_at),
  ].join('');
  renderThesisPanel(payload);
  renderDeltaPanel(payload);
  renderReviewSummaryPanel(payload);
  renderResearchAssumptions(payload);
  renderResearchEvents(payload);
  renderResearchCitations(payload);
}

function renderError(error) {
  const main = document.querySelector('main');
  if (!main) return;
  const box = document.createElement('div');
  box.className = 'error-state';
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

async function boot() {
  try {
    if (currentPage() === 'portfolio') {
      renderPortfolio(await loadJson('./data/portfolio.json'));
      return;
    }
    const digestPath = document.body.dataset.digestPath;
    const payload = await loadJson(digestPath);
    if (currentPage() === 'ticker') {
      renderTicker(payload);
      return;
    }
    if (currentPage() === 'research') {
      renderResearch(payload);
    }
  } catch (error) {
    console.error(error);
    renderError(error);
  }
}

document.addEventListener('DOMContentLoaded', boot);

// Appended Analytics & Exception rendering
function renderAnalytics(analytics) {
  const container = document.getElementById("analytics-summary");
  if (!container || !analytics) return;

  container.innerHTML = `
    <div class="summary-metric">
      <div class="metric-value">${analytics.hit_rate_pct}%</div>
      <div class="metric-label">Assumption Hit Rate (${analytics.assumptions_correct}/${analytics.assumptions_resolved})</div>
    </div>
    <div class="summary-metric">
      <div class="metric-value">${analytics.regime_drift_events}</div>
      <div class="metric-label">Regime Drifts Identified</div>
    </div>
    <div class="summary-metric">
        <div class="metric-value">${analytics.expectation_gap_events}</div>
        <div class="metric-label">Expectation Gaps Logged</div>
    </div>
  `;
}

// Override initDashboard to include analytics
const _oldInitDashboard = initDashboard;
initDashboard = async function() {
    await _oldInitDashboard();
    try {
        const response = await fetch('./data/portfolio.json');
        const data = await response.json();
        if (data.post_mortem_analytics) {
            renderAnalytics(data.post_mortem_analytics);
        }
    } catch (err) {
        console.error("Failed to load analytics: ", err);
    }
};

// Exception Dashboard logic
function renderExceptionQueue(tickers) {
  const container = document.getElementById("exception-queue");
  const board = document.getElementById("exception-board");
  if (!container || !board) return;

  const exceptions = [];
  
  if (tickers) {
    for (const ticker of tickers) {
      if (ticker.key_events) {
          for (const ev of ticker.key_events) {
             if (ev.metadata && ev.metadata.is_exception) {
                 exceptions.push({
                     ticker: ticker.ticker,
                     type: ev.metadata.exception_type,
                     severity: ev.metadata.severity,
                     title: ev.title,
                     date: ev.occurred_at
                 });
             }
          }
      }
    }
  }

  if (exceptions.length > 0) {
    board.style.display = "block";
    container.innerHTML = exceptions.map(ex => `
      <a href="tickers/${ex.ticker}.html" class="priority-item" style="border-left-color: var(--accent-red);">
        <div class="priority-meta">
          <span class="ticker">${ex.ticker}</span>
          <span class="score" style="background: var(--accent-red); color: white;">${ex.severity.toUpperCase()}</span>
        </div>
        <div class="priority-detail">
          <strong>${ex.type}</strong>
          <span class="reason">${ex.title} (${ex.date})</span>
        </div>
      </a>
    `).join("");
  } else {
    board.style.display = "none";
  }
}

// Override initDashboard to include exception rendering
const _oldInitDashboard2 = initDashboard;
initDashboard = async function() {
    await _oldInitDashboard2();
    try {
        const response = await fetch('./data/portfolio.json');
        const data = await response.json();
        if (data.tickers) {
            renderExceptionQueue(data.tickers);
        }
    } catch (err) {
        console.error("Failed to load exceptions: ", err);
    }
};
