#!/usr/bin/env bash
set -euo pipefail
ROOT=${1:-$(cd "$(dirname "$0")/.." && pwd)}
cd "$ROOT"
for f in 00_BOOT/METABLOOMS_PROJECT_BOOT_OVERLAY_POINTER_v1.json 02_VALIDATORS/verify_pre_tool_contract.sh 02_VALIDATORS/verify_export_bundle_guard.sh 03_INSTALL/apply_overlay_to_project_files.sh; do
  [ -f "$f" ] || { echo "DENY missing $f"; exit 1; }
done
for id in PRE_TOOL_EXECUTION_CONTRACT_v1 WEBRUN_REQUIRED_FOR_GOVERNANCE_REPAIR_v1 RUNAWAY_TURN_BREAKER_v2 NO_NORMAL_PYTHON_FOR_OS_WORK_v1 SHELL_FIRST_CHUNKED_EXECUTION_v1 PYTHON_RESILIENT_EXECUTION_POLICY_v1 FULL_OS_PORTABLE_EXPORT_MUST_INCLUDE_BASELINE_v1; do
  [ -f "01_GOVERNANCE/invariants/$id.json" ] || { echo "DENY missing invariant $id"; exit 1; }
done
[ -f 09_CHECKSUMS/SHA256SUMS.txt ] && sha256sum -c 09_CHECKSUMS/SHA256SUMS.txt >/dev/null
echo '{"decision":"ALLOW","validator":"verify_boot_overlay.sh"}'
