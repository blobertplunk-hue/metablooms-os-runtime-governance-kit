#!/usr/bin/env python3
"""MPP v3 R17: Debugging failure-class validator and repair router."""
from __future__ import annotations

import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class DebuggingValidationError(RuntimeError):
    pass

ROUTES = {"IMPLEMENTATION","VERIFICATION","TRACE_ANALYSIS","ANALYSIS_EVALUATION","ECL","FIR_STAGE","MONITOR","STOP_BLOCKED"}
SEVERITIES = {"S1_LOW","S2_MED","S3_HIGH","S4_CRITICAL"}

def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def require(cond: bool, code: str) -> None:
    if not cond:
        raise DebuggingValidationError(code)

def validate_debugging_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = ["schema_version","packet_id","stage","created_at","objective_id","source_analysis_packet_id","failure_classes","root_cause_analysis","repair_routes","action_items","learning_hooks","result_hash"]
    for key in required:
        require(key in packet, f"DEBUG_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.debugging_failure_class_packet.v1", "DEBUG_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "DEBUGGING", "DEBUG_BAD_STAGE")
    fcs = packet["failure_classes"]
    require(fcs, "DEBUG_NO_FAILURE_CLASSES")
    fc_ids = set()
    critical = set()
    for i, fc in enumerate(fcs):
        for key in ["failure_class_id","category","trigger","symptom","severity","evidence_refs","recurrence_risk","owner"]:
            require(key in fc, f"DEBUG_FC_{i}_MISSING_{key.upper()}")
        require(fc["failure_class_id"].startswith("FC-"), f"DEBUG_FC_{i}_BAD_ID")
        require(fc["failure_class_id"] not in fc_ids, f"DEBUG_DUPLICATE_FC_{fc['failure_class_id']}")
        require(fc["evidence_refs"], f"DEBUG_FC_{i}_NO_EVIDENCE")
        fc_ids.add(fc["failure_class_id"])
        if fc["severity"] == "S4_CRITICAL":
            critical.add(fc["failure_class_id"])
    rca_ids = set()
    for i, rca in enumerate(packet["root_cause_analysis"]):
        for key in ["rca_id","failure_class_id","proximate_cause","systemic_cause","five_whys","confidence","preventive_change"]:
            require(key in rca, f"DEBUG_RCA_{i}_MISSING_{key.upper()}")
        require(rca["failure_class_id"] in fc_ids, f"DEBUG_RCA_{i}_UNKNOWN_FC")
        require(len(rca["five_whys"]) >= 3, f"DEBUG_RCA_{i}_TOO_FEW_WHY_STEPS")
        require(rca["preventive_change"], f"DEBUG_RCA_{i}_NO_PREVENTIVE_CHANGE")
        rca_ids.add(rca["failure_class_id"])
    require(fc_ids.issubset(rca_ids), "DEBUG_NOT_ALL_FAILURE_CLASSES_HAVE_RCA")
    route_fc_ids = set()
    for i, route in enumerate(packet["repair_routes"]):
        for key in ["route_id","failure_class_id","route_to","repair_strategy","blocking","max_attempts"]:
            require(key in route, f"DEBUG_ROUTE_{i}_MISSING_{key.upper()}")
        require(route["failure_class_id"] in fc_ids, f"DEBUG_ROUTE_{i}_UNKNOWN_FC")
        require(route["route_to"] in ROUTES, f"DEBUG_ROUTE_{i}_BAD_DESTINATION")
        require(0 <= int(route["max_attempts"]) <= 5, f"DEBUG_ROUTE_{i}_BAD_MAX_ATTEMPTS")
        route_fc_ids.add(route["failure_class_id"])
    require(fc_ids.issubset(route_fc_ids), "DEBUG_NOT_ALL_FAILURE_CLASSES_HAVE_ROUTES")
    for fc_id in critical:
        critical_routes = [r for r in packet["repair_routes"] if r["failure_class_id"] == fc_id]
        require(any(r["blocking"] is True for r in critical_routes), f"DEBUG_CRITICAL_FC_{fc_id}_NO_BLOCKING_ROUTE")
    for i, action in enumerate(packet["action_items"]):
        for key in ["action_id","description","owner","priority","done_definition"]:
            require(key in action, f"DEBUG_ACTION_{i}_MISSING_{key.upper()}")
    require(packet["learning_hooks"], "DEBUG_NO_LEARNING_HOOKS")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "DEBUG_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"failure_class_count":len(fc_ids),"result_hash":expected}

def run_repair_router(packet: dict[str, Any]) -> dict[str, Any]:
    violations, warnings, routes = [], [], []
    try:
        validate_debugging_packet(packet)
    except DebuggingValidationError as e:
        violations.append(str(e))
    fc_by_id = {fc.get("failure_class_id"): fc for fc in packet.get("failure_classes", [])}
    for route in packet.get("repair_routes", []):
        fc = fc_by_id.get(route.get("failure_class_id"), {})
        routed = {
            "route_id": route.get("route_id"),
            "failure_class_id": route.get("failure_class_id"),
            "severity": fc.get("severity"),
            "route_to": route.get("route_to"),
            "repair_strategy": route.get("repair_strategy"),
            "blocking": route.get("blocking"),
            "max_attempts": route.get("max_attempts"),
        }
        routes.append(routed)
        if fc.get("severity") == "S4_CRITICAL" and route.get("route_to") not in {"STOP_BLOCKED","IMPLEMENTATION","VERIFICATION","ECL"}:
            violations.append(f"DEBUG_CRITICAL_ROUTE_UNSAFE_{route.get('route_id')}")
        if route.get("route_to") == "STOP_BLOCKED" and int(route.get("max_attempts", 0)) != 0:
            violations.append(f"DEBUG_STOP_BLOCKED_MUST_HAVE_ZERO_ATTEMPTS_{route.get('route_id')}")
    if not any(r.get("blocking") is True for r in packet.get("repair_routes", [])):
        violations.append("DEBUG_NO_BLOCKING_REPAIR_ROUTE")
    if len(packet.get("action_items", [])) < len(packet.get("failure_classes", [])):
        warnings.append("DEBUG_WARN_FEWER_ACTIONS_THAN_FAILURE_CLASSES")
    verdict = "STOP_BLOCKED" if any(r.get("route_to") == "STOP_BLOCKED" for r in packet.get("repair_routes", []) if r.get("blocking") is True) else ("FAIL" if violations else "PASS")
    result = {
        "schema_version":"mpp.debugging_repair_router_result.v1",
        "gate_id":f"DEBUG-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"DEBUGGING_REPAIR_ROUTER",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict if not violations or verdict == "STOP_BLOCKED" else "FAIL",
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "routes":routes,
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result

def write_debugging_packet(source_analysis_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.debugging_failure_class_packet.v1",
        "packet_id":f"DEBUG-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"DEBUGGING",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_analysis_packet_id":source_analysis_packet_id,
        "failure_classes":[
            {"failure_class_id":"FC-001","category":"reasoning_failure","trigger":"analysis gate reports repair_required","symptom":"claim lacks sufficient grounding or evidence binding","severity":"S3_HIGH","evidence_refs":["R16_ANALYSIS_REASONING_GATE"],"recurrence_risk":"medium","owner":"MPP_R17"}
        ],
        "root_cause_analysis":[
            {"rca_id":"RCA-001","failure_class_id":"FC-001","proximate_cause":"claim evaluation failed threshold","systemic_cause":"prior stage did not bind enough evidence before reasoning evaluation","five_whys":["Why fail? score below threshold","Why score low? evidence missing or weak","Why evidence weak? research/normalization did not supply binding"],"confidence":"high","preventive_change":"route to smallest repair stage and add regression fixture"}
        ],
        "repair_routes":[
            {"route_id":"ROUTE-001","failure_class_id":"FC-001","route_to":"ANALYSIS_EVALUATION","repair_strategy":"rerun_gate","blocking":True,"max_attempts":1}
        ],
        "action_items":[
            {"action_id":"ACT-001","description":"Add regression fixture for the failed reasoning dimension.","owner":"MPP_R17","priority":"P1","done_definition":"fixture fails before repair and passes after repair"}
        ],
        "learning_hooks":["persist failure class and route in receipt","promote recurring failure to ECL if it repeats"],
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_debugging_packet(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_debugging_failure_class_repair_router_v1_py_L141', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_debugging_packet(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_repair_router(packet)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] in {"PASS","STOP_BLOCKED"} and not result["violations"] else 1
    parser.error("provide --validate or --gate")

if __name__ == "__main__":
    raise SystemExit(main())
