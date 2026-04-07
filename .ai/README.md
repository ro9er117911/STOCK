# .ai Runtime Handoff

This directory is the local handoff layer for the active workflow mainline.

The workflow is split into three stages:

1. `brief.sh` compiles a bounded draft into `task.yaml`.
2. `freeze.sh` promotes the draft to a frozen contract.
3. `bridge.sh` executes only frozen tasks and writes `result.md`.

## Runtime Files

- `.ai/handoff/request.txt`: raw request snapshot written by `brief.sh`
- `.ai/handoff/task.yaml`: canonical bounded task spec in draft or frozen form
- `.ai/handoff/result.md`: executor summary returned to PM
- `.ai/handoff/*.template`: reference templates only

## Launcher

- `.ai/scripts/brief.sh`: compile-only PM helper that writes a draft `task.yaml`
- `.ai/scripts/freeze.sh`: governance gate that promotes draft tasks to frozen
- `.ai/scripts/bridge.sh`: execute-only launcher that selects `omc` or `omx` and writes `result.md`
- `.ai/governance.md`: stage gates and rework rules for the runtime workflow

## Rules

- Keep one bounded task per run.
- Drafts are allowed to change; frozen tasks are not.
- Do not treat `.ai/` as a product-spec folder.
- Do not treat `.codex/` or `.omx/` as repo source of truth; they are hidden local runtime state.
