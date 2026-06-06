#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path
ENGINE_ID="PRE_TOOL_EXECUTION_CONTRACT_GATE_v1"
GOV_RE=re.compile(r"governance|invariant|runtime|baseline|guard|policy|web\.run|SEE|CE|failure|failed|repair|improve|plan", re.I)
ALLOWED={"shell_coreutils","jq","node","python3_S","python3_dash_S_stdlib"}
SHELL={"shell_coreutils","jq","node"}
def _i(v,d):
    try: return int(v)
    except Exception: return d
def _contract_errors(c, req):
    e=[]; lane=c.get("lane")
    if lane not in ALLOWED: e.append("invalid_or_missing_lane")
    if lane=="normal_python" or c.get("uses_normal_python") is True: e.append("normal_python_denied_for_governed_os_work")
    if lane in {"python3_S","python3_dash_S_stdlib"}:
        if c.get("single_purpose") is not True: e.append("python3_S_requires_single_purpose")
        if c.get("broad_recursive_scan") or c.get("zip_build") or c.get("full_export"): e.append("python3_S_cannot_do_broad_scan_zip_build_or_full_export")
    if req.get("task_domain") in ("os_export","manifest","archive","filesystem") and lane not in SHELL and req.get("explicit_user_authorized_python3_S") is not True: e.append("os_export_manifest_archive_filesystem_must_be_shell_first")
    if _i(c.get("timeout_seconds"),999999)>25: e.append("timeout_seconds_exceeds_25")
    if _i(c.get("kill_after_seconds"),999999)>5: e.append("kill_after_seconds_exceeds_5")
    if _i(c.get("max_tool_calls"),999999)>2: e.append("max_tool_calls_exceeds_2")
    if _i(c.get("max_steps"),999999)>1: e.append("max_steps_exceeds_1")
    if _i(c.get("max_files"),999999)>250: e.append("max_files_exceeds_250")
    if _i(c.get("max_bytes"),999999999999)>50000000: e.append("max_bytes_exceeds_50000000")
    if not c.get("receipt_path"): e.append("missing_receipt_path")
    if not c.get("fallback_lane"): e.append("missing_fallback_lane")
    if c.get("all_in_one") is True: e.append("all_in_one_stage_denied")
    if _i(c.get("retry_same_lane_count"),0)>0: e.append("retry_same_lane_denied_switch_lanes_instead")
    if c.get("requires_timeout_wrapper") is not True: e.append("timeout_wrapper_required")
    return e
def validate_request(req: dict) -> dict:
    e=[]; cls=req.get("task_class"); txt=req.get("request_text") or req.get("user_request") or req.get("stage_name") or ""
    governed=cls in {"governed_execution","stage_execution","artifact_audit","archive_manifest","os_export","baseline_export","governance_repair","plan_improvement","failure_diagnosis"}
    gov_repair=cls in {"governance_repair","plan_improvement","failure_diagnosis"} or bool(GOV_RE.search(txt))
    if gov_repair:
        if not (req.get("web_run_sources") or req.get("web_sources")): e.append("web_run_required_for_governance_repair")
        if not req.get("SEE_summary"): e.append("SEE_summary_required")
        if not req.get("CE_decision"): e.append("CE_decision_required")
    if governed and req.get("pre_tool_contract_exempt") is not True:
        c=req.get("pre_tool_contract")
        if not isinstance(c, dict): e.append("missing_pre_tool_execution_contract")
        else: e.extend(_contract_errors(c, req))
    return {"engine_id":ENGINE_ID,"decision":"ALLOW" if not e else "DENY","errors":e}
if __name__=="__main__":
    data=json.load(sys.stdin) if len(sys.argv)==1 else json.loads(Path(sys.argv[1]).read_text())
    r=validate_request(data); print(json.dumps(r, indent=2)); raise SystemExit(0 if r["decision"]=="ALLOW" else 1)
