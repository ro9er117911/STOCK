#!/bin/zsh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

mkdir -p automation/run research/inbox/prep

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git fetch origin --prune || true
  if [ "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo detached)" = "main" ]; then
    git pull --ff-only origin main || true
  fi
fi

gh pr list --state open --limit 20 > automation/run/open-prs.txt || true

if [ -d prep ]; then
  rsync -a --delete --exclude '.DS_Store' prep/ research/inbox/prep/
fi
