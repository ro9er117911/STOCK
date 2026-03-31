# Stock Research Operator

This repo upgrades the original `stock-research-operator` prompt into a durable, personal-first research decision OS:

- `research/<ticker>/current.md` is the human-readable living thesis.
- `research/<ticker>/state.json` is the machine-readable state used by automation.
- `research/system/candidates.json` is the manually editable candidate queue and workflow index.
- `research/<ticker>/events.jsonl` is the event ledger.
- `research/<ticker>/artifacts/review_summary.json` is the machine-readable refresh artifact.
- `research/system/source_registry.json` is the source-of-truth whitelist for event inputs.
- `research/system/portfolio.private.json.example` is the template for local-only position data.
- GitHub Actions polls high-signal sources even when the Mac is off.
- Material updates become a reviewable PR instead of silently rewriting `main`.
- PR, email, and dashboard are rendered from the same canonical digest instead of ad hoc string assembly.

## vNext Decision Workflow

The repo now treats research as a workflow, not just a post-hoc holdings monitor:

`candidate -> in_research -> ready_to_decide -> active / rejected / archived`

The machine-readable contract in each `state.json` now includes:

- `research_stage`, `candidate_origin`, `decision_status`, `decision_updated_at`
- `radar_flags[]`, `radar_summary`, `radar_risk_level`
- `outcome_markers[]`, `thesis_change_log[]`, `invalidation_reason`, `consistency_notes[]`

Quant inputs are intentionally advisory only in vNext. They can prioritize and warn, but they do not act as hard vetoes or trade-execution signals.

## Repo Layout

```text
research/
  PLTR/
  MSFT/
  MAR/
  system/source_registry.json
  system/portfolio.private.json.example
stock_research/
  pipeline.py
  sources.py
  llm.py
  digest.py
  notify.py
site/
docs/
  README.md
  architecture/
  audits/
  guides/
  reference/
  walkthroughs/
scripts/
  research_ops.py
  local_catchup.sh
.github/workflows/research-refresh.yml
.github/workflows/dashboard-site.yml
launchd/com.ro9air.stock-research.catchup.plist
```

The repo root is intentionally kept lean. Long-form planning notes, audits, walkthroughs, and imported reference material now live under `docs/`.

## Python Setup

Recommended local setup from a clean checkout:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

This repo now keeps Python dependency metadata in `pyproject.toml`. For environments that prefer requirements files, `requirements-dev.txt` is a thin wrapper around the same editable install.

Once installed, you can use either interface:

```bash
research-ops --help
python scripts/research_ops.py --help
```

Run the test suite with:

```bash
python -m pytest
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

Normalize existing dossiers to the vNext contract and rebuild the candidate queue:

```bash
python3 scripts/research_ops.py sync-research-contracts
```

Rebuild the candidate queue only:

```bash
python3 scripts/research_ops.py sync-candidates
```

Create or advance a manual candidate dossier:

```bash
python3 scripts/research_ops.py upsert-candidate \
  --ticker NVDA \
  --company-name "NVIDIA" \
  --research-topic "AI capex beneficiary with valuation discipline" \
  --origin manual_watchlist \
  --stage in_research \
  --radar-flag "52-week breakout" \
  --radar-summary "Strong price confirmation, but valuation is already rich." \
  --radar-risk-level medium \
  --note "Promoted from watchlist into active pre-entry research."
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

Local usage:

- tracked public site: `site/`
- local private cockpit, only when `research/system/portfolio.private.json` exists: `automation/run/dashboard-local/`

Preview either static site with a temporary server:

```bash
python3 -m http.server 8765 -d site
```

If you have private positions configured, preview the private cockpit instead:

```bash
python3 -m http.server 8765 -d automation/run/dashboard-local
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
- `research/<ticker>/artifacts/citations.json`
- `site/data/portfolio.json`
- `site/data/tickers/<ticker>.json`
- `site/research/<ticker>.html`

Delivery surfaces:

- GitHub PR body
- Resend email summary
- Static dashboard artifact / GitHub Pages-ready site

Runtime-only artifacts:

- `automation/run/*.json`
- `automation/run/pr-body*.md`
- `automation/run/email-preview.*`
- `automation/run/dashboard-local/`

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
- Local-only position data belongs in [`portfolio.private.json.example`](/Users/ro9air/STOCK/research/system/portfolio.private.json.example) copied to `research/system/portfolio.private.json`.
- Operator-facing workflow and output docs live in [`operator-guide.md`](/Users/ro9air/STOCK/docs/operator-guide.md).
- The living thesis files are meant to be reviewed in PRs, not edited blindly by automation.
