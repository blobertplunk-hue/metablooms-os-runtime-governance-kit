#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class LearningRegistryError(RuntimeError): pass
VALID_DECISIONS = {"PROMOTE","DEMOTE","FORBID","WATCH","NO_CHANGE"}
VALID_METHOD_STATUS = {"promoted","watch","demoted","forbidden","unknown"}
BAD = {"", "tbd", "n/a", "unknown", "none"}

def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def require(cond: bool, code: str) -> None:
    if not cond:
        raise LearningRegistryError(code)

def validate_learning_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = ["schema_version","packet_id","stage","created_at","objective_id","source_monitor_packet_id","learning_events","method_reliability_records","promotion_rules","decay_policy","registry_summary","result_hash"]
    for key in required:
        require(key in packet, f"LEARN_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.persistent_learning_registry_packet.v1", "LEARN_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "PERSISTENT_LEARNING", "LEARN_BAD_STAGE")
    events = packet["learning_events"]; records = packet["method_reliability_records"]; rules = packet["promotion_rules"]
    require(events, "LEARN_NO_EVENTS"); require(records, "LEARN_NO_METHOD_RECORDS"); require(rules, "LEARN_NO_PROMOTION_RULES")
    event_ids = set(); recurring_events = 0
    for i, e in enumerate(events):
        for key in ["event_id","event_type","source_stage","summary","evidence_refs","severity","recurrence_key","action_required","routes_to"]:
            require(key in e, f"LEARN_EVENT_{i}_MISSING_{key.upper()}")
        require(e["event_id"].startswith("LEARN-"), f"LEARN_EVENT_{i}_BAD_ID")
        require(e["event_id"] not in event_ids, f"LEARN_DUPLICATE_EVENT_{e['event_id']}")
        event_ids.add(e["event_id"]); require(e["evidence_refs"], f"LEARN_EVENT_{i}_NO_EVIDENCE")
        if str(e["recurrence_key"]).strip().lower() not in BAD: recurring_events += 1
        if e["action_required"] is True:
            require(e["routes_to"] in {"DEBUGGING_R17","ECL_R18","SEE_MMD_REFRESH","FIR_REEVALUATION_R19","STOP_BLOCKED","METHOD_ROUTER_UPDATE"}, f"LEARN_EVENT_{i}_BAD_ROUTE")
    method_ids = set()
    for i, r in enumerate(records):
        for key in ["method_id","method_name","method_type","attempts","successes","failures","blocked_failures","last_outcome","reliability_score","confidence","status","evidence_refs","recommended_decision"]:
            require(key in r, f"LEARN_METHOD_{i}_MISSING_{key.upper()}")
        require(r["method_id"] not in method_ids, f"LEARN_DUPLICATE_METHOD_{r['method_id']}")
        method_ids.add(r["method_id"])
        attempts = int(r["attempts"]); successes = int(r["successes"]); failures = int(r["failures"])
        require(attempts == successes + failures, f"LEARN_METHOD_{i}_ATTEMPT_MISMATCH")
        require(0 <= float(r["reliability_score"]) <= 1, f"LEARN_METHOD_{i}_BAD_SCORE")
        require(r["status"] in VALID_METHOD_STATUS, f"LEARN_METHOD_{i}_BAD_STATUS")
        require(r["recommended_decision"] in VALID_DECISIONS, f"LEARN_METHOD_{i}_BAD_DECISION")
        require(r["evidence_refs"], f"LEARN_METHOD_{i}_NO_EVIDENCE")
    rule_ids = set()
    for i, rule in enumerate(rules):
        for key in ["rule_id","condition","decision","threshold","minimum_evidence_count","blocking"]:
            require(key in rule, f"LEARN_RULE_{i}_MISSING_{key.upper()}")
        require(rule["decision"] in VALID_DECISIONS, f"LEARN_RULE_{i}_BAD_DECISION")
        require(rule["rule_id"] not in rule_ids, f"LEARN_DUPLICATE_RULE_{rule['rule_id']}")
        rule_ids.add(rule["rule_id"])
    decay = packet["decay_policy"]
    for key in ["policy_id","staleness_window","confidence_decay","refresh_route"]:
        require(key in decay, f"LEARN_DECAY_MISSING_{key.upper()}")
    require(decay["refresh_route"] in {"SEE_MMD_REFRESH","METHOD_ROUTER_UPDATE","STOP_BLOCKED"}, "LEARN_DECAY_BAD_REFRESH_ROUTE")
    summary = packet["registry_summary"]
    require(summary["event_count"] == len(events), "LEARN_SUMMARY_EVENT_COUNT_MISMATCH")
    require(summary["method_count"] == len(records), "LEARN_SUMMARY_METHOD_COUNT_MISMATCH")
    require(summary["recurring_event_count"] == recurring_events, "LEARN_SUMMARY_RECURRING_COUNT_MISMATCH")
    require(packet["result_hash"] == stable_hash(packet), "LEARN_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":packet["result_hash"]}

def make_router_update(packet_id: str, method: dict[str, Any]) -> dict[str, Any]:
    decision = method.get("recommended_decision","NO_CHANGE")
    update = {"schema_version":"mpp.method_router_update.v1","update_id":f"METHOD-UPDATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{method.get('method_id','UNKNOWN')}","created_at":datetime.now(UTC).isoformat(),"source_packet_id":packet_id,"method_id":method.get("method_id","UNKNOWN"),"decision":decision,"reason":f"reliability_score={method.get('reliability_score')} status={method.get('status')}","evidence_refs":method.get("evidence_refs") or ["METHOD_RECORD"],"blocking":decision=="FORBID","result_hash":""}
    update["result_hash"] = stable_hash(update)
    return update

def run_method_reliability_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations, warnings, updates = [], [], []
    try:
        validate_learning_packet(packet)
    except LearningRegistryError as e:
        violations.append(str(e))
    for r in packet.get("method_reliability_records", []):
        score = float(r.get("reliability_score", 0)); decision = r.get("recommended_decision")
        if decision in {"PROMOTE","DEMOTE","FORBID","WATCH"}:
            updates.append(make_router_update(packet.get("packet_id","UNKNOWN"), r))
        if score < 0.50 and decision not in {"FORBID","DEMOTE","WATCH"}:
            violations.append(f"LEARN_LOW_SCORE_WITHOUT_DEMOTION_{r.get('method_id')}")
        if int(r.get("blocked_failures", 0)) > 0 and decision == "PROMOTE":
            violations.append(f"LEARN_BLOCKED_FAILURE_PROMOTED_{r.get('method_id')}")
        if r.get("status") == "forbidden" and decision != "FORBID":
            violations.append(f"LEARN_FORBIDDEN_METHOD_BAD_DECISION_{r.get('method_id')}")
    for e in packet.get("learning_events", []):
        if e.get("action_required") is True and not e.get("routes_to"):
            violations.append(f"LEARN_ACTION_REQUIRED_NO_ROUTE_{e.get('event_id')}")
    if not updates: warnings.append("LEARN_NO_ROUTER_UPDATES_EMITTED")
    result = {"schema_version":"mpp.method_reliability_gate_result.v1","gate_id":f"METHOD-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"METHOD_RELIABILITY_GATE","created_at":datetime.now(UTC).isoformat(),"packet_id":packet.get("packet_id","UNKNOWN"),"verdict":"FAIL" if violations else "PASS","violations":sorted(set(violations)),"warnings":warnings,"routing_updates":updates,"result_hash":""}
    result["result_hash"] = stable_hash(result)
    return result

def write_learning_packet(source_monitor_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.persistent_learning_registry_packet.v1","packet_id":f"LEARN-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"PERSISTENT_LEARNING","created_at":datetime.now(UTC).isoformat(),"objective_id":objective_id,"source_monitor_packet_id":source_monitor_packet_id,
        "learning_events":[
            {"event_id":"LEARN-001","event_type":"successful_method","source_stage":"R20","summary":"In-process validator execution avoided subprocess hook instability for R20 validation.","evidence_refs":["MPP_R20_RECEIPT","R20_TESTS"],"severity":"INFO","recurrence_key":"sandbox_subprocess_hang_avoidance","action_required":True,"routes_to":"METHOD_ROUTER_UPDATE"},
            {"event_id":"LEARN-002","event_type":"artifact_export_success","source_stage":"FULL_EXPORT","summary":"Streaming ZIP overlay produced duplicate-free whole OS export with MPP integrated.","evidence_refs":["FULL_MPP_V3_R0_R20_EXPORT_RECEIPT"],"severity":"INFO","recurrence_key":"stream_zip_overlay_success","action_required":False,"routes_to":"METHOD_ROUTER_UPDATE"}],
        "method_reliability_records":[
            {"method_id":"METHOD-001","method_name":"python_in_process_validator_gate","method_type":"validation","attempts":3,"successes":3,"failures":0,"blocked_failures":0,"last_outcome":"PASS","reliability_score":1.0,"confidence":"medium","status":"promoted","evidence_refs":["R20_FINAL_PASS"],"recommended_decision":"PROMOTE"},
            {"method_id":"METHOD-002","method_name":"subprocess_validation_inside_python_user_visible","method_type":"validation","attempts":2,"successes":0,"failures":2,"blocked_failures":1,"last_outcome":"HANG_OR_INTERRUPTED","reliability_score":0.0,"confidence":"medium","status":"forbidden","evidence_refs":["R20_INTERRUPTED_ATTEMPT"],"recommended_decision":"FORBID"},
            {"method_id":"METHOD-003","method_name":"zip_stream_overlay_full_export","method_type":"export","attempts":1,"successes":1,"failures":0,"blocked_failures":0,"last_outcome":"PASS","reliability_score":1.0,"confidence":"low","status":"watch","evidence_refs":["FULL_EXPORT_PASS"],"recommended_decision":"WATCH"}],
        "promotion_rules":[
            {"rule_id":"RULE-001","condition":"reliability_score >= 0.95 and failures == 0 with evidence","decision":"PROMOTE","threshold":"0.95","minimum_evidence_count":1,"blocking":False},
            {"rule_id":"RULE-002","condition":"blocked_failures > 0 or reliability_score < 0.50","decision":"FORBID","threshold":"0.50","minimum_evidence_count":1,"blocking":True},
            {"rule_id":"RULE-003","condition":"single success but insufficient sample size","decision":"WATCH","threshold":"sample_count < 3","minimum_evidence_count":1,"blocking":False}],
        "decay_policy":{"policy_id":"DECAY-001","staleness_window":"30 days or after tool/runtime behavior changes","confidence_decay":"confidence drops one level when stale without reconfirmation","refresh_route":"SEE_MMD_REFRESH"},
        "registry_summary":{"event_count":2,"method_count":3,"recurring_event_count":2,"promote_count":1,"forbid_count":1,"watch_count":1},
        "result_hash":""}
    packet["result_hash"] = stable_hash(packet)
    validate_learning_packet(packet)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_persistent_learning_method_reliability_gate_v1__L120', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet

def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--validate"); p.add_argument("--gate"); args = p.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8")); print(json.dumps(validate_learning_packet(packet), sort_keys=True)); return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8")); result = run_method_reliability_gate(packet); print(json.dumps(result, sort_keys=True)); return 0 if result["verdict"] == "PASS" else 1
    p.error("provide --validate or --gate")
if __name__ == "__main__":
    raise SystemExit(main())
