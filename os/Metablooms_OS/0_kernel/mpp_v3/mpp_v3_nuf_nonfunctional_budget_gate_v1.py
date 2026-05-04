#!/usr/bin/env python3
"""MPP v3 R10: NUF nonfunctional requirements validator and budget gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class NUFValidationError(RuntimeError):
    pass


REQUIRED_CATEGORIES = {"reliability", "security", "determinism", "artifact_integrity"}
BAD_THRESHOLDS = {"", "tbd", "n/a", "unknown", "later", "~", "varies"}


def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise NUFValidationError(code)


def validate_nuf_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version","packet_id","stage","created_at","objective_id","source_uxr_packet_id",
        "quality_model","requirements","budget_policy","tradeoffs","result_hash",
    ]
    for key in required:
        require(key in packet, f"NUF_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.nuf_nonfunctional_requirements_packet.v1", "NUF_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "NUF", "NUF_BAD_STAGE")
    qm = packet["quality_model"]
    for key in ["model","version","mapped_characteristics"]:
        require(key in qm, f"NUF_QUALITY_MODEL_MISSING_{key.upper()}")
    require(len(qm["mapped_characteristics"]) >= 3, "NUF_TOO_FEW_QUALITY_CHARACTERISTICS")
    reqs = packet["requirements"]
    require(len(reqs) >= 3, "NUF_TOO_FEW_REQUIREMENTS")
    seen = set()
    categories = set()
    blocking = 0
    for i, req in enumerate(reqs):
        for key in ["requirement_id","category","description","metric","threshold","measurement_window","verification_method","blocking","source_constraint_ids"]:
            require(key in req, f"NUF_REQ_{i}_MISSING_{key.upper()}")
        rid = req["requirement_id"]
        require(rid.startswith("NUF-"), f"NUF_REQ_{i}_BAD_ID")
        require(rid not in seen, f"NUF_DUPLICATE_REQUIREMENT_{rid}")
        seen.add(rid)
        categories.add(req["category"])
        require(str(req["metric"]).strip(), f"NUF_REQ_{i}_NO_METRIC")
        require(str(req["threshold"]).strip().lower() not in BAD_THRESHOLDS, f"NUF_REQ_{i}_BAD_THRESHOLD")
        require(str(req["verification_method"]).strip(), f"NUF_REQ_{i}_NO_VERIFICATION")
        if req["blocking"] is True:
            blocking += 1
    require(blocking >= 1, "NUF_NO_BLOCKING_REQUIREMENT")
    budget = packet["budget_policy"]
    for key in ["policy_id","budget_type","budget_metric","allowed_budget","burn_action","escalation_action"]:
        require(key in budget, f"NUF_BUDGET_MISSING_{key.upper()}")
    require(str(budget["allowed_budget"]).strip().lower() not in BAD_THRESHOLDS, "NUF_BUDGET_BAD_ALLOWED_BUDGET")
    require(packet["tradeoffs"], "NUF_NO_TRADEOFFS")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "NUF_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"categories":sorted(categories),"result_hash":expected}


def run_budget_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    categories: set[str] = set()
    try:
        res = validate_nuf_packet(packet)
        categories = set(res["categories"])
    except NUFValidationError as e:
        violations.append(str(e))
        categories = {r.get("category") for r in packet.get("requirements", []) if r.get("category")}
    missing_categories = sorted(REQUIRED_CATEGORIES - categories)
    for category in missing_categories:
        violations.append(f"NUF_MISSING_REQUIRED_CATEGORY_{category.upper()}")
    blocking_by_category = {r.get("category") for r in packet.get("requirements", []) if r.get("blocking") is True}
    if not (REQUIRED_CATEGORIES & blocking_by_category):
        violations.append("NUF_NO_BLOCKING_REQUIRED_CATEGORY")
    for req in packet.get("requirements", []):
        if str(req.get("threshold","")).strip().lower() in BAD_THRESHOLDS:
            violations.append(f"NUF_BAD_THRESHOLD_{req.get('requirement_id','UNKNOWN')}")
        if not str(req.get("measurement_window","")).strip():
            violations.append(f"NUF_NO_MEASUREMENT_WINDOW_{req.get('requirement_id','UNKNOWN')}")
    if packet.get("budget_policy", {}).get("budget_type") not in {"error_budget","latency_budget","token_budget","time_budget","artifact_budget","memory_budget"}:
        violations.append("NUF_BAD_BUDGET_TYPE")
    if "performance" not in categories and "latency" not in categories:
        warnings.append("NUF_WARN_NO_PERFORMANCE_OR_LATENCY_REQUIREMENT")
    verdict = "FAIL" if violations else "PASS"
    result = {
        "schema_version":"mpp.nuf_budget_gate_result.v1",
        "gate_id":f"NUF-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"NUF_BUDGET_GATE",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict,
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "coverage":{
            "required_categories": sorted(REQUIRED_CATEGORIES),
            "present_categories": sorted([c for c in categories if c]),
            "blocking_categories": sorted([c for c in blocking_by_category if c]),
            "budget_type": packet.get("budget_policy", {}).get("budget_type"),
        },
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result


def write_nuf_packet(source_uxr_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.nuf_nonfunctional_requirements_packet.v1",
        "packet_id":f"NUF-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"NUF",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_uxr_packet_id":source_uxr_packet_id,
        "quality_model":{
            "model":"ISO_IEC_25010_2023",
            "version":"2023",
            "mapped_characteristics":["reliability","security","maintainability","performance_efficiency","portability","usability"]
        },
        "requirements":[
            {
                "requirement_id":"NUF-001",
                "category":"reliability",
                "description":"Stage validation must fail closed when required artifacts or predecessor checks are missing.",
                "metric":"fail_closed_gate_coverage",
                "threshold":"100% of required predecessor/bundle checks must pass before READY handoff",
                "measurement_window":"per stage run",
                "verification_method":"receipt predecessor_verification and gate verdict inspection",
                "blocking":True,
                "source_constraint_ids":["UXC-002"]
            },
            {
                "requirement_id":"NUF-002",
                "category":"artifact_integrity",
                "description":"Every delivered bundle must include a checksum sidecar and pass ZIP integrity validation.",
                "metric":"zip_integrity_and_sidecar_match",
                "threshold":"zipfile.testzip == None and SHA-256 equals sidecar",
                "measurement_window":"per export",
                "verification_method":"direct sha256_file plus zipfile.testzip",
                "blocking":True,
                "source_constraint_ids":["UXC-002"]
            },
            {
                "requirement_id":"NUF-003",
                "category":"security",
                "description":"No validator may accept unknown or placeholder thresholds for blocking requirements.",
                "metric":"bad_threshold_count",
                "threshold":"0",
                "measurement_window":"per packet validation",
                "verification_method":"NUF budget gate threshold scan",
                "blocking":True,
                "source_constraint_ids":["UXC-002"]
            },
            {
                "requirement_id":"NUF-004",
                "category":"determinism",
                "description":"Packet result hashes must be stable and recomputable from canonical JSON.",
                "metric":"hash_mismatch_count",
                "threshold":"0",
                "measurement_window":"per packet validation",
                "verification_method":"stable_hash recomputation",
                "blocking":True,
                "source_constraint_ids":["UXC-002"]
            },
            {
                "requirement_id":"NUF-005",
                "category":"latency",
                "description":"Governed stages must remain bounded enough for ChatGPT mobile operator use.",
                "metric":"stage_bundle_count",
                "threshold":"one ZIP plus one checksum sidecar per stage",
                "measurement_window":"per stage response",
                "verification_method":"final response and receipt artifact check",
                "blocking":False,
                "source_constraint_ids":["UXC-001"]
            }
        ],
        "budget_policy":{
            "policy_id":"BUDGET-001",
            "budget_type":"error_budget",
            "budget_metric":"blocking_gate_failures_allowed_after PASS",
            "allowed_budget":"0 blocking gate failures after a PASS receipt",
            "burn_action":"mark stage BLOCKED and prevent READY handoff",
            "escalation_action":"write failure-class receipt and route to repair stage"
        },
        "tradeoffs":[
            {
                "tradeoff_id":"TRD-001",
                "tension":"speed versus verification depth",
                "decision":"prefer bounded verification with receipts over broad unverified implementation",
                "rationale":"MPP must preserve artifact trust in a turn-bounded mobile ChatGPT workflow."
            }
        ],
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_nuf_packet(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_nuf_nonfunctional_budget_gate_v1_py_L211', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_nuf_packet(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_budget_gate(packet)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")


if __name__ == "__main__":
    raise SystemExit(main())
