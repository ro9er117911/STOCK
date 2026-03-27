# Stock Research Operator

This repo upgrades the original `stock-research-operator` prompt into a durable research system:

- `research/<ticker>/current.md` is the human-readable living thesis.
- `research/<ticker>/state.json` is the machine-readable state used by automation.
- `research/<ticker>/events.jsonl` is the event ledger.
- GitHub Actions polls high-signal sources even when the Mac is off.
- Material updates become a reviewable PR instead of silently rewriting `main`.

## Repo Layout

```text
research/
  PLTR/
  MSFT/
  MAR/
  system/watchlist.json
stock_research/
  pipeline.py
  sources.py
  llm.py
scripts/
  research_ops.py
  local_catchup.sh
.github/workflows/research-refresh.yml
launchd/com.ro9air.stock-research.catchup.plist
```

## What Is Automated

The pipeline only uses high-signal inputs in v1:

- SEC filings: `8-K`, `10-Q`, `10-K`
- Company investor/news feeds or official release pages
- Price gaps and abnormal volume from Yahoo Finance chart data

Each event is normalized into:

- `event_id`
- `ticker`
- `source_type`
- `occurred_at`
- `title`
- `source_url`
- `affected_assumption_ids[]`
- `marginal_impact`
- `threshold_breach`
- `requires_refresh`

## Local Commands

Bootstrap the baseline living research files:

```bash
python3 scripts/research_ops.py bootstrap-baselines --force
```

Poll the live sources and update ledgers/cursors:

```bash
python3 scripts/research_ops.py poll --trigger event
```

Generate draft refreshes for material updates:

```bash
python3 scripts/research_ops.py draft-refresh --trigger event
```

## GitHub Actions Setup

1. Create the GitHub repo and push this folder.
2. Add repository secret `OPENAI_API_KEY`.
3. Optional: add repository variable `OPENAI_MODEL` if you want something other than `gpt-5.4-mini`.
4. Enable Actions.

The workflow does two things:

- On `main`, it commits event-ledger and cursor updates.
- If a material update is detected, it creates or updates a PR from `automation/research-refresh`.
- If a workflow-dispatch fixture is provided, it skips writing test events to `main` and opens a fixture-specific PR branch instead.

## Test Fixtures

The repo ships with one deterministic test event bundle:

```text
automation/test_events/msft_copilot_breakout.json
```

You can run it locally:

```bash
python3 scripts/research_ops.py poll --trigger manual --fixture msft_copilot_breakout
python3 scripts/research_ops.py draft-refresh --trigger manual --fixture msft_copilot_breakout
```

You can also trigger it from GitHub Actions by setting workflow input `fixture=msft_copilot_breakout`.

## Localization

After every refresh, the pipeline keeps the original research artifacts and then adds a final localization node:

- `research/<ticker>/current.zh-tw.md`
- `research/<ticker>/artifacts/review_summary.zh-tw.md`
- `automation/run/pr-body.zh-tw.md`

That final localization step uses `gpt-4.1-mini`.

## macOS Catch-Up Job

`scripts/local_catchup.sh` is intentionally small. It:

- fetches and fast-forwards `main`
- writes the list of open PRs into `automation/run/open-prs.txt`
- syncs `prep/` into `research/inbox/prep/`

Install the LaunchAgent:

```bash
mkdir -p ~/Library/LaunchAgents
cp launchd/com.ro9air.stock-research.catchup.plist ~/Library/LaunchAgents/
launchctl unload ~/Library/LaunchAgents/com.ro9air.stock-research.catchup.plist 2>/dev/null || true
launchctl load ~/Library/LaunchAgents/com.ro9air.stock-research.catchup.plist
```

## Notes

- If `OPENAI_API_KEY` is not set, the refresh step falls back to a deterministic rule-based draft.
- Default research model is `gpt-5.4-mini`. Set repository variable `OPENAI_MODEL` to override it without changing code.
- SEC polling is implemented as a best-effort official source. If SEC blocks your runner IP, the workflow will continue with investor-news and price signals while logging the SEC error in the poll summary.
- Feed endpoints are configurable in [`stock_research/config.py`](/Users/ro9air/STOCK/stock_research/config.py).
- The living thesis files are meant to be reviewed in PRs, not edited blindly by automation.
