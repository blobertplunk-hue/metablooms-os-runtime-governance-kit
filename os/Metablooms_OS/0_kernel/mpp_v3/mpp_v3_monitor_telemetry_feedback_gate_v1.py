#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class MonitorValidationError(RuntimeError): pass
VALID_ROUTES = {"CONTINUE_NORMAL","DEBUGGING_R17","ECL_R18","SEE_MMD_REFRESH","FIR_REEVALUATION_R19","STOP_BLOCKED"}
FAIL_ROUTES = VALID_ROUTES - {"CONTINUE_NORMAL"}

def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def require(cond: bool, code: str) -> None:
    if not cond:
        raise MonitorValidationError(code)

def route_target(route: str) -> str:
    return {"CONTINUE_NORMAL":"R21_OR_R23","DEBUGGING_R17":"MPP_R17_DEBUGGING_FAILURE_CLASS_SCHEMA_AND_REPAIR_ROUTER","ECL_R18":"MPP_R18_ECL_ENFORCED_CORRECTION_LOOP_SCHEMA_AND_REGRESSION_GATE","SEE_MMD_REFRESH":"MPP_R1_TO_R4_RESEARCH_REFRESH","FIR_REEVALUATION_R19":"MPP_R19_FIR_FITNESS_INTEGRATION_SCHEMA_AND_GATE","STOP_BLOCKED":"STOP_BLOCKED"}[route]

def validate_monitor_packet(packet: dict[str, Any]) -> dict[str, Any]:
    for key in ["schema_version","packet_id","stage","created_at","objective_id","source_fir_packet_id","telemetry_context","metric_definitions","telemetry_events","drift_indicators","silent_failure_checks","feedback_routes","monitor_summary","result_hash"]:
        require(key in packet, f"MONITOR_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.monitor_telemetry_packet.v1", "MONITOR_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "MONITOR", "MONITOR_BAD_STAGE")
    require(packet["telemetry_context"].get("artifact_persistence") is True, "MONITOR_TELEMETRY_ARTIFACT_PERSISTENCE_REQUIRED")
    require(len(packet["metric_definitions"]) >= 5, "MONITOR_TOO_FEW_METRIC_DEFINITIONS")
    metric_names = set()
    for i, m in enumerate(packet["metric_definitions"]):
        for key in ["metric_id","name","unit","aggregation","measurement_window","threshold","owner","route_on_breach"]:
            require(key in m, f"MONITOR_METRIC_{i}_MISSING_{key.upper()}")
            require(str(m[key]).strip().lower() not in {"", "tbd", "n/a", "unknown"}, f"MONITOR_METRIC_{i}_BAD_{key.upper()}")
        require(m["route_on_breach"] in FAIL_ROUTES, f"MONITOR_METRIC_{i}_BAD_ROUTE_ON_BREACH")
        metric_names.add(m["name"])
    fail_events = warn_events = unrouteable = 0
    for i, e in enumerate(packet["telemetry_events"]):
        for key in ["event_id","event_type","stage_ref","artifact_refs","gate_refs","severity","status","route"]:
            require(key in e, f"MONITOR_EVENT_{i}_MISSING_{key.upper()}")
        require(e["artifact_refs"] or e["gate_refs"], f"MONITOR_EVENT_{i}_UNBOUND_TO_ARTIFACT_OR_GATE")
        if e["status"] in {"FAIL","WARN"} and e["route"] == "CONTINUE_NORMAL":
            unrouteable += 1
        if e["status"] == "FAIL": fail_events += 1
        if e["status"] == "WARN": warn_events += 1
    drift_breach = 0
    for i, d in enumerate(packet["drift_indicators"]):
        for key in ["drift_id","metric_name","observed","threshold","breached","route"]:
            require(key in d, f"MONITOR_DRIFT_{i}_MISSING_{key.upper()}")
        require(d["metric_name"] in metric_names, f"MONITOR_DRIFT_{i}_UNKNOWN_METRIC")
        if d["breached"] is True:
            drift_breach += 1
            require(d["route"] != "CONTINUE_NORMAL", f"MONITOR_DRIFT_{i}_BREACH_CONTINUE_FORBIDDEN")
    silent_failures = 0
    for i, s in enumerate(packet["silent_failure_checks"]):
        for key in ["check_id","description","passed","route_on_fail","evidence_refs"]:
            require(key in s, f"MONITOR_SILENT_{i}_MISSING_{key.upper()}")
        require(s["evidence_refs"], f"MONITOR_SILENT_{i}_NO_EVIDENCE")
        if s["passed"] is False:
            silent_failures += 1
            require(s["route_on_fail"] in FAIL_ROUTES, f"MONITOR_SILENT_{i}_BAD_ROUTE")
    routes = packet["feedback_routes"]
    require("STOP_BLOCKED" in {r.get("route") for r in routes}, "MONITOR_STOP_BLOCKED_ROUTE_REQUIRED")
    for i, r in enumerate(routes):
        for key in ["route_id","route","condition","target_stage","blocking","evidence_required"]:
            require(key in r, f"MONITOR_ROUTE_{i}_MISSING_{key.upper()}")
        require(r["route"] in VALID_ROUTES, f"MONITOR_ROUTE_{i}_BAD_ROUTE")
        require(r["evidence_required"], f"MONITOR_ROUTE_{i}_NO_EVIDENCE_REQUIRED")
    summary = packet["monitor_summary"]
    require(summary["event_count"] == len(packet["telemetry_events"]), "MONITOR_SUMMARY_EVENT_COUNT_MISMATCH")
    require(summary["fail_event_count"] == fail_events, "MONITOR_SUMMARY_FAIL_COUNT_MISMATCH")
    require(summary["warn_event_count"] == warn_events, "MONITOR_SUMMARY_WARN_COUNT_MISMATCH")
    require(summary["drift_breach_count"] == drift_breach, "MONITOR_SUMMARY_DRIFT_COUNT_MISMATCH")
    require(summary["silent_failure_count"] == silent_failures, "MONITOR_SUMMARY_SILENT_COUNT_MISMATCH")
    require(summary["unrouteable_signal_count"] == unrouteable, "MONITOR_SUMMARY_UNROUTEABLE_COUNT_MISMATCH")
    require(summary["artifact_persisted"] is True, "MONITOR_SUMMARY_ARTIFACT_NOT_PERSISTED")
    if fail_events or silent_failures or unrouteable:
        require(summary["decision"] != "CONTINUE_NORMAL", "MONITOR_DECISION_MUST_NOT_CONTINUE_WITH_FAILURE")
    if drift_breach:
        require(summary["decision"] in {"FIR_REEVALUATION_R19","ECL_R18","SEE_MMD_REFRESH","STOP_BLOCKED"}, "MONITOR_BAD_DRIFT_DECISION")
    require(packet["result_hash"] == stable_hash(packet), "MONITOR_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":packet["result_hash"]}

def make_decision(packet_id: str, route: str, trigger: str, severity: str, evidence_refs: list[str], blocking: bool) -> dict[str, Any]:
    d = {"schema_version":"mpp.monitor_routing_decision.v1","decision_id":f"MON-ROUTE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{route}","created_at":datetime.now(UTC).isoformat(),"source_packet_id":packet_id,"route_to":route,"trigger":trigger,"severity":severity,"evidence_refs":evidence_refs,"next_stage":route_target(route),"blocking":blocking,"result_hash":""}
    d["result_hash"] = stable_hash(d)
    return d

def run_feedback_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations, warnings, decisions = [], [], []
    try:
        validate_monitor_packet(packet)
    except MonitorValidationError as e:
        violations.append(str(e))
    for e in packet.get("telemetry_events", []):
        if e.get("status") in {"FAIL","WARN"}:
            route = e.get("route", "STOP_BLOCKED")
            if route == "CONTINUE_NORMAL": route = "STOP_BLOCKED"
            decisions.append(make_decision(packet.get("packet_id","UNKNOWN"), route, f"event:{e.get('event_id')}", e.get("severity","FAIL"), e.get("artifact_refs") or e.get("gate_refs") or ["MONITOR_EVENT"], route == "STOP_BLOCKED"))
    for d in packet.get("drift_indicators", []):
        if d.get("breached") is True:
            decisions.append(make_decision(packet.get("packet_id","UNKNOWN"), d.get("route","STOP_BLOCKED"), f"drift:{d.get('drift_id')}", "WARN", [d.get("metric_name","DRIFT")], d.get("route") == "STOP_BLOCKED"))
    for s in packet.get("silent_failure_checks", []):
        if s.get("passed") is False:
            decisions.append(make_decision(packet.get("packet_id","UNKNOWN"), s.get("route_on_fail","STOP_BLOCKED"), f"silent:{s.get('check_id')}", "CRITICAL", s.get("evidence_refs") or ["SILENT_FAILURE"], True))
    summary = packet.get("monitor_summary", {})
    if summary.get("artifact_persisted") is not True:
        violations.append("MONITOR_GATE_TELEMETRY_NOT_PERSISTED")
        decisions.append(make_decision(packet.get("packet_id","UNKNOWN"), "STOP_BLOCKED", "telemetry_not_persisted", "CRITICAL", ["MONITOR_SUMMARY"], True))
    if summary.get("unrouteable_signal_count", 0) > 0:
        violations.append("MONITOR_GATE_UNROUTEABLE_SIGNALS_PRESENT")
    if summary.get("silent_failure_count", 0) > 0:
        violations.append("MONITOR_GATE_SILENT_FAILURE_PRESENT")
    if summary.get("fail_event_count", 0) > 0:
        violations.append("MONITOR_GATE_FAIL_EVENTS_PRESENT")
    if not decisions:
        decisions.append(make_decision(packet.get("packet_id","UNKNOWN"), "CONTINUE_NORMAL", "all_monitor_checks_passed", "INFO", ["MONITOR_PACKET"], False))
    verdict = "FAIL" if violations and any(d["route_to"] == "STOP_BLOCKED" for d in decisions) else ("NEEDS_REPAIR" if violations else "PASS")
    result = {"schema_version":"mpp.monitor_feedback_gate_result.v1","gate_id":f"MONITOR-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"MONITOR_FEEDBACK_GATE","created_at":datetime.now(UTC).isoformat(),"packet_id":packet.get("packet_id","UNKNOWN"),"verdict":verdict,"violations":sorted(set(violations)),"warnings":warnings,"routing_decisions":decisions,"result_hash":""}
    result["result_hash"] = stable_hash(result)
    return result

def base_packet(source_fir_packet_id: str, objective_id: str) -> dict[str, Any]:
    return {
        "schema_version":"mpp.monitor_telemetry_packet.v1","packet_id":f"MONITOR-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"MONITOR","created_at":datetime.now(UTC).isoformat(),"objective_id":objective_id,"source_fir_packet_id":source_fir_packet_id,
        "telemetry_context":{"run_id":f"RUN-{objective_id}","trace_id":hashlib.sha256(objective_id.encode()).hexdigest()[:32],"mode":"stage_monitor","artifact_persistence":True},
        "metric_definitions":[
            {"metric_id":"MET-001","name":"artifact_integrity_pass_rate","unit":"ratio","aggregation":"mean","measurement_window":"per stage","threshold":"1.0","owner":"MPP_R20","route_on_breach":"STOP_BLOCKED"},
            {"metric_id":"MET-002","name":"gate_pass_rate","unit":"ratio","aggregation":"mean","measurement_window":"per stage","threshold":"1.0","owner":"MPP_R20","route_on_breach":"DEBUGGING_R17"},
            {"metric_id":"MET-003","name":"drift_breach_count","unit":"count","aggregation":"sum","measurement_window":"per monitor packet","threshold":"0","owner":"MPP_R20","route_on_breach":"FIR_REEVALUATION_R19"},
            {"metric_id":"MET-004","name":"silent_failure_count","unit":"count","aggregation":"sum","measurement_window":"per monitor packet","threshold":"0","owner":"MPP_R20","route_on_breach":"STOP_BLOCKED"},
            {"metric_id":"MET-005","name":"feedback_route_coverage","unit":"ratio","aggregation":"mean","measurement_window":"per monitor packet","threshold":"1.0","owner":"MPP_R20","route_on_breach":"STOP_BLOCKED"},
            {"metric_id":"MET-006","name":"rework_rate","unit":"ratio","aggregation":"mean","measurement_window":"per pipeline","threshold":"<=0.20","owner":"MPP_R20","route_on_breach":"ECL_R18"}],
        "telemetry_events":[
            {"event_id":"EVT-001","event_type":"artifact_integrity","stage_ref":"R19","artifact_refs":["MPP_R19_FIR_FITNESS_INTEGRATION_SCHEMA_AND_GATE_20260501T024900Z.zip"],"gate_refs":["FIR_FITNESS_GATE"],"severity":"INFO","status":"PASS","route":"CONTINUE_NORMAL"},
            {"event_id":"EVT-002","event_type":"gate_outcome","stage_ref":"R20","artifact_refs":["MONITOR_TELEMETRY_PACKET_SCHEMA_v1.json"],"gate_refs":["MONITOR_FEEDBACK_GATE"],"severity":"INFO","status":"PASS","route":"CONTINUE_NORMAL"}],
        "drift_indicators":[{"drift_id":"DRIFT-001","metric_name":"drift_breach_count","observed":"0","threshold":"0","breached":False,"route":"CONTINUE_NORMAL"}],
        "silent_failure_checks":[{"check_id":"SILENT-001","description":"PASS result must have persisted telemetry artifact and evidence-bound events.","passed":True,"route_on_fail":"STOP_BLOCKED","evidence_refs":["valid_monitor_telemetry_packet_v1.json"]},{"check_id":"SILENT-002","description":"Every failure/warning signal must have a valid feedback route.","passed":True,"route_on_fail":"STOP_BLOCKED","evidence_refs":["feedback_routes"]}],
        "feedback_routes":[
            {"route_id":"ROUTE-001","route":"CONTINUE_NORMAL","condition":"all checks pass","target_stage":"R21_OR_R23","blocking":False,"evidence_required":["MONITOR_GATE_PASS"]},
            {"route_id":"ROUTE-002","route":"DEBUGGING_R17","condition":"new failure class or failed gate","target_stage":"MPP_R17","blocking":False,"evidence_required":["failed_event"]},
            {"route_id":"ROUTE-003","route":"ECL_R18","condition":"recurring failure or regression recurrence","target_stage":"MPP_R18","blocking":False,"evidence_required":["recurrence_evidence"]},
            {"route_id":"ROUTE-004","route":"SEE_MMD_REFRESH","condition":"stale or insufficient research basis","target_stage":"MPP_R1_TO_R4","blocking":False,"evidence_required":["research_staleness"]},
            {"route_id":"ROUTE-005","route":"FIR_REEVALUATION_R19","condition":"fitness drift below threshold","target_stage":"MPP_R19","blocking":False,"evidence_required":["drift_indicator"]},
            {"route_id":"ROUTE-006","route":"STOP_BLOCKED","condition":"silent failure, unrouteable signal, missing artifact, or sidecar mismatch","target_stage":"STOP_BLOCKED","blocking":True,"evidence_required":["blocking_violation"]}],
        "monitor_summary":{"event_count":2,"fail_event_count":0,"warn_event_count":0,"drift_breach_count":0,"silent_failure_count":0,"unrouteable_signal_count":0,"artifact_persisted":True,"decision":"CONTINUE_NORMAL"},
        "result_hash":""}
def write_monitor_packet(source_fir_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = base_packet(source_fir_packet_id, objective_id); packet["result_hash"] = stable_hash(packet); validate_monitor_packet(packet); _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_monitor_telemetry_feedback_gate_v1_py_L150', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000); return packet
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--validate"); parser.add_argument("--gate"); args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8")); print(json.dumps(validate_monitor_packet(packet), sort_keys=True)); return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8")); result = run_feedback_gate(packet); print(json.dumps(result, sort_keys=True)); return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")
if __name__ == "__main__":
    raise SystemExit(main())
