#!/usr/bin/env python3
"""MPP v3 R12: RRP recovery-plan validator and rollback gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RRPValidationError(RuntimeError):
    pass


BAD_VALUES = {"", "tbd", "n/a", "unknown", "later", "~", "varies", "none"}


def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise RRPValidationError(code)


def _bad(value: object) -> bool:
    return str(value).strip().lower() in BAD_VALUES


def validate_rrp_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version","packet_id","stage","created_at","objective_id","source_sso_packet_id",
        "recovery_objectives","failure_modes","rollback_plan","recovery_runbook","validation_drills",
        "drift_controls","cleanup_plan","result_hash",
    ]
    for key in required:
        require(key in packet, f"RRP_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.rrp_recovery_plan_packet.v1", "RRP_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "RRP", "RRP_BAD_STAGE")
    objectives = packet["recovery_objectives"]
    for key in ["rto","rpo","rollback_window","data_loss_tolerance","success_state"]:
        require(key in objectives, f"RRP_OBJECTIVE_MISSING_{key.upper()}")
        require(not _bad(objectives[key]), f"RRP_OBJECTIVE_BAD_{key.upper()}")
    fms = packet["failure_modes"]
    require(fms, "RRP_NO_FAILURE_MODES")
    require(any(fm.get("rollback_required") is True for fm in fms), "RRP_NO_ROLLBACK_REQUIRED_FAILURE_MODE")
    for i, fm in enumerate(fms):
        for key in ["failure_id","mode","severity","detection","safe_state","recovery_strategy","rollback_required"]:
            require(key in fm, f"RRP_FM_{i}_MISSING_{key.upper()}")
        require(fm["severity"] in {"S1_LOW","S2_MED","S3_HIGH","S4_CRITICAL"}, f"RRP_FM_{i}_BAD_SEVERITY")
        require(not _bad(fm["detection"]), f"RRP_FM_{i}_BAD_DETECTION")
        require(not _bad(fm["safe_state"]), f"RRP_FM_{i}_BAD_SAFE_STATE")
    rollback = packet["rollback_plan"]
    for key in ["trigger_conditions","steps","owner","verification","abort_conditions"]:
        require(key in rollback, f"RRP_ROLLBACK_MISSING_{key.upper()}")
    require(rollback["trigger_conditions"], "RRP_ROLLBACK_NO_TRIGGER_CONDITIONS")
    require(rollback["steps"], "RRP_ROLLBACK_NO_STEPS")
    require(not _bad(rollback["owner"]), "RRP_ROLLBACK_NO_OWNER")
    require(not _bad(rollback["verification"]), "RRP_ROLLBACK_NO_VERIFICATION")
    runbook = packet["recovery_runbook"]
    require(runbook, "RRP_NO_RECOVERY_RUNBOOK")
    for i, step in enumerate(runbook):
        for key in ["step_id","action","owner","expected_result","evidence"]:
            require(key in step, f"RRP_STEP_{i}_MISSING_{key.upper()}")
            require(not _bad(step[key]), f"RRP_STEP_{i}_BAD_{key.upper()}")
    drills = packet["validation_drills"]
    require(drills, "RRP_NO_VALIDATION_DRILLS")
    for i, drill in enumerate(drills):
        for key in ["drill_id","scenario","frequency","pass_criteria"]:
            require(key in drill, f"RRP_DRILL_{i}_MISSING_{key.upper()}")
            require(not _bad(drill[key]), f"RRP_DRILL_{i}_BAD_{key.upper()}")
    require(packet["drift_controls"], "RRP_NO_DRIFT_CONTROLS")
    require(packet["cleanup_plan"], "RRP_NO_CLEANUP_PLAN")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "RRP_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":expected}


def run_rollback_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    try:
        validate_rrp_packet(packet)
    except RRPValidationError as e:
        violations.append(str(e))
    objectives = packet.get("recovery_objectives", {})
    for key in ["rto","rpo","rollback_window"]:
        if _bad(objectives.get(key, "")):
            violations.append(f"RRP_GATE_BAD_{key.upper()}")
    rollback = packet.get("rollback_plan", {})
    if not rollback.get("trigger_conditions"):
        violations.append("RRP_GATE_NO_ROLLBACK_TRIGGERS")
    if not rollback.get("steps"):
        violations.append("RRP_GATE_NO_ROLLBACK_STEPS")
    if not rollback.get("abort_conditions"):
        violations.append("RRP_GATE_NO_ABORT_CONDITIONS")
    if not packet.get("validation_drills"):
        violations.append("RRP_GATE_NO_DRILL")
    if not packet.get("drift_controls"):
        violations.append("RRP_GATE_NO_DRIFT_CONTROL")
    if not packet.get("cleanup_plan"):
        violations.append("RRP_GATE_NO_CLEANUP_PLAN")
    if len(packet.get("validation_drills", [])) == 1:
        warnings.append("RRP_WARN_ONLY_ONE_VALIDATION_DRILL")
    verdict = "FAIL" if violations else "PASS"
    result = {
        "schema_version":"mpp.rrp_rollback_gate_result.v1",
        "gate_id":f"RRP-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"RRP_ROLLBACK_GATE",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict,
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "coverage":{
            "has_rto": not _bad(objectives.get("rto", "")),
            "has_rpo": not _bad(objectives.get("rpo", "")),
            "has_rollback_window": not _bad(objectives.get("rollback_window", "")),
            "failure_modes": len(packet.get("failure_modes", [])),
            "rollback_steps": len(rollback.get("steps", [])),
            "validation_drills": len(packet.get("validation_drills", [])),
            "drift_controls": len(packet.get("drift_controls", [])),
            "cleanup_steps": len(packet.get("cleanup_plan", [])),
        },
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result


def write_rrp_packet(source_sso_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.rrp_recovery_plan_packet.v1",
        "packet_id":f"RRP-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"RRP",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_sso_packet_id":source_sso_packet_id,
        "recovery_objectives":{
            "rto":"one bounded stage response",
            "rpo":"zero loss of validated receipts/handoffs already written to /mnt/data",
            "rollback_window":"before READY handoff to implementation",
            "data_loss_tolerance":"no loss of source artifacts; overlay outputs may be discarded if gate fails",
            "success_state":"RRP gate passes and downstream implementation can safely proceed."
        },
        "failure_modes":[
            {
                "failure_id":"RRP-FM-001",
                "mode":"stage writes incomplete or corrupted artifacts",
                "severity":"S4_CRITICAL",
                "detection":"missing file, hash mismatch, zip integrity failure, or validator failure",
                "safe_state":"block READY handoff and preserve failed receipt",
                "recovery_strategy":"rollback to previous stage bundle and rerun bounded repair stage",
                "rollback_required":True
            },
            {
                "failure_id":"RRP-FM-002",
                "mode":"scope creep attempts downstream implementation inside RRP",
                "severity":"S3_HIGH",
                "detection":"artifact path or handoff target outside RRP contract",
                "safe_state":"stop with blocked receipt",
                "recovery_strategy":"route to correct downstream stage through SSO change control",
                "rollback_required":False
            }
        ],
        "rollback_plan":{
            "trigger_conditions":[
                "predecessor checksum mismatch",
                "RRP validator or rollback gate returns FAIL",
                "ZIP integrity test fails",
                "required receipt or handoff is missing"
            ],
            "steps":[
                "Stop downstream promotion.",
                "Write blocked receipt with failure class and evidence.",
                "Use previous PASS bundle and sidecar as recovery source.",
                "Rerun the smallest repair stage that addresses the failed gate."
            ],
            "owner":"MPP_R12",
            "verification":"Rerun validator, rollback gate, checksum verification, and zipfile.testzip.",
            "abort_conditions":["unwritable artifact root","missing predecessor bundle and sidecar"]
        },
        "recovery_runbook":[
            {
                "step_id":"RRP-STEP-001",
                "action":"Verify predecessor bundle checksum and ZIP integrity.",
                "owner":"MPP_R12",
                "expected_result":"checksum matches and testzip returns None",
                "evidence":"predecessor_verification receipt block"
            },
            {
                "step_id":"RRP-STEP-002",
                "action":"Validate RRP packet and run rollback gate.",
                "owner":"MPP_R12",
                "expected_result":"validator and gate return PASS",
                "evidence":"smoke-test output in receipt"
            },
            {
                "step_id":"RRP-STEP-003",
                "action":"Package RRP outputs and checksum sidecar.",
                "owner":"MPP_R12",
                "expected_result":"bundle exists, sidecar exists, ZIP integrity passes",
                "evidence":"bundle SHA-256 and sidecar"
            }
        ],
        "validation_drills":[
            {
                "drill_id":"DRILL-001",
                "scenario":"invalid packet with missing rollback steps",
                "frequency":"per RRP stage build",
                "pass_criteria":"gate exits nonzero and records rollback-step violation"
            },
            {
                "drill_id":"DRILL-002",
                "scenario":"invalid packet with unknown recovery objectives",
                "frequency":"per RRP stage build",
                "pass_criteria":"validator exits nonzero on placeholder objective"
            }
        ],
        "drift_controls":["compare predecessor sidecar hash before trusting handoff","write latest receipt/handoff pointers only after PASS"],
        "cleanup_plan":["remove or ignore failed overlay outputs after blocked receipt","preserve failure evidence for debugging stage"],
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_rrp_packet(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_rrp_recovery_plan_rollback_gate_v1_py_L231', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_rrp_packet(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_rollback_gate(packet)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")


if __name__ == "__main__":
    raise SystemExit(main())
