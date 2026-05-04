#!/usr/bin/env python3
"""MPP v3 R13: Implementation contract validator and write-path gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ImplementationValidationError(RuntimeError):
    pass


BAD_SEGMENTS = {"", ".", ".."}
DEFAULT_FORBIDDEN = ["..", "~", "\x00", "//"]


def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise ImplementationValidationError(code)


def _is_subpath(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _bad_path_text(text: str, forbidden: list[str]) -> str | None:
    if text.startswith("/"):
        return "ABSOLUTE_PATH_FORBIDDEN"
    parts = Path(text).parts
    if any(p in BAD_SEGMENTS for p in parts):
        return "BAD_PATH_SEGMENT"
    for pat in forbidden:
        if pat and pat in text:
            return f"FORBIDDEN_PATTERN:{pat}"
    return None


def validate_implementation_contract(packet: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version","packet_id","stage","created_at","objective_id","source_rrp_packet_id",
        "implementation_targets","write_policy","artifact_plan","pre_write_checks","post_write_checks","provenance","result_hash",
    ]
    for key in required:
        require(key in packet, f"IMPL_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.implementation_contract_packet.v1", "IMPL_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "IMPLEMENTATION", "IMPL_BAD_STAGE")
    require(packet["implementation_targets"], "IMPL_NO_TARGETS")
    seen = set()
    forbidden = packet["write_policy"].get("forbidden_path_patterns", DEFAULT_FORBIDDEN)
    for i, target in enumerate(packet["implementation_targets"]):
        for key in ["target_id","path","artifact_type","operation","expected_hash_mode","owner"]:
            require(key in target, f"IMPL_TARGET_{i}_MISSING_{key.upper()}")
        require(target["target_id"].startswith("IMPL-"), f"IMPL_TARGET_{i}_BAD_ID")
        require(target["target_id"] not in seen, f"IMPL_DUPLICATE_TARGET_{target['target_id']}")
        seen.add(target["target_id"])
        bad = _bad_path_text(target["path"], forbidden)
        require(bad is None, f"IMPL_TARGET_{i}_{bad}")
        require(target["expected_hash_mode"] in {"sha256_required","hash_not_applicable"}, f"IMPL_TARGET_{i}_BAD_HASH_MODE")
    wp = packet["write_policy"]
    for key in ["allowed_roots","forbidden_path_patterns","requires_probe","requires_parent_creation","requires_atomic_write","requires_receipt"]:
        require(key in wp, f"IMPL_WRITE_POLICY_MISSING_{key.upper()}")
    require(wp["allowed_roots"], "IMPL_NO_ALLOWED_ROOTS")
    require(wp["requires_probe"] is True, "IMPL_WRITE_POLICY_MUST_REQUIRE_PROBE")
    require(wp["requires_parent_creation"] is True, "IMPL_WRITE_POLICY_MUST_REQUIRE_PARENT_CREATION")
    require(wp["requires_atomic_write"] is True, "IMPL_WRITE_POLICY_MUST_REQUIRE_ATOMIC_WRITE")
    require(wp["requires_receipt"] is True, "IMPL_WRITE_POLICY_MUST_REQUIRE_RECEIPT")
    require(packet["artifact_plan"], "IMPL_NO_ARTIFACT_PLAN")
    require(packet["pre_write_checks"], "IMPL_NO_PRE_WRITE_CHECKS")
    require(packet["post_write_checks"], "IMPL_NO_POST_WRITE_CHECKS")
    prov = packet["provenance"]
    for key in ["builder","inputs","expected_outputs","verification_expectations"]:
        require(key in prov, f"IMPL_PROVENANCE_MISSING_{key.upper()}")
        require(prov[key], f"IMPL_PROVENANCE_EMPTY_{key.upper()}")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "IMPL_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"result_hash":expected}


def run_write_path_gate(packet: dict[str, Any], base_root: str | None = None, probe: bool = False) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    checked: list[dict[str, Any]] = []
    try:
        validate_implementation_contract(packet)
    except ImplementationValidationError as e:
        violations.append(str(e))
    roots = [Path(base_root)] if base_root else [Path(r) for r in packet.get("write_policy", {}).get("allowed_roots", [])]
    roots = [r for r in roots if str(r)]
    if not roots:
        violations.append("IMPL_GATE_NO_ALLOWED_ROOTS")
    forbidden = packet.get("write_policy", {}).get("forbidden_path_patterns", DEFAULT_FORBIDDEN)
    for target in packet.get("implementation_targets", []):
        rel = target.get("path", "")
        bad = _bad_path_text(rel, forbidden)
        target_result = {"target_id": target.get("target_id"), "path": rel, "allowed": False, "reason": None}
        if bad:
            target_result["reason"] = bad
            violations.append(f"IMPL_GATE_BAD_PATH_{target.get('target_id')}:{bad}")
            checked.append(target_result)
            continue
        allowed_paths = []
        for r in roots:
            candidate = (r / rel).resolve()
            if _is_subpath(candidate, r):
                allowed_paths.append(candidate)
        if not allowed_paths:
            target_result["reason"] = "OUTSIDE_ALLOWED_ROOTS"
            violations.append(f"IMPL_GATE_OUTSIDE_ALLOWED_ROOTS_{target.get('target_id')}")
            checked.append(target_result)
            continue
        target_result["allowed"] = True
        target_result["resolved_path"] = str(allowed_paths[0])
        if probe:
            try:
                probe_path = allowed_paths[0].parent / f".write_probe_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.tmp"
                probe_path.parent.mkdir(parents=True, exist_ok=True)
                probe_path.write_text("probe", encoding="utf-8")
                if probe_path.read_text(encoding="utf-8") != "probe":
                    violations.append(f"IMPL_GATE_PROBE_READBACK_FAILED_{target.get('target_id')}")
                probe_path.unlink(missing_ok=True)
            except Exception as e:
                violations.append(f"IMPL_GATE_PROBE_FAILED_{target.get('target_id')}:{type(e).__name__}")
        checked.append(target_result)
    if not packet.get("write_policy", {}).get("requires_receipt"):
        violations.append("IMPL_GATE_RECEIPT_REQUIRED")
    if len(packet.get("implementation_targets", [])) == 1:
        warnings.append("IMPL_WARN_SINGLE_TARGET_CONTRACT")
    verdict = "FAIL" if violations else "PASS"
    result = {
        "schema_version":"mpp.implementation_write_path_gate_result.v1",
        "gate_id":f"IMPL-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"IMPLEMENTATION_WRITE_PATH_GATE",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict,
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "checked_targets":checked,
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result


def write_implementation_contract(source_rrp_packet_id: str, objective_id: str, allowed_root: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.implementation_contract_packet.v1",
        "packet_id":f"IMPL-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"IMPLEMENTATION",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_rrp_packet_id":source_rrp_packet_id,
        "implementation_targets":[
            {
                "target_id":"IMPL-001",
                "path":"0_kernel/mpp_v3/mpp_v3_implementation_write_path_gate_v1.py",
                "artifact_type":"python",
                "operation":"create",
                "expected_hash_mode":"sha256_required",
                "owner":"MPP_R13"
            },
            {
                "target_id":"IMPL-002",
                "path":"0_kernel/schemas/mpp_v3/IMPLEMENTATION_CONTRACT_PACKET_SCHEMA_v1.json",
                "artifact_type":"json",
                "operation":"create",
                "expected_hash_mode":"sha256_required",
                "owner":"MPP_R13"
            }
        ],
        "write_policy":{
            "allowed_roots":[allowed_root],
            "forbidden_path_patterns":["..","~","\u0000","//"],
            "requires_probe":True,
            "requires_parent_creation":True,
            "requires_atomic_write":True,
            "requires_receipt":True
        },
        "artifact_plan":[
            {
                "artifact_id":"ART-001",
                "relative_path":"0_kernel/mpp_v3/mpp_v3_implementation_write_path_gate_v1.py",
                "purpose":"validate implementation contracts and write paths",
                "validation":"py_compile plus valid/invalid write-path gate fixtures"
            },
            {
                "artifact_id":"ART-002",
                "relative_path":"runtime/receipts/mpp_v3/MPP_R13_IMPLEMENTATION_CONTRACT_SCHEMA_AND_WRITE_PATH_GATE_RECEIPT_LATEST.json",
                "purpose":"prove R13 execution and tests",
                "validation":"exists and contains PASS status"
            }
        ],
        "pre_write_checks":["verify R12 bundle checksum and ZIP integrity","validate implementation contract","run write-path gate with probe"],
        "post_write_checks":["recompute artifact hashes","run py_compile","package ZIP and checksum sidecar"],
        "provenance":{
            "builder":"MPP_R13_IMPLEMENTATION_CONTRACT_SCHEMA_AND_WRITE_PATH_GATE",
            "inputs":["R12 handoff","RRP recovery plan schema","write-root probe"],
            "expected_outputs":["implementation schema","write-path gate","fixtures","receipt","handoff","ZIP sidecar"],
            "verification_expectations":["hashes match","write paths stay under allowed root","forbidden paths blocked"]
        },
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_implementation_contract(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_implementation_write_path_gate_v1_py_L220', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    parser.add_argument("--base-root")
    parser.add_argument("--probe", action="store_true")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_implementation_contract(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_write_path_gate(packet, base_root=args.base_root, probe=args.probe)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")


if __name__ == "__main__":
    raise SystemExit(main())
