#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:-/mnt/data/Metablooms_OS}
GATE="$ROOT/runtime/governance/per_action_tool_interception_v1/pre_tool_action_gate_v1.js"
FIX="$ROOT/runtime/governance/per_action_tool_interception_v1/fixtures"
OUT=/mnt/data/metablooms_stage6b_work/fixture_results.jsonl
: > "$OUT"
run_fixture(){
  local fixture_name="$1"
  local expected="$2"
  local file="$FIX/$fixture_name"
  set +e
  local output status decision pass_bool
  output=$(node "$GATE" "$file" 2>&1)
  status=$?
  set -e
  decision=$(printf '%s' "$output" | node -e 'let s=""; process.stdin.on("data",d=>s+=d); process.stdin.on("end",()=>{try{let o=JSON.parse(s); console.log(o.decision)}catch(e){console.log("PARSE_ERROR")}})')
  if [ "$decision" = "$expected" ]; then pass_bool=true; else pass_bool=false; fi
  printf '{"fixture":"%s","expected":"%s","actual":"%s","status":%s,"pass":%s}\n' "$fixture_name" "$expected" "$decision" "$status" "$pass_bool" >> "$OUT"
  [ "$decision" = "$expected" ]
}
run_fixture allow_shell_read_envelope.json ALLOW
run_fixture deny_forbidden_unzip_envelope.json DENY
run_fixture defer_see_missing_envelope.json DEFER
run_fixture require_approval_export_envelope.json REQUIRE_APPROVAL
cat "$OUT"
