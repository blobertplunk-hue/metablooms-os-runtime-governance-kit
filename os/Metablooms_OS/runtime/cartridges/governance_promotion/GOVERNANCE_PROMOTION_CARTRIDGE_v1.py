#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, hashlib, datetime, re
from typing import Dict, Any

CARTRIDGE_ID = "GOVERNANCE_PROMOTION_CARTRIDGE_v1"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def slugify(text: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", text.strip()).strip("_").upper()
    return s[:80] or "GOVERNANCE_RULE"

def infer_gate(request: Dict[str, Any]) -> str:
    target = (request.get("target_gate") or "").strip()
    if target:
        return target
    text = (request.get("governance_text") or "").lower()
    if "tracker" in text:
        return "TRACKER_RELEASE_GATE"
    if "research" in text or "web.run" in text or "see" in text or "ce" in text:
        return "RESEARCH_SEE_CE_GATE"
    if "write" in text or "rollback" in text or "runtime" in text:
        return "RUNTIME_WRITE_ROLLBACK_GATE"
    return "CUSTOM_GOVERNANCE_GATE"

def build_invariant(request: Dict[str, Any]) -> Dict[str, Any]:
    rule_id = request.get("id") or slugify(request.get("governance_text", "governance_rule"))
    gate = infer_gate(request)
    return {
        "id": rule_id,
        "status": "proposed",
        "gate": gate,
        "description": request.get("governance_text", ""),
        "failure_action": request.get("failure_action", "DENY_STAGE_EXECUTION"),
        "activation_requirements": [
            "positive test must ALLOW",
            "negative test must DENY",
            "promotion receipt must be written",
            "active status only after test proof"
        ],
        "source_request": request
    }

def build_tests(invariant: Dict[str, Any], work_dir: Path) -> Dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    gate = invariant["gate"]
    valid_tracker = work_dir / "test_valid_tracker.html"
    invalid_tracker = work_dir / "test_invalid_tracker.html"
    valid_tracker.write_text("""<!doctype html><html><body>
<h2>Workflow Timeline</h2>
<h2>Next Valid Stage</h2><div class="code">NEXT</div></section>
<h2>Evidence Ledger</h2>
<h2>Permanent OS / Governance Improvements Ledger</h2>
</body></html>""", encoding="utf-8")
    invalid_tracker.write_text("<html><body>tiny</body></html>", encoding="utf-8")
    rb = work_dir / "rollback.json"
    snap = work_dir / "snapshot.json"
    write_json(rb, {"ok": True})
    write_json(snap, {"ok": True})
    base = {"baseline_path": str(valid_tracker), "live_state_path": str(valid_tracker)}
    if gate == "TRACKER_RELEASE_GATE":
        positive = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "s", "CE_decision": "d", "will_modify_runtime": False}
        negative = {**base, "tracker_path": str(invalid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "s", "CE_decision": "d", "will_modify_runtime": False}
    elif gate == "RESEARCH_SEE_CE_GATE":
        positive = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "s", "CE_decision": "d", "will_modify_runtime": False}
        negative = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "will_modify_runtime": False}
    elif gate == "RUNTIME_WRITE_ROLLBACK_GATE":
        positive = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "s", "CE_decision": "d", "will_modify_runtime": True, "rollback_manifest_path": str(rb), "pre_write_snapshot_path": str(snap), "registry_patch": False}
        negative = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "s", "CE_decision": "d", "will_modify_runtime": True}
    else:
        # Include valid tracker path so generic IAE gates do not fail for accidental missing tracker_path.
        positive = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "s", "CE_decision": "d", "will_modify_runtime": False, "custom_governance_ack": True}
        negative = {**base, "tracker_path": str(valid_tracker), "task_class": "governed_execution", "will_modify_runtime": False}
    return {"positive": positive, "negative": negative}

def promote(request: Dict[str, Any], root: Path, out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    invariant = build_invariant(request)
    tests = build_tests(invariant, out_dir / "tests")
    proposal_path = out_dir / "proposed_invariant.json"
    write_json(proposal_path, invariant)
    write_json(out_dir / "gate_tests.json", tests)
    engine_path = root / "runtime" / "governance" / "invariant_activation_engine_v1.py"
    if not engine_path.exists():
        result = {"status": "FAIL_ENGINE_MISSING", "engine_path": str(engine_path)}
        write_json(out_dir / "promotion_result.json", result)
        return result
    ns: Dict[str, Any] = {}
    exec(engine_path.read_text(encoding="utf-8"), ns)
    positive_result = ns["evaluate"](root, tests["positive"])
    negative_result = ns["evaluate"](root, tests["negative"])
    can_activate = positive_result.get("decision") == "ALLOW" and negative_result.get("decision") == "DENY" and invariant["gate"] != "CUSTOM_GOVERNANCE_GATE"
    activated_path = None
    if can_activate:
        invariant["status"] = "active"
        inv_dir = root / "governance" / "invariants"
        inv_dir.mkdir(parents=True, exist_ok=True)
        activated_path = inv_dir / f"{invariant['id']}.json"
        write_json(activated_path, invariant)
    result = {
        "cartridge_id": CARTRIDGE_ID,
        "timestamp_utc": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "status": "ACTIVE" if can_activate else "PROPOSED_NOT_ACTIVE",
        "invariant": invariant,
        "proposal_path": str(proposal_path),
        "activated_path": str(activated_path) if activated_path else None,
        "positive_result": positive_result,
        "negative_result": negative_result,
        "activation_allowed": can_activate,
        "reason": "positive ALLOW and negative DENY" if can_activate else "activation requires mapped gate and positive/negative proof"
    }
    write_json(out_dir / "promotion_result.json", result)
    return result


# PYTHON_RESILIENT_EXECUTION_GATE_GPC_TESTS_v1
try:
    _MB_ORIGINAL_BUILD_TESTS = build_tests
except NameError:
    _MB_ORIGINAL_BUILD_TESTS = None

def build_tests(invariant, work_dir):
    from pathlib import Path
    gate = invariant.get("gate")
    work_dir = Path(work_dir)
    if gate != "PYTHON_RESILIENT_EXECUTION_GATE":
        return _MB_ORIGINAL_BUILD_TESTS(invariant, work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    valid_tracker = work_dir / "test_valid_tracker.html"
    invalid_tracker = work_dir / "test_invalid_tracker.html"
    valid_tracker.write_text("""<!doctype html><html><body>
<h2>Workflow Timeline</h2><p>x</p>
<h2>Next Valid Stage</h2><div class="code">NEXT</div></section>
<h2>Evidence Ledger</h2><p>x</p>
<h2>Permanent OS / Governance Improvements Ledger</h2><p>x</p>
</body></html>""", encoding="utf-8")
    invalid_tracker.write_text("<html><body>bad</body></html>", encoding="utf-8")
    probe = work_dir / "tool_probe.txt"
    probe.write_text("bash: FOUND\nfind: FOUND\nsha256sum: FOUND\nzip: FOUND\nunzip: FOUND\npython3 -S: PASS\n", encoding="utf-8")
    rb = work_dir / "rollback.json"; snap = work_dir / "snapshot.json"
    write_json(rb, {"ok": True}); write_json(snap, {"ok": True})
    base = {"tracker_path": str(valid_tracker), "task_class": "governed_execution", "web_sources": ["source"], "SEE_summary": "summary", "CE_decision": "decision", "will_modify_runtime": False}
    positive = {**base, "tool_probe_path": str(probe), "execution_lane": "shell_coreutils", "fallback_lanes": ["jq_node", "python3_dash_S_stdlib"], "failure_lane_switch_required": True, "archive_or_filesystem_work": True, "normal_python_used": False}
    negative = {**base}
    return {"positive": positive, "negative": negative}
