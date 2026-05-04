#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ROOT = Path("/mnt/data/Metablooms_OS_refined")
DEFAULT_SCHEMA = DEFAULT_ROOT / "0_kernel/schemas/CE_PACKET_SCHEMA_v1.json"
DEFAULT_RECEIPT_DIR = DEFAULT_ROOT / "0_kernel/registry/ce_validation_receipts"
REQUIRED = ["version","created_at","stage","task","intent_model","hidden_goal_detection","misinterpretation_traps","trap_mitigation_plan","fact_inference_uncertainty_map","comprehension_readiness_decision","ce_verdict"]

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def is_context_summary_only(packet: Dict[str, Any]) -> bool:
    substantive = {"intent_model","hidden_goal_detection","misinterpretation_traps","trap_mitigation_plan","fact_inference_uncertainty_map","comprehension_readiness_decision"}
    keys = set(packet.keys())
    return ("context_summary" in keys and not (keys & substantive)) or keys.issubset({"version","created_at","stage","task","context_summary","ce_verdict","issues"})

def validate_packet(packet: Dict[str, Any], schema: Dict[str, Any], strict: bool=False) -> Dict[str, Any]:
    issues = []
    for f in schema.get("required", REQUIRED):
        if f not in packet:
            issues.append(f"missing_required_field:{f}")
    if packet.get("stage") != "CE_COMPREHENSION_PASS":
        issues.append("stage_must_be_CE_COMPREHENSION_PASS")
    if is_context_summary_only(packet):
        issues.append("context_summary_only")
    for f in ["hidden_goal_detection","misinterpretation_traps","trap_mitigation_plan"]:
        if f in packet and (not isinstance(packet[f], list) or not packet[f]):
            issues.append(f"{f}_missing_or_empty")
    readiness = packet.get("comprehension_readiness_decision")
    if isinstance(readiness, dict) and readiness.get("ready") is True and packet.get("ce_verdict") == "FAIL":
        issues.append("readiness_conflicts_with_ce_verdict")
    return {
        "version":"1.0","created_at":time.time(),"stage":"CE_VALIDATION",
        "schema_validation":{"passed": not any(i.startswith("missing_required_field") for i in issues), "issues":[i for i in issues if i.startswith("missing_required_field")]},
        "semantic_validation":{"passed": not any(i in issues for i in ["context_summary_only","readiness_conflicts_with_ce_verdict"]), "issues":[i for i in issues if i in ["context_summary_only","readiness_conflicts_with_ce_verdict"]]},
        "context_summary_only_check":{"passed": "context_summary_only" not in issues, "context_summary_only": "context_summary_only" in issues},
        "verdict":"PASS" if not issues else "FAIL","issues":issues,
        "next_stage":"PLAN" if not issues else "BLOCK_WITH_CE_VALIDATION_RECEIPT"
    }

def write_receipt(result: Dict[str, Any], receipt_dir: Path, source: str, schema_path: str) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    result["packet_source"] = source
    result["schema_path"] = schema_path
    path = receipt_dir / f"CE_VALIDATION_RECEIPT_{int(time.time()*1000)}.json"
    result["receipt_path"] = str(path)
    _mb_write_json_file(path, result, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_ce_packet_validator_v1_py_L50', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    return path

def main(argv: Optional[List[str]]=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--packet")
    ap.add_argument("--packet-file")
    ap.add_argument("--schema", default=str(DEFAULT_SCHEMA))
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    try:
        schema = load_json(Path(args.schema))
        if args.packet_file:
            packet = load_json(Path(args.packet_file)); source = args.packet_file
        elif args.packet:
            packet = json.loads(args.packet); source = "(inline)"
        else:
            print(json.dumps({"verdict":"FAIL","issues":["missing_packet_input"]}), file=sys.stderr); return 1
    except Exception as exc:
        failure = {"version":"1.0","created_at":time.time(),"stage":"CE_VALIDATION","verdict":"FAIL","issues":[f"parse_error:{exc!r}"],"next_stage":"BLOCK_WITH_CE_VALIDATION_RECEIPT"}
        try: write_receipt(failure, Path(args.receipt_dir), args.packet_file or "(inline)", args.schema)
        except Exception: pass
        print(json.dumps(failure, indent=2), file=sys.stderr); return 2
    result = validate_packet(packet, schema, args.strict)
    receipt = write_receipt(result, Path(args.receipt_dir), source, args.schema)
    print(json.dumps(result if args.json else {"verdict":result["verdict"],"issues":result["issues"],"receipt_path":str(receipt)}, indent=2))
    return 0 if result["verdict"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
