# gemini advisor artifact

- Provider: gemini
- Exit code: 0
- Created at: 2026-04-20T10:55:50.432Z

## Original task

Phase 3 planning support for STOCK Light Track. Read ~/vault/projects/stock/context.md.

TASK: Draft a minimal Phase 3 implementation plan for:
1. launchd scheduled monitoring — what plist changes needed to call 'quick-decision --no-prompt' for each watchlist ticker at market open (09:00 TWD)? What threshold triggers a push notification?
2. site/ Quick Pulse page — what's the minimal HTML/JS needed to display the quick-decision.json output as a Traffic Light Card? The existing site uses static files in site/data/.
3. Telegram bot — what's the simplest Python snippet to send a LightVerdict as a Telegram message using an existing bot token?

Output: bullet-point plan per item, code snippets where helpful. Keep it concise.

## Final prompt

Phase 3 planning support for STOCK Light Track. Read ~/vault/projects/stock/context.md.

TASK: Draft a minimal Phase 3 implementation plan for:
1. launchd scheduled monitoring — what plist changes needed to call 'quick-decision --no-prompt' for each watchlist ticker at market open (09:00 TWD)? What threshold triggers a push notification?
2. site/ Quick Pulse page — what's the minimal HTML/JS needed to display the quick-decision.json output as a Traffic Light Card? The existing site uses static files in site/data/.
3. Telegram bot — what's the simplest Python snippet to send a LightVerdict as a Telegram message using an existing bot token?

Output: bullet-point plan per item, code snippets where helpful. Keep it concise.

## Raw output

```text
I will search for `context.md` in the workspace to see if it's available locally, and I'll also examine the existing `launchd` configuration and `site/` structure to inform the Phase 3 plan.
I will read the existing `launchd` configuration and the `site/index.html` file to understand the current setup, and I'll also search for the `quick-decision` command in the source code to see how it's implemented.
I will read the `src/stock_research/quick_decision.py` file to understand the structure of the JSON output and the threshold for push notifications, and I'll also check `requirements.txt` to see which Telegram libraries are available.
I will read the `pyproject.toml` file to check for project dependencies.
I will search for `watchlist` in the codebase to determine how it's managed, which will help refine the `launchd` configuration.
I will read the `scripts/quick_pulse_monitor.sh` file to see if it contains any existing logic that can be reused for the Phase 3 plan.
I will check if the `src/stock_research/notify_telegram.py` file exists to see if the notification logic is already implemented.
I will check if the `automation/run/quick-decision.json` file exists and read its content to understand the schema for the Phase 3 plan.
I will read `src/stock_research/config.py` to determine the value of `AUTOMATION_ROOT`, which will help in placing the `quick-decision.json` file where the site can fetch it.
This Phase 3 implementation plan focuses on automating the "Light Track" workflow to provide real-time, high-signal alerts and a visual dashboard for quick decision-making.

### 1. `launchd` Scheduled Monitoring
To automate the daily market-open check, we will leverage a new `launchd` agent that triggers the `quick-decision` logic for all watchlist tickers.

*   **Plist Configuration:** Create `launchd/com.ro9air.stock-research.pulse.plist` scheduled for **09:00 TWD** (01:00 UTC).
*   **Threshold for Notification:** A push notification is triggered when `status == "BUY"`. In `quick_decision.py`, this occurs when the **ADR premium > 5%** and **RSI is not "overbought"**.
*   **Script Update:** Modify `scripts/quick_pulse_monitor.sh` to automatically fetch live prices (via `yfinance` or similar) and sync the resulting `quick-decision.json` to `site/data/` for the dashboard.

```xml
<!-- launchd/com.ro9air.stock-research.pulse.plist snippet -->
<key>StartCalendarInterval</key>
<dict>
    <key>Hour</key><integer>9</integer>
    <key>Minute</key><integer>0</integer>
</dict>
<key>ProgramArguments</key>
<array>
    <string>/bin/zsh</string>
    <string>/Users/ro9air/projects/STOCK/scripts/quick_pulse_monitor.sh</string>
</array>
```

### 2. `site/` Quick Pulse Page
The "Quick Pulse" page provides a "Traffic Light" visual for the latest automated verdict.

*   **Minimal HTML/JS:** Create `site/quick_pulse.html` that fetches `data/quick-decision.json`.
*   **Visual Logic:**
    *   **Green (BUY):** Premium > 5%, RSI cool.
    *   **Yellow (WAIT):** Premium > 5%, but RSI overbought or gap too wide.
    *   **Gray (PASS):** Premium < 5%.

```html
<!-- site/quick_pulse.html snippet -->
<div id="pulse-card" class="card">
  <div class="status-light"></div>
  <h2 id="ticker">--</h2>
  <p id="verdict">Loading...</p>
  <div id="rationale"></div>
</div>

<script>
  fetch('./data/quick-decision.json')
    .then(r => r.json())
    .then(d => {
      document.getElementById('ticker').innerText = d.ticker;
      document.getElementById('verdict').innerText = d.status;
      const card = document.getElementById('pulse-card');
      card.className = `card status-${d.status.toLowerCase()}`;
      document.getElementById('rationale').innerHTML = d.rationale.map(r => `<li>${r}</li>`).join('');
    });
</script>
```

### 3. Telegram Bot Snippet
A minimal Python script to send the `LightVerdict` to a Telegram chat. No heavy libraries required; `urllib.request` is sufficient.

```python
# src/stock_research/notify_telegram.py snippet
import json, urllib.request

def send_telegram_alert(token, chat_id, verdict_data):
    msg = (f"🚨 *{verdict_data['ticker']} Light Pulse: {verdict_data['status']}*\n\n"
           f"Confidence: {verdict_data['confidence']*100:.0f}%\n"
           f"Rationale: {verdict_data['rationale'][0]}\n\n"
           f"_{verdict_data['disclaimer']}_")
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    req = urllib.request.Request(url, method="POST")
    req.add_header('Content-Type', 'application/json')
    data = json.dumps({"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"}).encode()
    
    with urllib.request.urlopen(req, data=data) as f:
        return f.status == 200

# Usage in shell: python3 notify_telegram.py --ticker 2330 --verdict-file automation/run/quick-decision.json
```


YOLO mode is enabled. All tool calls will be automatically approved.
YOLO mode is enabled. All tool calls will be automatically approved.
Error executing tool read_file: File not found.
Error executing tool read_file: File path '/Users/ro9air/projects/STOCK/automation/run/quick-decision.json' is ignored by configured ignore patterns.

```

## Concise summary

Provider completed successfully. Review the raw output for details.

## Action items

- Review the response and extract decisions you want to apply.
- Capture follow-up implementation tasks if needed.
