#!/usr/bin/env bash
set -euo pipefail
CONTRACT=${1:?contract json required}
if command -v jq >/dev/null 2>&1; then
  jq -e '.stage_id and .lane and .timeout_seconds and .kill_after_seconds and .max_steps and .fallback_lane and .receipt_path and (.normal_python_allowed == false) and (.all_in_one_stage == false)' "$CONTRACT" >/dev/null
  if jq -e '(.task_class|tostring|test("governance|repair|failure|improvement")) and (.web_run_required == true) and (.web_run_done != true)' "$CONTRACT" >/dev/null; then
    echo '{"decision":"DENY","reason":"governance repair requires completed web.run"}'
    exit 1
  fi
  echo '{"decision":"ALLOW","validator":"verify_pre_tool_contract.sh"}'
else
  grep -q '"normal_python_allowed"[[:space:]]*:[[:space:]]*false' "$CONTRACT"
  grep -q '"all_in_one_stage"[[:space:]]*:[[:space:]]*false' "$CONTRACT"
  grep -q '"timeout_seconds"' "$CONTRACT"
  echo '{"decision":"ALLOW","validator":"verify_pre_tool_contract.sh","mode":"grep_fallback"}'
fi
