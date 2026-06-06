#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
VALID_DIMENSIONS={"theory","implementation","failure_modes","requirements","evidence_quality","source_conflict","scope","validation","user_context","provenance"}
VALID_EVIDENCE_STATUS={"missing","partial","contradictory","stale","sufficient"}
VALID_STRATEGY={"research_more","ask_user","narrow_scope","convert_to_assumption","write_blocked_receipt","accept_with_risk","resolve_from_artifact"}
VALID_SEVERITY={"critical","high","medium","low"}
VALID_STATUS={"open","resolved","accepted_risk","blocked"}
class MMDValidationError(RuntimeError): pass
def _require(cond: bool, code: str)->None:
    if not cond: raise MMDValidationError(code)
def stable_hash(payload: dict[str,Any])->str:
    clone=json.loads(json.dumps(payload, sort_keys=True)); clone["result_hash"]=""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",",":")).encode()).hexdigest()
def validate_gap_ledger(ledger: dict[str,Any])->dict[str,Any]:
    for key in ["schema_version","ledger_id","stage","created_at","objective_id","inputs","gaps","decision","handoff"]:
        _require(key in ledger, f"MMD_MISSING_{key.upper()}")
    _require(ledger["schema_version"]=="mmd_gap_ledger.v1", "MMD_BAD_SCHEMA_VERSION")
    _require(ledger["stage"]=="MMD", "MMD_BAD_STAGE")
    for key in ["research_planner_packet","see_packet","ce_packet","normalized_evidence"]:
        _require(key in ledger["inputs"] and str(ledger["inputs"][key]), f"MMD_INPUT_MISSING_{key.upper()}")
    _require(isinstance(ledger["gaps"], list), "MMD_GAPS_NOT_LIST")
    seen=set(); critical_open=0; blocking_open=[]
    for i,gap in enumerate(ledger["gaps"]):
        for key in ["gap_id","dimension","severity","description","evidence_status","blocks_stage","resolution_strategy","status"]:
            _require(key in gap, f"MMD_GAP_{i}_MISSING_{key.upper()}")
        gid=gap["gap_id"]
        _require(isinstance(gid,str) and gid.startswith("GAP-") and len(gid)==7, f"MMD_GAP_{i}_BAD_ID")
        _require(gid not in seen, f"MMD_DUPLICATE_GAP_ID_{gid}"); seen.add(gid)
        _require(gap["dimension"] in VALID_DIMENSIONS, f"MMD_GAP_{gid}_BAD_DIMENSION")
        _require(gap["severity"] in VALID_SEVERITY, f"MMD_GAP_{gid}_BAD_SEVERITY")
        _require(len(str(gap["description"]))>=5, f"MMD_GAP_{gid}_DESCRIPTION_TOO_SHORT")
        _require(gap["evidence_status"] in VALID_EVIDENCE_STATUS, f"MMD_GAP_{gid}_BAD_EVIDENCE_STATUS")
        _require(isinstance(gap["blocks_stage"], list), f"MMD_GAP_{gid}_BLOCKS_STAGE_NOT_LIST")
        _require(gap["resolution_strategy"] in VALID_STRATEGY, f"MMD_GAP_{gid}_BAD_STRATEGY")
        _require(gap["status"] in VALID_STATUS, f"MMD_GAP_{gid}_BAD_STATUS")
        if gap["severity"]=="critical" and gap["status"] in {"open","blocked"}: critical_open+=1
        if gap["status"] in {"open","blocked"} and gap["blocks_stage"]: blocking_open.append(gid)
    dec=ledger["decision"]
    for key in ["verdict","critical_open_count","allowed_next_stage"]: _require(key in dec, f"MMD_DECISION_MISSING_{key.upper()}")
    _require(dec["verdict"] in {"PASS","PASS_WITH_WARNINGS","BLOCKED"}, "MMD_BAD_VERDICT")
    _require(dec["critical_open_count"]==critical_open, "MMD_CRITICAL_COUNT_MISMATCH")
    if critical_open>0 or blocking_open:
        _require(dec["verdict"]=="BLOCKED", "MMD_ESCALATION_NOT_BLOCKED")
        _require(dec["allowed_next_stage"] in {"RRP","RESEARCH_PLANNER","SEE","BLOCKED_RECEIPT"}, "MMD_BAD_BLOCKED_NEXT_STAGE")
    else:
        _require(dec["verdict"] in {"PASS","PASS_WITH_WARNINGS"}, "MMD_PASS_STATE_BAD_VERDICT")
        _require(dec["allowed_next_stage"]!="BLOCKED_RECEIPT", "MMD_PASS_STATE_BLOCKED_NEXT_STAGE")
    _require(ledger["handoff"].get("next_stage")==dec["allowed_next_stage"], "MMD_HANDOFF_DECISION_MISMATCH")
    _require(isinstance(ledger["handoff"].get("conditions"), list), "MMD_HANDOFF_CONDITIONS_NOT_LIST")
    if "result_hash" in ledger: _require(ledger["result_hash"]==stable_hash(ledger), "MMD_HASH_MISMATCH")
    return {"status":"PASS","ledger_id":ledger["ledger_id"],"verdict":dec["verdict"],"critical_open_count":critical_open,"blocking_open":blocking_open}
def write_gap_ledger(*, objective_id:str, inputs:dict[str,str], gaps:list[dict[str,Any]], allowed_next_stage:str, out_path:Path)->dict[str,Any]:
    critical_open=sum(1 for g in gaps if g.get("severity")=="critical" and g.get("status") in {"open","blocked"})
    blocking_open=[g.get("gap_id") for g in gaps if g.get("status") in {"open","blocked"} and g.get("blocks_stage")]
    verdict="BLOCKED" if critical_open or blocking_open else ("PASS_WITH_WARNINGS" if gaps else "PASS")
    if verdict=="BLOCKED" and allowed_next_stage not in {"RRP","RESEARCH_PLANNER","SEE","BLOCKED_RECEIPT"}: allowed_next_stage="BLOCKED_RECEIPT"
    ledger={"schema_version":"mmd_gap_ledger.v1","ledger_id":f"MMD-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"MMD","created_at":datetime.now(UTC).isoformat(),"objective_id":objective_id,"inputs":inputs,"gaps":gaps,"decision":{"verdict":verdict,"critical_open_count":critical_open,"allowed_next_stage":allowed_next_stage},"handoff":{"next_stage":allowed_next_stage,"conditions":[] if verdict=="PASS" else ["Resolve or accept listed MMD gaps before proceeding."]},"result_hash":""}
    ledger["result_hash"]=stable_hash(ledger); validate_gap_ledger(ledger)
    out_path.write_text(json.dumps(ledger, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return ledger
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--validate", required=True); a=ap.parse_args()
    print(json.dumps(validate_gap_ledger(json.loads(Path(a.validate).read_text(encoding="utf-8"))), sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
