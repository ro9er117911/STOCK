#!/usr/bin/env bash
set -euo pipefail

echo "=== [harness/init.sh] ==="

echo "[pwd]"
pwd

echo "[git status]"
git status --short || true

echo "[git log]"
git log --oneline -10 || true

echo "[python env]"
python3 --version || true

if [ -f pyproject.toml ]; then
  echo "[pytest quick check]"
  python3 -m pytest tests/ --tb=short -q 2>&1 | tail -5 || true
fi

echo "[feature_list.json summary]"
if [ -f feature_list.json ]; then
  python3 -c "
import json
fl = json.load(open('feature_list.json'))
total = len(fl)
done = sum(1 for f in fl if f['passes'])
print(f'Features: {done}/{total} passed')
for f in fl:
    status = '✅' if f['passes'] else '❌'
    print(f'  {status} {f[\"id\"]} [{f[\"priority\"]}] {f[\"description\"][:60]}')
" || true
fi

echo "[done]"
