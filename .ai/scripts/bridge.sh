#!/usr/bin/env bash
set -euo pipefail

# ------------------------------------------------------------------------------
# Auto-patch PATH for NVM/NPM Global Binaries
# ------------------------------------------------------------------------------
if ! command -v omx >/dev/null 2>&1 || ! command -v codex >/dev/null 2>&1; then
  # 1. Try via npm prefix
  NPM_GLOBAL_PREFIX=$(npm config get prefix 2>/dev/null || echo "")
  if [ -n "$NPM_GLOBAL_PREFIX" ] && [ -d "$NPM_GLOBAL_PREFIX/bin" ]; then
    export PATH="$PATH:$NPM_GLOBAL_PREFIX/bin"
  fi
  
  # 2. Try common NVM locations if still missing
  if ! command -v omx >/dev/null 2>&1; then
    NVM_BIN_SEARCH=$(find "$HOME/.nvm/versions/node" -maxdepth 2 -type d -name "bin" 2>/dev/null | sort -V | tail -n1 || echo "")
    if [ -n "$NVM_BIN_SEARCH" ]; then
      export PATH="$PATH:$NVM_BIN_SEARCH"
    fi
  fi
fi

usage() {
  cat <<'EOF'
Usage:
  bridge.sh [--lane auto|omc|omx] [--task PATH] [--dry-run] [--workdir PATH]

Options:
  --lane auto|omc|omx   Choose executor lane. auto prefers omx for read-heavy tasks.
  --task PATH           Use PATH as the frozen task.yaml file.
  --dry-run             Validate the task and print the selected lane without running an executor.
  --workdir PATH        Use PATH as the repository root.
  -h, --help            Show this help.
EOF
}

lane="auto"
dry_run=0
workdir=""
task_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lane)
      lane="${2:-}"
      shift 2
      ;;
    --lane=*)
      lane="${1#*=}"
      shift
      ;;
    --task)
      task_path="${2:-}"
      shift 2
      ;;
    --task=*)
      task_path="${1#*=}"
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
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

if [[ $# -gt 0 ]]; then
  echo "bridge.sh no longer accepts raw request text. Use .ai/scripts/brief.sh first." >&2
  usage
  exit 2
fi

if [[ -n "$workdir" ]]; then
  root="$workdir"
else
  root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi

cd "$root"

handoff_dir="$root/.ai/handoff"
mkdir -p "$handoff_dir"

task_file="${task_path:-$handoff_dir/task.yaml}"
result_file="$handoff_dir/result.md"
tmp_stdout="$(mktemp "${TMPDIR:-/tmp}/bridge.stdout.XXXXXX")"
codex_home="$(mktemp -d "${TMPDIR:-/tmp}/bridge-codex-home.XXXXXX")"
trap 'rm -f "$tmp_stdout"; rm -rf "$codex_home"' EXIT

if [[ ! -f "$task_file" ]]; then
  echo "Missing task file: $task_file" >&2
  exit 1
fi

if ! grep -Eq '^[[:space:]]*status:[[:space:]]*frozen[[:space:]]*$' "$task_file"; then
  echo "Task is not frozen. Run .ai/scripts/freeze.sh before bridge.sh." >&2
  exit 1
fi

detect_lane() {
  local file="$1"
  local task_body

  if grep -Eiq '^[[:space:]]*lane_hint:[[:space:]]*(omx|omc)[[:space:]]*$' "$file"; then
    grep -Eoi '^[[:space:]]*lane_hint:[[:space:]]*(omx|omc)[[:space:]]*$' "$file" | tail -n1 | awk -F': ' '{print $2}'
    return
  fi

  task_body="$(awk '
    BEGIN { capture = 0 }
    /^goal:/ { capture = 1 }
    capture { print }
  ' "$file")"

  if grep -Eiq '(read|scan|summar|review|compare|explore|list|find|inspect|inventory|parallel|report)' <<<"$task_body"; then
    printf 'omx\n'
  else
    printf 'omc\n'
  fi
}

if [[ "$lane" == "auto" ]]; then
  lane="$(detect_lane "$task_file")"
fi

build_prompt() {
  local chosen_lane="$1"

  cat <<EOF
You are the $chosen_lane executor for this repository.

Read $task_file and the smallest set of surrounding files needed to complete the frozen task.

Rules:
1. Keep token usage low.
2. Prefer surgical edits.
3. Run only the minimal relevant checks.
4. Return only markdown with these sections:
   - summary
   - changed_files
   - test_results
   - risks
5. Keep the response concise.
EOF
}

prompt="$(build_prompt "$lane")"

if [[ "$dry_run" -eq 1 ]]; then
  printf 'Dry run complete.\n' >&2
  printf 'lane: %s\n' "$lane" >&2
  printf 'task: %s\n' "$task_file" >&2
  exit 0
fi

status=0
if [[ "$lane" == "omx" ]]; then
  if (
    export CODEX_HOME="$codex_home"
    printf '%s\n' "$prompt" | omx exec --cd "$root" --sandbox workspace-write --full-auto --output-last-message "$tmp_stdout" -
  ); then
    status=0
  else
    status=$?
    if command -v codex >/dev/null 2>&1; then
      echo "omx exec failed with status $status; falling back to codex exec" >&2
      if (
        export CODEX_HOME="$codex_home"
        printf '%s\n' "$prompt" | codex exec --cd "$root" --sandbox workspace-write --full-auto --output-last-message "$tmp_stdout" -
      ); then
        status=0
      else
        status=$?
      fi
    fi
  fi
else
  if claude -p --permission-mode auto --tools default "$prompt" >"$tmp_stdout"; then
    status=0
  else
    status=$?
  fi
fi

if [[ -s "$tmp_stdout" ]]; then
  cp "$tmp_stdout" "$result_file"
elif [[ "$status" -ne 0 ]]; then
  cat > "$result_file" <<EOF
summary:
- Executor failed before producing a summary.

changed_files:
- []

test_results:
- failed

risks:
- Review the executor stderr and rerun the bridge.
EOF
fi

printf 'Generated: %s\n' "$result_file" >&2
exit "$status"
