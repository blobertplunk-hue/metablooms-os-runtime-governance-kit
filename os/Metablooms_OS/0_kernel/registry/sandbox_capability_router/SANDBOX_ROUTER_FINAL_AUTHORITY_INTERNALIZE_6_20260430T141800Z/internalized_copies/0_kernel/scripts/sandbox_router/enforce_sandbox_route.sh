#!/usr/bin/env bash
set -euo pipefail
ROOT="${METABLOOMS_ROOT:-/mnt/data/Metablooms_OS}"
TASK="${1:-boot_probe}"
METHOD="${2:-auto}"
TIMEOUT_SECONDS="${SANDBOX_ROUTER_TIMEOUT_SECONDS:-5}"
PY_EVAL="$ROOT/0_kernel/lib/sandbox_router_policy_loader_v1.py"
NODE_EVAL="$ROOT/0_kernel/lib/sandbox_router_enforcer_v1.mjs"
TMP_OUT="$(mktemp)"
TMP_ERR="$(mktemp)"
cleanup(){ rm -f "$TMP_OUT" "$TMP_ERR"; }
trap cleanup EXIT
# Default path: python3 -S evaluator. It avoids normal python site hooks and avoids direct Node timeout hangs.
if command -v python3 >/dev/null 2>&1 && [ -f "$PY_EVAL" ]; then
  set +e
  timeout --kill-after=1s "${TIMEOUT_SECONDS}s" python3 -S "$PY_EVAL" "$TASK" "$METHOD" >"$TMP_OUT" 2>"$TMP_ERR"
  code=$?
  set -e
  if [ "$code" -eq 0 ] || [ "$code" -eq 7 ]; then
    cat "$TMP_OUT"
    [ -s "$TMP_ERR" ] && cat "$TMP_ERR" >&2 || true
    exit "$code"
  fi
  # timeout(1) normally returns 124 on timeout; fall through to Node fallback for evaluator runtime failure.
fi
if command -v node >/dev/null 2>&1 && [ -f "$NODE_EVAL" ]; then
  set +e
  timeout --kill-after=1s "${TIMEOUT_SECONDS}s" node "$NODE_EVAL" "$TASK" "$METHOD" >"$TMP_OUT" 2>"$TMP_ERR"
  code=$?
  set -e
  cat "$TMP_OUT"
  [ -s "$TMP_ERR" ] && cat "$TMP_ERR" >&2 || true
  exit "$code"
fi
printf '{"allowed":false,"decision":"DENY","reason":"no_evaluator_available","task":"%s","method":"%s"}\n' "$TASK" "$METHOD"
exit 9
