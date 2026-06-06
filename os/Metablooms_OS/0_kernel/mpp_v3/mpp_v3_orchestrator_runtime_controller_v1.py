#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class OrchestratorError(RuntimeError): pass
DECISIONS={"ADVANCE","RETRY","REPAIR_ROUTE","STOP_BLOCKED","EXPORT_PROMOTION"}
REPAIR_ROUTES={"DEBUGGING_R17","ECL_R18","SEE_MMD_REFRESH","FIR_REEVALUATION_R19","STOP_BLOCKED"}

def stable_hash(payload: dict[str, Any]) -> str:
    clone=json.loads(json.dumps(payload,sort_keys=True))
    clone["result_hash"]=""
    return hashlib.sha256(json.dumps(clone,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def require(cond: bool, code: str) -> None:
    if not cond: raise OrchestratorError(code)

def validate_orchestrator_plan(packet: dict[str, Any]) -> dict[str, Any]:
    required=["schema_version","packet_id","stage","created_at","objective_id","source_learning_packet_id","stage_graph","runtime_state","transition_rules","retry_policy","exit_handlers","reconciliation_policy","controller_summary","result_hash"]
    for key in required: require(key in packet,f"ORCH_MISSING_{key.upper()}")
    require(packet["schema_version"]=="mpp.orchestrator_runtime_plan.v1","ORCH_BAD_SCHEMA_VERSION")
    require(packet["stage"]=="ORCHESTRATOR","ORCH_BAD_STAGE")
    stages=packet["stage_graph"]; require(stages,"ORCH_NO_STAGE_GRAPH")
    ids=[]; orders=[]
    for i,s in enumerate(stages):
        for key in ["stage_id","order","status","required_inputs","required_gates","handoff_path","receipt_path","retryable","repair_routes"]:
            require(key in s,f"ORCH_STAGE_{i}_MISSING_{key.upper()}")
        ids.append(s["stage_id"]); orders.append(s["order"])
        require(isinstance(s["order"],int),f"ORCH_STAGE_{i}_ORDER_NOT_INT")
        require(s["required_inputs"],f"ORCH_STAGE_{i}_NO_REQUIRED_INPUTS")
        require(s["required_gates"],f"ORCH_STAGE_{i}_NO_REQUIRED_GATES")
        for route in s["repair_routes"]:
            require(route in REPAIR_ROUTES,f"ORCH_STAGE_{i}_BAD_REPAIR_ROUTE_{route}")
    require(len(ids)==len(set(ids)),"ORCH_DUPLICATE_STAGE_IDS")
    require(orders==sorted(orders),"ORCH_STAGE_GRAPH_NOT_SORTED")
    state=packet["runtime_state"]
    for key in ["current_stage","last_completed_stage","desired_state","actual_state","blocked","attempt_count"]:
        require(key in state,f"ORCH_RUNTIME_STATE_MISSING_{key.upper()}")
    require(state["desired_state"] in {"READY","RUNNING","COMPLETE","BLOCKED","EXPORT_READY"},"ORCH_BAD_DESIRED_STATE")
    require(state["actual_state"] in {"READY","RUNNING","COMPLETE","BLOCKED","EXPORT_READY"},"ORCH_BAD_ACTUAL_STATE")
    for i,rule in enumerate(packet["transition_rules"]):
        for key in ["rule_id","from_state","condition","decision","to_stage","evidence_required"]:
            require(key in rule,f"ORCH_RULE_{i}_MISSING_{key.upper()}")
        require(rule["decision"] in DECISIONS,f"ORCH_RULE_{i}_BAD_DECISION")
        require(rule["evidence_required"],f"ORCH_RULE_{i}_NO_EVIDENCE")
    retry=packet["retry_policy"]
    for key in ["max_attempts","retryable_failures","non_retryable_failures","backoff_strategy","failure_budget"]:
        require(key in retry,f"ORCH_RETRY_MISSING_{key.upper()}")
    require(0<=int(retry["max_attempts"])<=3,"ORCH_RETRY_MAX_ATTEMPTS_OUT_OF_BOUNDS")
    require(retry["non_retryable_failures"],"ORCH_NO_NON_RETRYABLE_FAILURES")
    require(packet["exit_handlers"],"ORCH_NO_EXIT_HANDLERS")
    for i,h in enumerate(packet["exit_handlers"]):
        for key in ["handler_id","condition","action","always_runs","evidence_output"]:
            require(key in h,f"ORCH_EXIT_{i}_MISSING_{key.upper()}")
        require(h["always_runs"] is True,f"ORCH_EXIT_{i}_MUST_ALWAYS_RUN")
        require(h["evidence_output"],f"ORCH_EXIT_{i}_NO_EVIDENCE_OUTPUT")
    rec=packet["reconciliation_policy"]
    for key in ["policy_id","compare","repair_on_drift","stop_on_unrepairable","writes_receipt"]:
        require(key in rec,f"ORCH_RECONCILE_MISSING_{key.upper()}")
    require(rec["repair_on_drift"] is True,"ORCH_RECONCILE_MUST_REPAIR_DRIFT")
    require(rec["stop_on_unrepairable"] is True,"ORCH_RECONCILE_MUST_STOP_UNREPAIRABLE")
    require(rec["writes_receipt"] is True,"ORCH_RECONCILE_MUST_WRITE_RECEIPT")
    summary=packet["controller_summary"]
    require(summary["stage_count"]==len(stages),"ORCH_SUMMARY_STAGE_COUNT_MISMATCH")
    require(summary["blocked"]==state["blocked"],"ORCH_SUMMARY_BLOCKED_MISMATCH")
    require(packet["result_hash"]==stable_hash(packet),"ORCH_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":packet["result_hash"]}

def decide_next(packet: dict[str, Any]) -> dict[str, Any]:
    state=packet.get("runtime_state",{})
    decision="EXPORT_PROMOTION"; to_stage="MPP_R23_EXPORT_PROMOTION_GATE"; reason="R22 completed; export promotion is next"; blocking=False
    if state.get("blocked") is True:
        decision="STOP_BLOCKED"; to_stage="STOP_BLOCKED"; reason="runtime state is blocked"; blocking=True
    elif int(state.get("attempt_count",0)) > int(packet.get("retry_policy",{}).get("max_attempts",0)):
        decision="STOP_BLOCKED"; to_stage="STOP_BLOCKED"; reason="attempt budget exceeded"; blocking=True
    d={"schema_version":"mpp.orchestrator_transition_decision.v1","decision_id":f"ORCH-DECISION-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","created_at":datetime.now(UTC).isoformat(),"source_packet_id":packet.get("packet_id","UNKNOWN"),"from_stage":state.get("current_stage","UNKNOWN"),"to_stage":to_stage,"decision":decision,"reason":reason,"evidence_refs":["ORCHESTRATOR_RUNTIME_PLAN","R21_HANDOFF"],"blocking":blocking,"result_hash":""}
    d["result_hash"]=stable_hash(d)
    return d

def run_controller_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations=[]; warnings=[]
    try: validate_orchestrator_plan(packet)
    except OrchestratorError as e: violations.append(str(e))
    decision=decide_next(packet)
    if packet.get("runtime_state",{}).get("desired_state") != packet.get("runtime_state",{}).get("actual_state"):
        violations.append("ORCH_DESIRED_ACTUAL_DRIFT")
        decision={**decision,"decision":"REPAIR_ROUTE","to_stage":"MPP_R17_DEBUGGING_FAILURE_CLASS_SCHEMA_AND_REPAIR_ROUTER","reason":"desired/actual state drift detected","blocking":False}
        decision["result_hash"]=stable_hash(decision)
    if not packet.get("exit_handlers"): violations.append("ORCH_NO_EXIT_HANDLERS")
    verdict="STOP_BLOCKED" if decision["decision"]=="STOP_BLOCKED" else ("FAIL" if violations else "PASS")
    result={"schema_version":"mpp.orchestrator_controller_gate_result.v1","gate_id":f"ORCH-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"ORCHESTRATOR_CONTROLLER_GATE","created_at":datetime.now(UTC).isoformat(),"packet_id":packet.get("packet_id","UNKNOWN"),"verdict":verdict,"violations":sorted(set(violations)),"warnings":warnings,"next_action":decision,"result_hash":""}
    result["result_hash"]=stable_hash(result)
    return result

def write_orchestrator_plan(source_learning_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    core=["MPP_R20_MONITOR_TELEMETRY_SCHEMA_AND_FEEDBACK_GATE","MPP_R21_PERSISTENT_LEARNING_REGISTRY_AND_METHOD_RELIABILITY_GATE","MPP_R22_ORCHESTRATOR_RUNTIME_CONTROLLER","MPP_R23_EXPORT_PROMOTION_GATE"]
    graph=[]
    for idx,sid in enumerate(core,start=20):
        graph.append({"stage_id":sid,"order":idx,"status":"COMPLETE" if idx<22 else ("RUNNING" if idx==22 else "READY"),"required_inputs":[f"{sid}_HANDOFF_LATEST.json"],"required_gates":[f"{sid}_GATE"],"handoff_path":f"runtime/handoffs/mpp_v3/{sid}_HANDOFF_LATEST.json","receipt_path":f"runtime/receipts/mpp_v3/{sid}_RECEIPT_LATEST.json","retryable":idx<23,"repair_routes":["DEBUGGING_R17","ECL_R18","STOP_BLOCKED"]})
    packet={"schema_version":"mpp.orchestrator_runtime_plan.v1","packet_id":f"ORCH-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"ORCHESTRATOR","created_at":datetime.now(UTC).isoformat(),"objective_id":objective_id,"source_learning_packet_id":source_learning_packet_id,"stage_graph":graph,"runtime_state":{"current_stage":"MPP_R22_ORCHESTRATOR_RUNTIME_CONTROLLER","last_completed_stage":"MPP_R21_PERSISTENT_LEARNING_REGISTRY_AND_METHOD_RELIABILITY_GATE","desired_state":"RUNNING","actual_state":"RUNNING","blocked":False,"attempt_count":1},"transition_rules":[{"rule_id":"ORCH-RULE-001","from_state":"RUNNING","condition":"current stage PASS and handoff READY","decision":"ADVANCE","to_stage":"next ordered stage","evidence_required":["receipt","handoff","gate_result"]},{"rule_id":"ORCH-RULE-002","from_state":"RUNNING","condition":"retryable failure and attempts within budget","decision":"RETRY","to_stage":"same stage","evidence_required":["failure receipt"]},{"rule_id":"ORCH-RULE-003","from_state":"BLOCKED","condition":"non-retryable or unrepairable failure","decision":"STOP_BLOCKED","to_stage":"STOP_BLOCKED","evidence_required":["blocked receipt"]}],"retry_policy":{"max_attempts":2,"retryable_failures":["transient_tool_interruption","validator_runtime_interrupt"],"non_retryable_failures":["checksum_mismatch","missing_required_marker","duplicate_zip_member","unrouteable_signal"],"backoff_strategy":"bounded same-turn retry only after root cause identified","failure_budget":"0 non-retryable failures"},"exit_handlers":[{"handler_id":"ORCH-EXIT-001","condition":"always","action":"write receipt and handoff or blocked receipt","always_runs":True,"evidence_output":"runtime/receipts/mpp_v3/"},{"handler_id":"ORCH-EXIT-002","condition":"failure","action":"route to R17/R18/STOP_BLOCKED","always_runs":True,"evidence_output":"runtime/handoffs/mpp_v3/"}],"reconciliation_policy":{"policy_id":"ORCH-RECON-001","compare":"desired_state vs actual_state plus required markers","repair_on_drift":True,"stop_on_unrepairable":True,"writes_receipt":True},"controller_summary":{"stage_count":len(graph),"blocked":False,"ready_for_export_promotion":True},"result_hash":""}
    packet["result_hash"]=stable_hash(packet)
    validate_orchestrator_plan(packet)
    out_path.parent.mkdir(parents=True,exist_ok=True)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_orchestrator_runtime_controller_v1_py_L106', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--validate"); p.add_argument("--gate"); args=p.parse_args()
    if args.validate:
        packet=json.loads(Path(args.validate).read_text()); print(json.dumps(validate_orchestrator_plan(packet),sort_keys=True)); return 0
    if args.gate:
        packet=json.loads(Path(args.gate).read_text()); result=run_controller_gate(packet); print(json.dumps(result,sort_keys=True)); return 0 if result["verdict"]=="PASS" else 1
    p.error("provide --validate or --gate")
if __name__=="__main__": raise SystemExit(main())
