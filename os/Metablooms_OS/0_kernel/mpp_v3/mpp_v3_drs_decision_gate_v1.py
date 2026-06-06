#!/usr/bin/env python3
"""MPP v3 R5 DRS decision-record validator and research-to-decision gate."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

class DRSValidationError(RuntimeError): pass

def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def req(cond: bool, code: str) -> None:
    if not cond: raise DRSValidationError(code)

def validate_decision_record(packet: dict[str, Any], normalized_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    required = ["schema_version","decision_id","stage","title","status","created_at","context","decision","alternatives_considered","evidence_bindings","consequences","confidence","result_hash"]
    for k in required: req(k in packet, f"DRS_MISSING_{k.upper()}")
    req(packet["schema_version"] == "mpp.drs_decision_record.v1", "DRS_BAD_SCHEMA_VERSION")
    req(packet["stage"] == "DRS", "DRS_BAD_STAGE")
    req(str(packet["decision_id"]).startswith("DRS-"), "DRS_BAD_DECISION_ID")
    req(packet["status"] in {"proposed","accepted","deprecated","superseded","blocked"}, "DRS_BAD_STATUS")
    req(len(packet["context"]) >= 20 and len(packet["decision"]) >= 20, "DRS_CONTEXT_OR_DECISION_TOO_SHORT")
    req(isinstance(packet["alternatives_considered"], list) and len(packet["alternatives_considered"]) >= 2, "DRS_NEEDS_TWO_ALTERNATIVES")
    for i, alt in enumerate(packet["alternatives_considered"]):
        req(len(alt.get("option", "")) >= 5, f"DRS_ALT_{i}_BAD_OPTION")
        req(len(alt.get("reason_rejected", "")) >= 10, f"DRS_ALT_{i}_BAD_REASON")
    req(packet["confidence"] in {"low","medium","high"}, "DRS_BAD_CONFIDENCE")
    req(isinstance(packet["evidence_bindings"], list) and packet["evidence_bindings"], "DRS_NO_EVIDENCE_BINDINGS")
    known_atoms = None
    if normalized_packet is not None:
        known_atoms = {a["atom_id"] for a in normalized_packet.get("normalized_atoms", [])}
    for i, bind in enumerate(packet["evidence_bindings"]):
        req(bind.get("source_packet_id"), f"DRS_BINDING_{i}_NO_SOURCE")
        req(bind.get("atom_ids"), f"DRS_BINDING_{i}_NO_ATOMS")
        if known_atoms is not None: req(set(bind["atom_ids"]).issubset(known_atoms), f"DRS_BINDING_{i}_UNKNOWN_ATOM")
    cons = packet["consequences"]
    req(cons.get("positive") and cons.get("negative") is not None, "DRS_BAD_CONSEQUENCES")
    expected = stable_hash(packet)
    req(packet["result_hash"] == expected, "DRS_HASH_MISMATCH")
    return {"status":"PASS", "decision_id":packet["decision_id"], "result_hash":expected}

def write_decision_record(decision_id: str, title: str, context: str, decision: str, alternatives: list[dict[str,str]], evidence_bindings: list[dict[str,Any]], out_path: Path, status: str = "accepted", confidence: str = "high") -> dict[str, Any]:
    packet = {"schema_version":"mpp.drs_decision_record.v1", "decision_id":decision_id, "stage":"DRS", "title":title, "status":status, "created_at":datetime.now(UTC).isoformat(), "supersedes":None, "context":context, "decision":decision, "alternatives_considered":alternatives, "evidence_bindings":evidence_bindings, "consequences":{"positive":["Creates auditable decision provenance tied to normalized research evidence."], "negative":["Requires explicit evidence and alternatives before later stages can proceed."], "follow_up_actions":["Use accepted decisions as CDR inputs."]}, "confidence":confidence, "result_hash":""}
    packet["result_hash"] = stable_hash(packet)
    validate_decision_record(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_drs_decision_gate_v1_py_L50', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet

def research_to_decision_gate(decisions: list[dict[str, Any]], normalized_packet: dict[str, Any] | None = None) -> dict[str, Any]:
    blocked = []
    ids = []
    for d in decisions:
        try:
            validate_decision_record(d, normalized_packet)
            ids.append(d["decision_id"])
            if d["status"] not in {"accepted", "proposed"}: blocked.append(f"{d['decision_id']}: inactive status {d['status']}")
            if d["confidence"] == "low" and d["status"] == "accepted": blocked.append(f"{d['decision_id']}: accepted with low confidence")
        except Exception as e:
            blocked.append(f"{d.get('decision_id','UNKNOWN')}: {e}")
    gate = {"schema_version":"mpp.research_to_decision_gate.v1", "gate_id":"RTD-001", "stage":"DRS", "created_at":datetime.now(UTC).isoformat(), "decision_ids":ids, "verdict":"BLOCK" if blocked else "PASS", "blocked_reasons":blocked, "result_hash":""}
    gate["result_hash"] = stable_hash(gate)
    return gate

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--validate-decision")
    ap.add_argument("--normalized-context")
    ap.add_argument("--gate", nargs="+")
    args=ap.parse_args()
    ctx=json.loads(Path(args.normalized_context).read_text()) if args.normalized_context else None
    if args.validate_decision:
        pkt=json.loads(Path(args.validate_decision).read_text())
        print(json.dumps(validate_decision_record(pkt, ctx), sort_keys=True)); return 0
    if args.gate:
        decisions=[json.loads(Path(p).read_text()) for p in args.gate]
        gate=research_to_decision_gate(decisions, ctx)
        print(json.dumps(gate, sort_keys=True))
        return 0 if gate["verdict"] == "PASS" else 2
    ap.error("provide --validate-decision or --gate")
if __name__ == "__main__": raise SystemExit(main())
