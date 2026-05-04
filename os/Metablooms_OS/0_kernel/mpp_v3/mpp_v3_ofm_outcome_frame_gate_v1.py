#!/usr/bin/env python3
"""MPP v3 R7: OFM outcome-frame validator and measurable-success gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class OFMValidationError(RuntimeError):
    pass


def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise OFMValidationError(code)


def validate_ofm_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version","packet_id","stage","created_at","objective_id","source_cdr_packet_id",
        "outcomes","success_criteria","failure_criteria","measurement_plan","result_hash",
    ]
    for key in required:
        require(key in packet, f"OFM_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.ofm_outcome_frame_packet.v1", "OFM_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "OFM", "OFM_BAD_STAGE")
    require(packet["outcomes"], "OFM_NO_OUTCOMES")
    outcome_ids = set()
    for i, outcome in enumerate(packet["outcomes"]):
        for key in ["outcome_id","description","stakeholder_value","quality_model_refs"]:
            require(key in outcome, f"OFM_OUTCOME_{i}_MISSING_{key.upper()}")
        require(outcome["outcome_id"].startswith("OUT-"), f"OFM_OUTCOME_{i}_BAD_ID")
        require(outcome["quality_model_refs"], f"OFM_OUTCOME_{i}_NO_QUALITY_REFS")
        outcome_ids.add(outcome["outcome_id"])
    require(packet["success_criteria"], "OFM_NO_SUCCESS_CRITERIA")
    measurable_count = 0
    blocking_count = 0
    for i, sc in enumerate(packet["success_criteria"]):
        for key in ["criterion_id","outcome_id","criterion","measurable","metric","threshold","verification_method","blocking"]:
            require(key in sc, f"OFM_SC_{i}_MISSING_{key.upper()}")
        require(sc["criterion_id"].startswith("SC-"), f"OFM_SC_{i}_BAD_ID")
        require(sc["outcome_id"] in outcome_ids, f"OFM_SC_{i}_UNKNOWN_OUTCOME")
        if sc["measurable"] is True:
            measurable_count += 1
            require(str(sc["metric"]).strip(), f"OFM_SC_{i}_NO_METRIC")
            require(str(sc["threshold"]).strip(), f"OFM_SC_{i}_NO_THRESHOLD")
            require(str(sc["verification_method"]).strip(), f"OFM_SC_{i}_NO_VERIFICATION")
        if sc["blocking"] is True:
            blocking_count += 1
    require(measurable_count >= 1, "OFM_NO_MEASURABLE_SUCCESS_CRITERION")
    require(blocking_count >= 1, "OFM_NO_BLOCKING_SUCCESS_CRITERION")
    require(packet["failure_criteria"], "OFM_NO_FAILURE_CRITERIA")
    plan = packet["measurement_plan"]
    for key in ["when_measured","evidence_required","minimum_measurable_success_count"]:
        require(key in plan, f"OFM_MEASUREMENT_PLAN_MISSING_{key.upper()}")
    require(plan["minimum_measurable_success_count"] <= measurable_count, "OFM_MIN_MEASURABLE_EXCEEDS_AVAILABLE")
    require(plan["evidence_required"], "OFM_NO_EVIDENCE_REQUIRED")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "OFM_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":expected}


def run_measurable_success_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    try:
        validate_ofm_packet(packet)
    except OFMValidationError as e:
        violations.append(str(e))
    measurable = [sc for sc in packet.get("success_criteria", []) if sc.get("measurable") is True]
    blocking = [sc for sc in packet.get("success_criteria", []) if sc.get("blocking") is True]
    if not measurable:
        violations.append("POLICY_BLOCK_NO_MEASURABLE_SUCCESS")
    if not blocking:
        violations.append("POLICY_BLOCK_NO_BLOCKING_SUCCESS")
    for sc in measurable:
        threshold = str(sc.get("threshold", "")).strip().lower()
        if threshold in {"", "tbd", "n/a", "unknown", "later"}:
            violations.append(f"POLICY_BLOCK_BAD_THRESHOLD_{sc.get('criterion_id','UNKNOWN')}")
    if len(packet.get("failure_criteria", [])) < 1:
        violations.append("POLICY_BLOCK_NO_FAILURE_CRITERIA")
    if len(measurable) < 2:
        warnings.append("POLICY_WARN_ONLY_ONE_MEASURABLE_SUCCESS_CRITERION")
    verdict = "FAIL" if violations else "PASS"
    result = {
        "schema_version":"mpp.ofm_measurable_success_gate_result.v1",
        "gate_id":f"OFM-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"OFM_MEASURABLE_SUCCESS_GATE",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict,
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result


def write_ofm_packet(source_cdr_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.ofm_outcome_frame_packet.v1",
        "packet_id":f"OFM-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"OFM",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_cdr_packet_id":source_cdr_packet_id,
        "outcomes":[
            {
                "outcome_id":"OUT-001",
                "description":"The governed implementation produces a verifiable artifact that satisfies the declared objective.",
                "stakeholder_value":"The operator can trust the result because success is measured before promotion.",
                "quality_model_refs":["ISO_25010_functional_suitability","ISO_25010_reliability"]
            }
        ],
        "success_criteria":[
            {
                "criterion_id":"SC-001",
                "outcome_id":"OUT-001",
                "criterion":"All required R7 artifacts exist and ZIP integrity passes.",
                "measurable":True,
                "metric":"zip_integrity_and_file_presence",
                "threshold":"testzip == None and required file count >= 8",
                "verification_method":"direct filesystem check plus zipfile.testzip",
                "blocking":True
            },
            {
                "criterion_id":"SC-002",
                "outcome_id":"OUT-001",
                "criterion":"The OFM packet includes at least one measurable and blocking success criterion.",
                "measurable":True,
                "metric":"measurable_blocking_criteria_count",
                "threshold":">= 1",
                "verification_method":"OFM measurable success gate",
                "blocking":True
            }
        ],
        "failure_criteria":[
            "No measurable success criterion is present.",
            "No blocking success criterion is present.",
            "Any required artifact is missing or ZIP integrity fails."
        ],
        "measurement_plan":{
            "when_measured":"before ADS and before export promotion",
            "evidence_required":["validator output","gate output","receipt artifact","checksum sidecar"],
            "minimum_measurable_success_count":1
        },
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_ofm_packet(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_ofm_outcome_frame_gate_v1_py_L162', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_ofm_packet(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_measurable_success_gate(packet)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")


if __name__ == "__main__":
    raise SystemExit(main())
