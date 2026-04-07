#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  brief.sh [--workdir PATH] "request..."

Options:
  --workdir PATH        Use PATH as the repository root.
  -h, --help            Show this help.
EOF
}

workdir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir)
      workdir="${2:-}"
      shift 2
      ;;
    --workdir=*)
      workdir="${1#*=}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

request="${*:-}"
if [[ -z "$request" ]]; then
  usage
  exit 1
fi

if [[ -n "$workdir" ]]; then
  root="$workdir"
else
  root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

cd "$root"

handoff_dir="$root/.ai/handoff"
mkdir -p "$handoff_dir"

request_file="$handoff_dir/request.txt"
task_file="$handoff_dir/task.yaml"

printf '%s\n' "$request" > "$request_file"

cat > "$task_file" <<EOF
governance:
  status: draft
  owner: PM
  lane_hint: auto
  change_budget: 1
  review_gate: codex-on-convergence
goal: |
$(printf '%s\n' "$request" | sed 's/^/  /')
scope:
  - pending
constraints:
  - minimum token usage
  - minimum file edits
  - preserve existing patterns
  - no db schema change unless explicitly requested
acceptance:
  - draft reviewed and frozen before execution
output:
  - summary
  - changed_files
  - test_results
  - risks
EOF

printf 'Draft brief written.\n' >&2
printf 'request: %s\n' "$request_file" >&2
printf 'task: %s\n' "$task_file" >&2
printf 'next: run .ai/scripts/freeze.sh before bridge.sh\n' >&2
