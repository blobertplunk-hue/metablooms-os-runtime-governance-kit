#!/usr/bin/env python3
"""MPP v3 R8: ADS architecture DAG validator and ownership gate."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ADSValidationError(RuntimeError):
    pass


def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise ADSValidationError(code)


def _toposort(component_ids: set[str], edges: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    """Return topological order and cycle violations. Edge direction: from -> to means from must precede to."""
    incoming = {cid: set() for cid in component_ids}
    outgoing = {cid: set() for cid in component_ids}
    violations: list[str] = []
    for e in edges:
        f, t = e.get("from"), e.get("to")
        if f not in component_ids or t not in component_ids:
            violations.append(f"ADS_EDGE_UNKNOWN_COMPONENT_{f}_TO_{t}")
            continue
        if f == t:
            violations.append(f"ADS_SELF_EDGE_{f}")
            continue
        outgoing[f].add(t)
        incoming[t].add(f)
    ready = sorted([cid for cid in component_ids if not incoming[cid]])
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for nxt in sorted(outgoing[node]):
            incoming[nxt].discard(node)
            if not incoming[nxt] and nxt not in order and nxt not in ready:
                ready.append(nxt)
        ready.sort()
    if len(order) != len(component_ids):
        remaining = sorted(component_ids - set(order))
        violations.append("ADS_DAG_CYCLE_DETECTED:" + ",".join(remaining))
    return order, violations


def validate_ads_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version","packet_id","stage","created_at","objective_id","source_ofm_packet_id",
        "components","dependency_edges","ownership_map","outcome_traceability","architecture_decisions","result_hash",
    ]
    for key in required:
        require(key in packet, f"ADS_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.ads_architecture_dag_packet.v1", "ADS_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "ADS", "ADS_BAD_STAGE")
    require(packet["components"], "ADS_NO_COMPONENTS")
    component_ids: set[str] = set()
    for i, c in enumerate(packet["components"]):
        for key in ["component_id","name","type","purpose","owned_outputs","risk_class"]:
            require(key in c, f"ADS_COMPONENT_{i}_MISSING_{key.upper()}")
        require(c["component_id"].startswith("CMP-"), f"ADS_COMPONENT_{i}_BAD_ID")
        require(c["component_id"] not in component_ids, f"ADS_DUPLICATE_COMPONENT_{c['component_id']}")
        component_ids.add(c["component_id"])
        require(c["owned_outputs"], f"ADS_COMPONENT_{i}_NO_OUTPUTS")
    ownership = packet["ownership_map"]
    for cid in component_ids:
        require(cid in ownership, f"ADS_COMPONENT_{cid}_NO_OWNER")
        owner = ownership[cid]
        for key in ["owner","authority","accountability"]:
            require(key in owner and str(owner[key]).strip(), f"ADS_COMPONENT_{cid}_OWNER_MISSING_{key.upper()}")
    order, topo_violations = _toposort(component_ids, packet.get("dependency_edges", []))
    require(not topo_violations, "|".join(topo_violations))
    require(packet["outcome_traceability"], "ADS_NO_OUTCOME_TRACEABILITY")
    for i, trace in enumerate(packet["outcome_traceability"]):
        for cid in trace.get("component_ids", []):
            require(cid in component_ids, f"ADS_TRACE_{i}_UNKNOWN_COMPONENT_{cid}")
        require(trace.get("success_criterion_ids"), f"ADS_TRACE_{i}_NO_SUCCESS_CRITERIA")
    require(packet["architecture_decisions"], "ADS_NO_ARCHITECTURE_DECISIONS")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "ADS_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"topological_order":order,"result_hash":expected}


def run_dag_ownership_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    order: list[str] = []
    try:
        res = validate_ads_packet(packet)
        order = res["topological_order"]
    except ADSValidationError as e:
        violations.append(str(e))
        component_ids = {c.get("component_id") for c in packet.get("components", []) if c.get("component_id")}
        order, extra = _toposort(component_ids, packet.get("dependency_edges", []))
        violations.extend(extra)
    for c in packet.get("components", []):
        if c.get("risk_class") in {"high", "critical"}:
            owner = packet.get("ownership_map", {}).get(c.get("component_id"), {})
            if not owner.get("accountability"):
                violations.append(f"ADS_HIGH_RISK_NO_ACCOUNTABILITY_{c.get('component_id')}")
    if len(packet.get("components", [])) == 1:
        warnings.append("ADS_WARN_SINGLE_COMPONENT_ARCHITECTURE")
    verdict = "FAIL" if violations else "PASS"
    result = {
        "schema_version":"mpp.ads_dag_ownership_gate_result.v1",
        "gate_id":f"ADS-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"ADS_DAG_OWNERSHIP_GATE",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict,
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "topological_order":order,
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result


def write_ads_packet(source_ofm_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    packet = {
        "schema_version":"mpp.ads_architecture_dag_packet.v1",
        "packet_id":f"ADS-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"ADS",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_ofm_packet_id":source_ofm_packet_id,
        "components":[
            {
                "component_id":"CMP-001",
                "name":"ADS architecture packet schema",
                "type":"schema",
                "purpose":"Defines the architecture component, dependency, ownership, and traceability contract.",
                "owned_outputs":["ADS_ARCHITECTURE_DAG_PACKET_SCHEMA_v1.json"],
                "risk_class":"medium",
            },
            {
                "component_id":"CMP-002",
                "name":"ADS DAG ownership validator",
                "type":"validator",
                "purpose":"Validates architecture packets, rejects cycles, and enforces component ownership.",
                "owned_outputs":["mpp_v3_ads_architecture_dag_gate_v1.py"],
                "risk_class":"high",
            },
            {
                "component_id":"CMP-003",
                "name":"ADS gate fixtures",
                "type":"fixture",
                "purpose":"Proves pass and fail behavior for DAG and ownership contracts.",
                "owned_outputs":["valid_ads_architecture_dag_packet_v1.json","invalid_ads_cycle_packet_v1.json"],
                "risk_class":"low",
            }
        ],
        "dependency_edges":[
            {"from":"CMP-001","to":"CMP-002","kind":"validates"},
            {"from":"CMP-002","to":"CMP-003","kind":"gates"}
        ],
        "ownership_map":{
            "CMP-001":{"owner":"MPP_R8","authority":"schema contract","accountability":"schema changes require validator and fixture updates"},
            "CMP-002":{"owner":"MPP_R8","authority":"validation gate","accountability":"blocks cyclic or ownerless architecture"},
            "CMP-003":{"owner":"MPP_R8","authority":"regression fixtures","accountability":"proves both pass and block paths"}
        },
        "outcome_traceability":[
            {"outcome_id":"OUT-001","component_ids":["CMP-001","CMP-002","CMP-003"],"success_criterion_ids":["SC-001","SC-002"]}
        ],
        "architecture_decisions":[
            "Represent ADS as a DAG so implementation order can be validated before build stages.",
            "Require explicit owner, authority, and accountability for every component.",
            "Trace components to OFM outcomes and success criteria to prevent architecture drift."
        ],
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_ads_packet(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_ads_architecture_dag_gate_v1_py_L187', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_ads_packet(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_dag_ownership_gate(packet)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")


if __name__ == "__main__":
    raise SystemExit(main())
