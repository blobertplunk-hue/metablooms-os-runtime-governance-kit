#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class ExportPromotionError(RuntimeError): pass

REQUIRED_PAC_CHECK_IDS = {"PROMOTION_AUTHORITY_COHERENCE_GATE_v1", "PAC-GATE", "PAC-000"}
REQUIRED_PAC_CHECK_NAMES = {"promotion_authority_coherence", "promotion_authority_coherence_gate", "authority_coherence"}

def stable_hash(payload: dict[str, Any]) -> str:
    clone=json.loads(json.dumps(payload,sort_keys=True))
    clone["result_hash"]=""
    return hashlib.sha256(json.dumps(clone,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def require(cond: bool, code: str) -> None:
    if not cond: raise ExportPromotionError(code)

def validate_export_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required=["schema_version","packet_id","stage","created_at","objective_id","source_orchestrator_packet_id","export_candidate","included_stage_range","promotion_checks","required_markers","bundle_inventory","promotion_summary","result_hash"]
    for key in required: require(key in packet, f"EXPORT_MISSING_{key.upper()}")
    require(packet["schema_version"]=="mpp.export_promotion_packet.v1","EXPORT_BAD_SCHEMA_VERSION")
    require(packet["stage"]=="EXPORT_PROMOTION","EXPORT_BAD_STAGE")
    cand=packet["export_candidate"]
    for key in ["zip_path","sha256","sidecar_path","zip_testzip","duplicate_count","member_count"]:
        require(key in cand, f"EXPORT_CANDIDATE_MISSING_{key.upper()}")
    require(cand["zip_testzip"] is None, "EXPORT_ZIP_TESTZIP_FAILED")
    require(int(cand["duplicate_count"])==0, "EXPORT_DUPLICATE_MEMBERS_PRESENT")
    require(int(cand["member_count"])>0, "EXPORT_EMPTY_BUNDLE")
    require(packet["included_stage_range"]=="R0-R23", "EXPORT_STAGE_RANGE_NOT_R0_R23")
    pac_checks=[]
    for i,check in enumerate(packet["promotion_checks"]):
        for key in ["check_id","name","status","evidence_refs","blocking"]:
            require(key in check, f"EXPORT_CHECK_{i}_MISSING_{key.upper()}")
        require(check["evidence_refs"], f"EXPORT_CHECK_{i}_NO_EVIDENCE")
        check_id=str(check.get("check_id", ""))
        check_name=str(check.get("name", "")).lower()
        if check_id in REQUIRED_PAC_CHECK_IDS or check_name in REQUIRED_PAC_CHECK_NAMES:
            pac_checks.append(check)
        if check["blocking"] is True:
            require(check["status"]=="PASS", f"EXPORT_BLOCKING_CHECK_FAILED_{check['check_id']}")
    require(pac_checks, "EXPORT_MISSING_PROMOTION_AUTHORITY_COHERENCE_GATE")
    require(any(c.get("blocking") is True and c.get("status") == "PASS" for c in pac_checks), "EXPORT_PROMOTION_AUTHORITY_COHERENCE_GATE_NOT_PASSING_BLOCKER")
    markers=packet["required_markers"]
    require(markers, "EXPORT_NO_REQUIRED_MARKERS")
    for i,m in enumerate(markers):
        for key in ["marker_id","path","present","purpose"]:
            require(key in m, f"EXPORT_MARKER_{i}_MISSING_{key.upper()}")
        require(m["present"] is True, f"EXPORT_REQUIRED_MARKER_MISSING_{m['path']}")
    inv=packet["bundle_inventory"]
    for key in ["schema_count","impl_count","fixture_count","receipt_count","handoff_count","stage_bundle_count"]:
        require(key in inv, f"EXPORT_INVENTORY_MISSING_{key.upper()}")
        require(int(inv[key])>0, f"EXPORT_INVENTORY_ZERO_{key.upper()}")
    summary=packet["promotion_summary"]
    require(summary["decision"]=="PROMOTE", "EXPORT_DECISION_NOT_PROMOTE")
    require(summary["all_blocking_checks_passed"] is True, "EXPORT_BLOCKING_CHECKS_NOT_ALL_PASS")
    require(summary["sidecar_required"] is True, "EXPORT_SIDECAR_REQUIRED_NOT_TRUE")
    require(packet["result_hash"]==stable_hash(packet), "EXPORT_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":packet["result_hash"]}

def run_export_promotion_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations=[]; warnings=[]
    try: validate_export_packet(packet)
    except ExportPromotionError as e: violations.append(str(e))
    checks=packet.get("promotion_checks",[])
    if any(c.get("blocking") and c.get("status")!="PASS" for c in checks):
        violations.append("EXPORT_GATE_BLOCKING_CHECK_FAILED")
    if any(m.get("present") is not True for m in packet.get("required_markers",[])):
        violations.append("EXPORT_GATE_REQUIRED_MARKER_MISSING")
    if packet.get("promotion_summary",{}).get("decision")!="PROMOTE":
        violations.append("EXPORT_GATE_DECISION_NOT_PROMOTE")
    result={"schema_version":"mpp.export_promotion_gate_result.v1","gate_id":f"EXPORT-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","stage":"EXPORT_PROMOTION_GATE","created_at":datetime.now(UTC).isoformat(),"packet_id":packet.get("packet_id","UNKNOWN"),"verdict":"FAIL" if violations else "PASS","violations":sorted(set(violations)),"warnings":warnings,"promotion_decision":{"decision":"BLOCK" if violations else "PROMOTE","authority_zip":packet.get("export_candidate",{}).get("zip_path"),"authority_sha256":packet.get("export_candidate",{}).get("sha256"),"next_recommended_stage":"USE_AS_CURRENT_AUTHORITY_OR_START_NEW_TASK"},"result_hash":""}
    result["result_hash"]=stable_hash(result)
    return result

def make_pointer(authority_zip: str, authority_sha256: str, authority_sidecar: str) -> dict[str, Any]:
    ptr={"schema_version":"mpp.export_authority_pointer.v1","pointer_id":f"EXPORT-AUTHORITY-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}","created_at":datetime.now(UTC).isoformat(),"authority_zip":authority_zip,"authority_sha256":authority_sha256,"authority_sidecar":authority_sidecar,"stage_range":"R0-R23","status":"PROMOTED","next_recommended_stage":"USE_AS_CURRENT_AUTHORITY_OR_START_NEW_TASK","result_hash":""}
    ptr["result_hash"]=stable_hash(ptr)
    return ptr

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--validate"); p.add_argument("--gate"); args=p.parse_args()
    if args.validate:
        packet=json.loads(Path(args.validate).read_text()); print(json.dumps(validate_export_packet(packet),sort_keys=True)); return 0
    if args.gate:
        packet=json.loads(Path(args.gate).read_text()); result=run_export_promotion_gate(packet); print(json.dumps(result,sort_keys=True)); return 0 if result["verdict"]=="PASS" else 1
    p.error("provide --validate or --gate")
if __name__=="__main__": raise SystemExit(main())
