const portfolioRoot = document.getElementById('portfolio-grid');
const portfolioMeta = document.getElementById('portfolio-meta');

/**
 * Creates a meta pill element for the hero section.
 */
function createMetaPill(label, value) {
  const wrapper = document.createElement('div');
  wrapper.className = 'meta-pill';
  wrapper.innerHTML = `<strong>${label}</strong> <span>${value}</span>`;
  return wrapper;
}

/**
 * Renders a list of items using a provided renderer function.
 */
function renderList(container, items, renderer) {
  container.innerHTML = '';
  if (!items || !items.length) {
    const empty = document.createElement('p');
    empty.className = 'subtle-empty';
    empty.textContent = '目前沒有需要顯示的項目。';
    container.appendChild(empty);
    return;
  }
  const list = document.createElement('div');
  list.className = 'list';
  items.forEach((item, index) => {
    const rendered = renderer(item);
    rendered.style.opacity = '0';
    rendered.style.transform = 'translateY(10px)';
    rendered.style.transition = `all 0.4s ease ${index * 0.05}s`;
    list.appendChild(rendered);
    
    // Trigger animation
    setTimeout(() => {
      rendered.style.opacity = '1';
      rendered.style.transform = 'translateY(0)';
    }, 50);
  });
  container.appendChild(list);
}

/**
 * Renders the portfolio (index) page.
 */
function renderPortfolio(payload) {
  portfolioMeta.appendChild(createMetaPill('更新時間', payload.generated_at));
  portfolioMeta.appendChild(createMetaPill('持股數', payload.tickers.length));
  
  payload.tickers.forEach((card, index) => {
    const link = document.createElement('a');
    link.className = 'card';
    link.href = card.detail_href;
    link.style.opacity = '0';
    link.style.transform = 'translateY(20px)';
    link.style.transition = `all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) ${index * 0.1}s`;
    
    link.innerHTML = `
      <div class="card-top">
        <div>
          <h2 class="ticker">${card.ticker}</h2>
          <p class="subtle" style="margin: 4px 0 0; font-size: 14px; color: var(--muted);">${card.company_name}</p>
        </div>
        <span class="tag">${card.status_label}</span>
      </div>
      <p class="card-summary">${card.summary_blurb}</p>
      <div class="card-meta">
        <div class="meta-row"><span>目前操作</span><strong>${card.current_action}</strong></div>
        <div class="meta-row"><span>下次檢查</span><strong>${card.next_review_at}</strong></div>
        <div class="meta-row"><span>信心指數</span><strong>${(card.thesis_confidence * 100).toFixed(0)}%</strong></div>
      </div>
    `;
    portfolioRoot.appendChild(link);
    
    // Trigger animation
    setTimeout(() => {
      link.style.opacity = '1';
      link.style.transform = 'translateY(0)';
    }, 100);
  });
}

/**
 * Renders the ticker detail page.
 */
function renderTicker(payload) {
  document.title = `${payload.ticker} | ${payload.company_name}`;
  document.getElementById('ticker-title').textContent = `${payload.ticker}｜${payload.company_name}`;
  document.getElementById('ticker-summary').textContent = payload.summary_blurb;
  
  const meta = document.getElementById('ticker-meta');
  meta.appendChild(createMetaPill('狀態', payload.status_label));
  meta.appendChild(createMetaPill('信心', `${(payload.thesis_confidence * 100).toFixed(0)}%`));
  meta.appendChild(createMetaPill('下次檢查', payload.next_review_at));
  
  document.getElementById('ticker-action').textContent = payload.current_action;
  document.getElementById('ticker-next-data').textContent = payload.next_must_check_data;

  // Render Key Action Rules
  renderList(document.getElementById('ticker-rules'), payload.key_action_rules, (rule) => {
    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
      <h3>${rule.action_rule_id} · ${rule.kind}</h3>
      <p><strong>條件：</strong>${rule.condition}</p>
      <p class="subtle"><strong>動作：</strong>${rule.action}</p>
    `;
    return item;
  });

  // Render Key Events
  renderList(document.getElementById('ticker-events'), payload.key_events, (event) => {
    const item = document.createElement('div');
    item.className = 'list-item';
    item.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <h3>${event.occurred_at} · ${event.source_type}</h3>
        <a href="${event.source_url}" target="_blank" class="subtle" style="font-size: 12px;">原始連結 ↗</a>
      </div>
      <p>${event.title}</p>
      <p class="subtle"><strong>判斷：</strong>${event.decision}</p>
    `;
    return item;
  });

  // Render Source Status
  renderList(document.getElementById('ticker-sources'), payload.source_status, (source) => {
    const item = document.createElement('div');
    item.className = 'list-item';
    const statusClass = source.status === 'failed' ? 'status-negative' : 'status-positive';
    item.innerHTML = `
      <div style="display: flex; justify-content: space-between;">
        <h3>${source.source_id}</h3>
        <span class="${statusClass}" style="font-size: 12px; font-weight: 700;">${source.status_label}</span>
      </div>
      <p style="margin-bottom: 4px;">${source.notes || 'No additional notes'}</p>
      <a href="${source.url}" target="_blank" class="subtle" style="font-size: 12px; word-break: break-all;">${source.url}</a>
    `;
    return item;
  });
}

/**
 * Main boot function.
 */
async function boot() {
  const page = document.body.dataset.dashboardPage;
  try {
    if (page === 'portfolio') {
      const response = await fetch('./data/portfolio.json');
      if (!response.ok) throw new Error('Failed to load portfolio data');
      renderPortfolio(await response.json());
      return;
    }
    if (page === 'ticker') {
      const digestPath = document.body.dataset.digestPath;
      const response = await fetch(digestPath);
      if (!response.ok) throw new Error('Failed to load ticker data');
      renderTicker(await response.json());
    }
  } catch (error) {
    console.error('Dashboard Error:', error);
    const main = document.querySelector('main');
    const errBox = document.createElement('div');
    errBox.style.padding = '20px';
    errBox.style.background = 'rgba(211, 47, 47, 0.1)';
    errBox.style.color = '#d32f2f';
    errBox.style.borderRadius = '8px';
    errBox.style.marginTop = '20px';
    errBox.textContent = `無法載入資料：${error.message}`;
    main.appendChild(errBox);
  }
}

// Start the dashboard
document.addEventListener('DOMContentLoaded', boot);
