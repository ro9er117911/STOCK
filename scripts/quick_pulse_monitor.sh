#!/bin/zsh
# Quick Pulse Monitor — runs at TWD market open (09:00 TWD / 01:00 UTC)
# Auto-fetches ADR premium via yfinance and sends alert if signal is BUY or PASS

set -e
REPO_DIR="/Users/ro9air/projects/STOCK"
cd "$REPO_DIR"

ENV_FILE="$HOME/.stock-quick-pulse.env"
if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
fi

# Watchlist tickers (must have adr_symbol in source_registry.json)
WATCHLIST=("2330")

for TICKER in "${WATCHLIST[@]}"; do
  echo "[$(date -u)] Running Quick Pulse for $TICKER (auto-fetch mode)"

  # Auto-fetch mode: no env vars needed, yfinance fetches TSM + USDTWD
  python3 -m src.stock_research quick-decision \
    --ticker "$TICKER" \
    --trigger-description "Scheduled market-open pulse check" \
    --no-prompt 2>&1

  # Read verdict status
  STATUS=$(python3 -c "
import json
with open('automation/run/quick-decision.json') as f:
    d = json.load(f)
print(d.get('status', 'UNKNOWN'))
" 2>/dev/null || echo "UNKNOWN")

  echo "[$(date -u)] $TICKER verdict: $STATUS"

  # Copy to site/data for Quick Pulse page
  cp automation/run/quick-decision.json site/data/quick-decision.json 2>/dev/null || true

  # Send LINE Messaging API alert for BUY or PASS (skip WAIT)
  if [ "$STATUS" = "BUY" ] || [ "$STATUS" = "PASS" ]; then
    if [ -n "$LINE_CHANNEL_ACCESS_TOKEN" ] || { [ -n "$LINE_CHANNEL_ID" ] && [ -n "$LINE_CHANNEL_SECRET" ]; }; then
      python3 -m src.stock_research.notify_line \
        --verdict-file automation/run/quick-decision.json \
        2>/dev/null || echo "[$(date -u)] LINE Messaging API failed"
    else
      echo "[$(date -u)] LINE Messaging API skipped (channel credential not set)"
    fi
  fi
done

echo "[$(date -u)] Quick Pulse monitor complete"
