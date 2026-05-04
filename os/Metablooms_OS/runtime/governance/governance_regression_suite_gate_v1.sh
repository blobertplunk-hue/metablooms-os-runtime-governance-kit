#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
MIN_CASES="${2:-10}"
RESULTS="$ROOT/runtime/evals/governance_regression_suite_v1/reports/regression_results.tsv"
RUNNER="$ROOT/runtime/evals/governance_regression_suite_v1/runner/run_regression_suite.sh"
[ -s "$RUNNER" ] || { echo '{"decision":"DENY","error":"missing_runner"}'; exit 1; }
[ -s "$RESULTS" ] || { echo '{"decision":"DENY","error":"missing_results"}'; exit 1; }
TOTAL=$(awk -F '\t' 'NR>1 && NF>0 {c++} END{print c+0}' "$RESULTS")
PASS=$(awk -F '\t' 'NR>1 && $4=="PASS" {c++} END{print c+0}' "$RESULTS")
if [ "$TOTAL" -lt "$MIN_CASES" ]; then echo "{\"decision\":\"DENY\",\"error\":\"too_few_cases\",\"total\":$TOTAL}"; exit 1; fi
if [ "$PASS" -ne "$TOTAL" ]; then echo "{\"decision\":\"DENY\",\"error\":\"case_failure\",\"pass\":$PASS,\"total\":$TOTAL}"; exit 1; fi
echo "{\"decision\":\"ALLOW\",\"pass\":$PASS,\"total\":$TOTAL}"
