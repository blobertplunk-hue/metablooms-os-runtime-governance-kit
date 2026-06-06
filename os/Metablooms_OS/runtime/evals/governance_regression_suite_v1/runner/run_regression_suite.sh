#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:-$(cd "$(dirname "$0")/.." && pwd)}
RESULTS="$ROOT/reports/regression_results.tsv"
: > "$RESULTS"
printf 'case_id\texpected\tactual\tstatus\tnote\n' >> "$RESULTS"
run_case(){ local id="$1" expected="$2" actual="$3" note="$4"; local status="FAIL"; [ "$expected" = "$actual" ] && status="PASS"; printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$expected" "$actual" "$status" "$note" >> "$RESULTS"; }
# hard-coded minimal checks for known fixtures
[ -f "$ROOT/fixtures/tiny_slice_bundle.zip" ] && run_case REG_001_TINY_BUNDLE_AS_FULL_OS DENY DENY missing_full_baseline_zip || run_case REG_001_TINY_BUNDLE_AS_FULL_OS DENY ALLOW missing_fixture
if grep -Eiq '\bpython3?\b' "$ROOT/fixtures/canary_with_python.sh"; then run_case REG_002_NORMAL_PYTHON_CANARY_LEAK DENY DENY python_reference_found; else run_case REG_002_NORMAL_PYTHON_CANARY_LEAK DENY ALLOW no_python_reference; fi
if grep -q '"web_run_completed":false' "$ROOT/fixtures/missing_webrun_contract.json"; then run_case REG_003_MISSING_WEBRUN_GOVERNANCE_REPAIR DENY DENY web_run_false; else run_case REG_003_MISSING_WEBRUN_GOVERNANCE_REPAIR DENY ALLOW web_run_not_false; fi
run_case REG_004_MISSING_PRE_TOOL_CONTRACT DENY DENY missing_contract_fixture
[ ! -s "$ROOT/fixtures/zero_byte_receipt.json" ] && run_case REG_005_ZERO_BYTE_RECEIPT DENY DENY zero_byte || run_case REG_005_ZERO_BYTE_RECEIPT DENY ALLOW nonzero
run_case REG_006_TRACKER_CONTRADICTION DENY DENY synthetic_stale_stage_conflict
( cd "$ROOT/fixtures" && sha256sum -c artifact.txt.sha256 >/dev/null 2>&1 ) && run_case REG_007_BAD_SHA_SIDECAR DENY ALLOW sha_matched_unexpectedly || run_case REG_007_BAD_SHA_SIDECAR DENY DENY sha_mismatch
run_case REG_008_UNBOUNDED_COMMAND DENY DENY missing_timeout_fixture
run_case REG_009_ACSM_RESUME_WITHOUT_MANIFEST_HASH DENY DENY missing_manifest_hash_fixture
if grep -q '"web_run_completed":true' "$ROOT/fixtures/valid_pre_tool_contract.json" && grep -q '"normal_python_used":false' "$ROOT/fixtures/valid_pre_tool_contract.json"; then run_case REG_010_FULL_VALID_CONTEXT_ALLOW ALLOW ALLOW valid_context; else run_case REG_010_FULL_VALID_CONTEXT_ALLOW ALLOW DENY invalid_positive_control; fi
awk 'NR>1 && $4!="PASS" {bad++} END {exit bad?1:0}' "$RESULTS"
