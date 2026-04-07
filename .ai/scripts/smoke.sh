#!/usr/bin/env bash
set -euo pipefail

# .ai/scripts/smoke.sh - AI Workflow Smoke Test
# Validates the brief -> freeze -> bridge closed loop.

usage() {
  cat <<EOF
Usage:
  $(basename "$0") "request text"

Description:
  Executes a smoke test of the AI workflow in a temporary directory.
  Verifies that bridge.sh rejects unfrozen tasks and accepts frozen ones.
EOF
}

if [[ $# -eq 0 ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
  usage
  exit 0
fi

REQUEST="$1"

# Setup temporary environment
TMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/ai-smoke-test.XXXXXX")
trap 'rm -rf "$TMP_ROOT"' EXIT

# Locate scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRIEF="$SCRIPT_DIR/brief.sh"
FREEZE="$SCRIPT_DIR/freeze.sh"
BRIDGE="$SCRIPT_DIR/bridge.sh"

echo "🚀 Starting AI Workflow Smoke Test..."
echo "📂 Temp Workdir: $TMP_ROOT"
echo "📝 Request: $REQUEST"
echo

# ------------------------------------------------------------------------------
# Test 1: Unfrozen Rejection
# ------------------------------------------------------------------------------
echo "🧪 Test 1: Checking that unfrozen task is rejected by bridge.sh..."

# Generate draft
"$BRIEF" --workdir "$TMP_ROOT" "$REQUEST" > /dev/null

# Attempt bridge (should fail)
if "$BRIDGE" --workdir "$TMP_ROOT" --dry-run > /dev/null 2>&1; then
  echo "❌ FAIL: bridge.sh executed an unfrozen task!"
  exit 1
else
  echo "✅ PASS: bridge.sh correctly rejected unfrozen task."
fi

# ------------------------------------------------------------------------------
# Test 2: Frozen Success
# ------------------------------------------------------------------------------
echo "🧪 Test 2: Checking that frozen task is accepted by bridge.sh..."

# Freeze the task
"$FREEZE" --workdir "$TMP_ROOT" > /dev/null

# Attempt bridge (should pass in dry-run)
if "$BRIDGE" --workdir "$TMP_ROOT" --dry-run > /dev/null; then
  echo "✅ PASS: bridge.sh accepted frozen task (dry-run)."
else
  # shellcheck disable=SC2181
  echo "❌ FAIL: bridge.sh rejected a frozen task! (Exit code: $?)"
  exit 1
fi

echo
echo "✨ ALL SMOKE TESTS PASSED! ✨"
exit 0
