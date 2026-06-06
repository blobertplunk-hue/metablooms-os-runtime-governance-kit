#!/usr/bin/env python3
"""
MetaBlooms Invariant Activation Engine v1

Purpose:
- Turn stored governance/invariant artifacts into executable runtime gates.
- Load active invariants at boot.
- Evaluate every governed stage plan/release artifact before it is used.
- Fail closed when required gates are missing or violated.

This module is intentionally dependency-light and policy-as-data driven.
"""

from __future__ import annotations
from pathlib import Path
import json, hashlib, re, datetime
from typing import Any, Dict, List, Tuple

ENGINE_ID = "METABLOOMS_INVARIANT_ACTIVATION_ENGINE_v1"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def default_root() -> Path:
    return Path("/mnt/data/Metablooms_OS")

def invariant_dirs(root: Path) -> List[Path]:
    return [
        root / "governance" / "invariants",
        root / "0_kernel" / "registry" / "invariants",
        root / "runtime" / "invariants",
    ]

def load_invariants(root: Path) -> List[Dict[str, Any]]:
    loaded = []
    for d in invariant_dirs(root):
        if not d.exists():
            continue
        for p in sorted(d.glob("*.json")):
            try:
                obj = load_json(p)
                obj["_path"] = str(p)
                obj["_sha256"] = sha256_file(p)
                if obj.get("status", "").lower() in {"active", "active_governance_patch", "enabled", "runtime_active"}:
                    loaded.append(obj)
            except Exception as exc:
                loaded.append({
                    "id": f"LOAD_ERROR::{p.name}",
                    "status": "load_error",
                    "_path": str(p),
                    "error": repr(exc)
                })
    return loaded

def validate_tracker_release(input_obj: Dict[str, Any], invariant: Dict[str, Any]) -> List[str]:
    errors = []
    tracker_path = Path(input_obj.get("tracker_path", ""))
    baseline_path = Path(input_obj.get("baseline_path", ""))
    live_state_path = Path(input_obj.get("live_state_path", ""))

    if not tracker_path.exists():
        return [f"tracker_path_missing:{tracker_path}"]
    text = tracker_path.read_text(encoding="utf-8", errors="replace")

    required_sections = invariant.get("required_sections", [
        "Workflow Timeline",
        "Next Valid Stage",
        "Evidence Ledger",
        "Permanent OS / Governance Improvements Ledger",
    ])
    for section in required_sections:
        if section not in text:
            errors.append(f"missing_required_section:{section}")

    next_blocks = re.findall(r"<h2>Next Valid Stage</h2>(.*?)</section>", text, flags=re.S)
    if len(next_blocks) != 1:
        errors.append(f"next_valid_stage_block_count:{len(next_blocks)}")
    else:
        commands = re.findall(r'<div class="code">(.*?)</div>', next_blocks[0], flags=re.S)
        if len(commands) != 1:
            errors.append(f"next_command_block_count:{len(commands)}")

    title_match = re.search(r"<title>(.*?)</title>", text, flags=re.S)
    comment_match = re.findall(r"<!--(.*?)-->", text, flags=re.S)
    title = title_match.group(1).strip() if title_match else ""
    final_comment = comment_match[-1].strip() if comment_match else ""
    version_in_title = re.search(r"v(\d+)", title)
    version_in_comment = re.search(r"V(\d+)|v(\d+)", final_comment)
    if version_in_title and version_in_comment:
        cver = version_in_comment.group(1) or version_in_comment.group(2)
        if version_in_title.group(1) != cver:
            errors.append(f"version_mismatch:title_v{version_in_title.group(1)}_comment_v{cver}")

    if "NON_CANONICAL_STATUS_PAGE" in text and "LIVE_CONTROL_SURFACE" in text:
        errors.append("classification_conflict:noncanonical_and_live")

    # Baseline comparison is existence-bound here; detailed diff can be supplied externally.
    if baseline_path and not baseline_path.exists():
        errors.append(f"baseline_path_missing:{baseline_path}")
    if live_state_path and not live_state_path.exists():
        errors.append(f"live_state_path_missing:{live_state_path}")

    return errors

def validate_research_see_ce(input_obj: Dict[str, Any], invariant: Dict[str, Any]) -> List[str]:
    if input_obj.get("task_class") in {"pure_chat", "non_informational"}:
        return []
    errors = []
    if not input_obj.get("web_sources"):
        errors.append("missing_web_sources")
    if not input_obj.get("SEE_summary"):
        errors.append("missing_SEE_summary")
    if not input_obj.get("CE_decision"):
        errors.append("missing_CE_decision")
    return errors

def validate_no_runtime_write_without_rollback(input_obj: Dict[str, Any], invariant: Dict[str, Any]) -> List[str]:
    errors = []
    if input_obj.get("will_modify_runtime"):
        if not input_obj.get("rollback_manifest_path"):
            errors.append("runtime_write_without_rollback_manifest")
        if not input_obj.get("pre_write_snapshot_path"):
            errors.append("runtime_write_without_pre_write_snapshot")
        if input_obj.get("registry_patch") and not input_obj.get("post_copy_hash_validation"):
            errors.append("registry_patch_without_post_copy_hash_validation")
    return errors

GATE_DISPATCH = {
    "TRACKER_RELEASE_GATE": validate_tracker_release,
    "RESEARCH_SEE_CE_GATE": validate_research_see_ce,
    "RUNTIME_WRITE_ROLLBACK_GATE": validate_no_runtime_write_without_rollback,
}

def evaluate(root: Path, gate_input: Dict[str, Any]) -> Dict[str, Any]:
    invariants = load_invariants(root)
    errors: List[Dict[str, Any]] = []
    evaluated = []
    for inv in invariants:
        gate = inv.get("gate")
        if gate in GATE_DISPATCH:
            gate_errors = GATE_DISPATCH[gate](gate_input, inv)
            evaluated.append({"id": inv.get("id"), "gate": gate, "errors": gate_errors})
            for err in gate_errors:
                errors.append({"invariant_id": inv.get("id"), "gate": gate, "error": err})
    return {
        "engine_id": ENGINE_ID,
        "timestamp_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "root": str(root),
        "invariants_loaded": len(invariants),
        "evaluated": evaluated,
        "decision": "ALLOW" if not errors else "DENY",
        "errors": errors,
    }

def boot(root: Path | None = None) -> Dict[str, Any]:
    root = root or default_root()
    invariants = load_invariants(root)
    return {
        "engine_id": ENGINE_ID,
        "timestamp_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "root": str(root),
        "invariants_loaded": len(invariants),
        "invariants": [
            {"id": inv.get("id"), "gate": inv.get("gate"), "path": inv.get("_path"), "sha256": inv.get("_sha256")}
            for inv in invariants
        ],
    }

if __name__ == "__main__":
    import argparse, sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="/mnt/data/Metablooms_OS")
    parser.add_argument("--input", help="JSON gate input")
    parser.add_argument("--boot", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    if args.boot:
        result = boot(root)
    else:
        gate_input = load_json(Path(args.input)) if args.input else {}
        result = evaluate(root, gate_input)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("decision", "ALLOW") == "ALLOW" else 1)


# FULL_BUNDLE_EXPORT_GATE_WRAPPER_v1
try:
    _MB_ORIGINAL_EVALUATE = evaluate
except NameError:
    _MB_ORIGINAL_EVALUATE = None

def _mb_full_bundle_export_eval(root, request):
    from pathlib import Path
    import importlib.util
    validator = Path(root) / "runtime" / "governance" / "full_bundle_export_guard_v1.py"
    if not validator.exists():
        return {"decision":"DENY","errors":["full_bundle_export_guard_validator_missing"]}
    spec = importlib.util.spec_from_file_location("full_bundle_export_guard_v1", validator)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    bundle_path = request.get("bundle_path") or request.get("export_bundle_path") or request.get("handoff_bundle_path")
    if not bundle_path:
        return {"decision":"DENY","errors":["missing_bundle_path_for_full_bundle_export_gate"]}
    return mod.validate_bundle(bundle_path, request.get("expected_baseline_sha256",""), int(request.get("expected_baseline_min_bytes") or 0))

def evaluate(root, request):
    if request.get("task_class") in ("portable_export","handoff_export","baseline_export","project_files_replacement_bundle"):
        return _mb_full_bundle_export_eval(root, request)
    if _MB_ORIGINAL_EVALUATE is None:
        return {"decision":"DENY","errors":["original_evaluate_missing"]}
    return _MB_ORIGINAL_EVALUATE(root, request)


# PYTHON_RESILIENT_EXECUTION_GATE_WRAPPER_v1
try:
    _MB_PRE_PY_RESILIENCE_EVALUATE = evaluate
except NameError:
    _MB_PRE_PY_RESILIENCE_EVALUATE = None

def _mb_python_resilience_eval(root, request):
    from pathlib import Path
    import importlib.util
    validator = Path(root) / 'runtime' / 'governance' / 'python_resilient_execution_gate_v1.py'
    if not validator.exists():
        return {'decision':'DENY','errors':['python_resilient_execution_gate_validator_missing']}
    spec=importlib.util.spec_from_file_location('python_resilient_execution_gate_v1', validator)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_request(request)

def evaluate(root, request):
    if _MB_PRE_PY_RESILIENCE_EVALUATE is None:
        return {'decision':'DENY','errors':['previous_evaluate_missing']}
    base_result=_MB_PRE_PY_RESILIENCE_EVALUATE(root, request)
    if base_result.get('decision') != 'ALLOW':
        return base_result
    # Enforce only for real governed stage execution, not legacy/internal smoke tests unless explicitly opted out.
    if request.get('task_class') in ('governed_execution','stage_execution','artifact_audit','archive_manifest') and request.get('python_resilience_policy_exempt') is not True:
        py_result=_mb_python_resilience_eval(root, request)
        if py_result.get('decision') != 'ALLOW':
            return {'decision':'DENY','errors':['PYTHON_RESILIENT_EXECUTION_POLICY_v1_DENY'] + py_result.get('errors',[]),'base_result':base_result,'policy_result':py_result}
        merged=dict(base_result)
        merged['python_resilience_policy']='ALLOW'
        merged['python_resilience_policy_result']=py_result
        return merged
    return base_result

# PRE_TOOL_EXECUTION_CONTRACT_GATE_WRAPPER_v1
try:
    _MB_PRE_PRETOOL_EVALUATE = evaluate
except NameError:
    _MB_PRE_PRETOOL_EVALUATE = None

def _mb_pretool_contract_eval(root, request):
    from pathlib import Path
    import importlib.util
    validator = Path(root) / "runtime" / "governance" / "pre_tool_execution_contract_gate_v1.py"
    if not validator.exists():
        return {"decision":"DENY","errors":["pre_tool_execution_contract_validator_missing"]}
    spec = importlib.util.spec_from_file_location("pre_tool_execution_contract_gate_v1", validator)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_request(request)

def evaluate(root, request):
    if _MB_PRE_PRETOOL_EVALUATE is None:
        return {"decision":"DENY","errors":["previous_evaluate_missing_before_pretool_gate"]}
    base_result = _MB_PRE_PRETOOL_EVALUATE(root, request)
    if base_result.get("decision") != "ALLOW":
        return base_result
    if request.get("pre_tool_contract_exempt") is True:
        return base_result
    policy_result = _mb_pretool_contract_eval(root, request)
    if policy_result.get("decision") != "ALLOW":
        return {"decision":"DENY","errors":["PRE_TOOL_EXECUTION_CONTRACT_GATE_DENY"] + policy_result.get("errors",[]),"base_result":base_result,"pretool_policy_result":policy_result}
    merged=dict(base_result)
    merged["pre_tool_execution_contract_gate"]="ALLOW"
    merged["pretool_policy_result"]=policy_result
    return merged

# CHAT_GOVERNANCE_KERNEL_GATE_WRAPPER_v1
try:
    _MB_PRE_CHAT_GOVERNANCE_EVALUATE = evaluate
except NameError:
    _MB_PRE_CHAT_GOVERNANCE_EVALUATE = None

def _mb_chat_governance_eval(root, request):
    from pathlib import Path
    import importlib.util
    validator = Path(root) / "runtime" / "governance" / "chat_governance_kernel_v1.py"
    if not validator.exists():
        return {"decision":"DENY","errors":["chat_governance_kernel_validator_missing"]}
    spec = importlib.util.spec_from_file_location("chat_governance_kernel_v1", validator)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate_turn(root, request)

def evaluate(root, request):
    if _MB_PRE_CHAT_GOVERNANCE_EVALUATE is None:
        return {"decision":"DENY","errors":["previous_evaluate_missing_before_chat_governance_gate"]}
    base_result = _MB_PRE_CHAT_GOVERNANCE_EVALUATE(root, request)
    if base_result.get("decision") != "ALLOW":
        return base_result
    if request.get("chat_governance_exempt") is True:
        return base_result
    if request.get("task_class") in ("meta_chat_turn", "chat_governance_kernel", "governed_execution", "stage_execution") or request.get("explicit_meta_task") is True:
        policy_result = _mb_chat_governance_eval(root, request)
        if policy_result.get("decision") != "ALLOW":
            return {"decision":"DENY","errors":["CHAT_GOVERNANCE_KERNEL_GATE_DENY"] + policy_result.get("errors",[]),"base_result":base_result,"chat_governance_policy_result":policy_result}
        merged=dict(base_result)
        merged["chat_governance_kernel_gate"]="ALLOW"
        merged["chat_governance_policy_result"]=policy_result
        return merged
    return base_result

# CHAT_GOVERNANCE_KERNEL_UPSTREAM_ORDER_FIX_v1
# H0B1 correction: MetaBlooms chat governance must execute before legacy downstream gates
# so missing router/SEE/tracker conditions fail closed instead of bypassing or crashing in
# later path-specific validators.
try:
    _MB_DOWNSTREAM_AFTER_CHAT_EVALUATE = evaluate
except NameError:
    _MB_DOWNSTREAM_AFTER_CHAT_EVALUATE = None

def evaluate(root, request):
    is_meta = request.get("task_class") in ("meta_chat_turn", "chat_governance_kernel", "governed_execution", "stage_execution") or request.get("explicit_meta_task") is True
    if is_meta and request.get("chat_governance_exempt") is not True:
        policy_result = _mb_chat_governance_eval(root, request)
        if policy_result.get("decision") != "ALLOW":
            return {"decision":"DENY","errors":["CHAT_GOVERNANCE_KERNEL_GATE_DENY"] + policy_result.get("errors",[]),"chat_governance_policy_result":policy_result}
    if _MB_DOWNSTREAM_AFTER_CHAT_EVALUATE is None:
        return {"decision":"DENY","errors":["downstream_evaluate_missing_after_chat_governance"]}
    downstream = _MB_DOWNSTREAM_AFTER_CHAT_EVALUATE(root, dict(request, chat_governance_exempt=True))
    if downstream.get("decision") != "ALLOW":
        return downstream
    if is_meta:
        merged=dict(downstream)
        merged["chat_governance_kernel_gate"]="ALLOW_UPSTREAM"
        merged["chat_governance_policy_result"]=policy_result
        return merged
    return downstream
