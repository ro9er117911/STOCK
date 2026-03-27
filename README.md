# Stock Research Operator

This repo upgrades the original `stock-research-operator` prompt into a durable research system:

- `research/<ticker>/current.md` is the human-readable living thesis.
- `research/<ticker>/state.json` is the machine-readable state used by automation.
- `research/<ticker>/events.jsonl` is the event ledger.
- `research/<ticker>/artifacts/review_summary.json` is the machine-readable refresh artifact.
- `research/system/source_registry.json` is the source-of-truth whitelist for event inputs.
- GitHub Actions polls high-signal sources even when the Mac is off.
- Material updates become a reviewable PR instead of silently rewriting `main`.
- PR, email, and dashboard are rendered from the same canonical digest instead of ad hoc string assembly.

## Repo Layout

```text
research/
  PLTR/
  MSFT/
  MAR/
  system/source_registry.json
stock_research/
  pipeline.py
  sources.py
  llm.py
  digest.py
  notify.py
site/
docs/operator-guide.md
scripts/
  research_ops.py
  local_catchup.sh
.github/workflows/research-refresh.yml
.github/workflows/dashboard-site.yml
launchd/com.ro9air.stock-research.catchup.plist
```

## What Is Automated

The pipeline only uses high-signal inputs in v1:

- SEC filings: `8-K`, `10-Q`, `10-K`
- Company investor/news feeds or official release pages
- Price gaps and abnormal volume from Yahoo Finance chart data

All live input sources now come from:

```text
research/system/source_registry.json
```

That file is the whitelist. If a source is not listed there as `active`, the pipeline does not poll it.

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

Build the private-first dashboard artifact:

```bash
python3 scripts/research_ops.py build-dashboard
```

Send a material-update email preview or live email:

```bash
python3 scripts/research_ops.py send-email \
  --run-type event \
  --pr-url https://github.com/OWNER/REPO/pull/123 \
  --dashboard-url https://github.com/OWNER/REPO/actions/workflows/dashboard-site.yml
```

## GitHub Actions Setup

1. Create the GitHub repo and push this folder.
2. Add repository secret `OPENAI_API_KEY`.
3. Optional: add repository variable `OPENAI_MODEL` if you want something other than `gpt-5.4-mini`.
4. Optional email secrets for Resend:
   - `RESEND_API_KEY`
   - `RESEND_FROM_EMAIL`
   - `RESEND_TO_EMAIL`
5. Optional dashboard variables:
   - `DASHBOARD_BASE_URL`
   - `ENABLE_DASHBOARD_PUBLISH=true` once GitHub Pages is ready
6. Enable Actions.

The workflow does two things:

- On `main`, it commits event-ledger and cursor updates.
- If a material update is detected, it creates or updates a PR from `automation/research-refresh`.
- If a workflow-dispatch fixture is provided, it skips writing test events to `main` and opens a fixture-specific PR branch instead.
- On material refresh PR create/update, it can send a Resend email summary.
- A separate dashboard workflow builds a Pages-ready static site artifact from merged `main`.

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

## Outputs

Formal outputs:

- `research/<ticker>/current.md`
- `research/<ticker>/state.json`
- `research/<ticker>/artifacts/review_summary.json`
- `research/<ticker>/artifacts/digest.json`
- `site/data/portfolio.json`
- `site/data/tickers/<ticker>.json`

Delivery surfaces:

- GitHub PR body
- Resend email summary
- Static dashboard artifact / GitHub Pages-ready site

Runtime-only artifacts:

- `automation/run/*.json`
- `automation/run/pr-body*.md`
- `automation/run/email-preview.*`

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
- Feed endpoints are configurable through [`source_registry.json`](/Users/ro9air/STOCK/research/system/source_registry.json).
- Operator-facing workflow and output docs live in [`operator-guide.md`](/Users/ro9air/STOCK/docs/operator-guide.md).
- The living thesis files are meant to be reviewed in PRs, not edited blindly by automation.
