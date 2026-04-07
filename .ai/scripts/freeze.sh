#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  freeze.sh [--task PATH] [--workdir PATH]

Options:
  --task PATH           Use PATH as the task.yaml file.
  --workdir PATH        Use PATH as the repository root.
  -h, --help            Show this help.
EOF
}

task_path=""
workdir=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --task)
      task_path="${2:-}"
      shift 2
      ;;
    --task=*)
      task_path="${1#*=}"
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
  echo "freeze.sh expects a task file, not raw request text." >&2
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

if [[ ! -f "$task_file" ]]; then
  echo "Missing task file: $task_file" >&2
  exit 1
fi

if grep -Eq '^[[:space:]]*status:[[:space:]]*frozen[[:space:]]*$' "$task_file"; then
  printf 'Task already frozen: %s\n' "$task_file" >&2
  exit 0
fi

if ! grep -Eq '^[[:space:]]*status:[[:space:]]*draft[[:space:]]*$' "$task_file"; then
  echo "Task file does not contain governance.status: draft" >&2
  exit 1
fi

perl -0pi -e 's/^([[:space:]]*status:[[:space:]]*)draft([[:space:]]*)$/${1}frozen${2}/m' "$task_file"

printf 'Task frozen: %s\n' "$task_file" >&2
