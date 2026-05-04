#!/usr/bin/env python3
"""MPP v3 R15: Trace analysis validator and anomaly gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TraceValidationError(RuntimeError):
    pass


HEX32 = re.compile(r"^[a-f0-9]{32}$")
HEX16 = re.compile(r"^[a-f0-9]{16}$")


def stable_hash(payload: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(payload, sort_keys=True))
    clone["result_hash"] = ""
    return hashlib.sha256(json.dumps(clone, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def require(cond: bool, code: str) -> None:
    if not cond:
        raise TraceValidationError(code)


def _span_ids(packet: dict[str, Any]) -> set[str]:
    return {s.get("span_id") for s in packet.get("spans", []) if s.get("span_id")}


def _detect_anomalies(packet: dict[str, Any]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []
    spans = packet.get("spans", [])
    ids = set()
    seen_stage_order = []
    expected = packet.get("expected_stage_order", [])
    expected_pos = {name: i for i, name in enumerate(expected)}
    last_pos = -1
    for span in spans:
        sid = span.get("span_id")
        if sid in ids:
            anomalies.append({"rule_id":"TRACE-RULE-001","severity":"S4_CRITICAL","message":f"duplicate span_id {sid}"})
        ids.add(sid)
        if span.get("end_index", 0) < span.get("start_index", 0):
            anomalies.append({"rule_id":"TRACE-RULE-002","severity":"S4_CRITICAL","message":f"negative order span {sid}"})
        if span.get("status") == "ERROR":
            anomalies.append({"rule_id":"TRACE-RULE-003","severity":"S4_CRITICAL","message":f"error span {sid}"})
        if not span.get("artifact_refs"):
            anomalies.append({"rule_id":"TRACE-RULE-004","severity":"S3_HIGH","message":f"missing artifact refs {sid}"})
        parent = span.get("parent_span_id")
        if parent is not None and parent not in ids and parent not in _span_ids(packet):
            anomalies.append({"rule_id":"TRACE-RULE-005","severity":"S3_HIGH","message":f"unknown parent span {parent}"})
        stage = span.get("stage_name")
        if stage in expected_pos:
            pos = expected_pos[stage]
            if pos < last_pos:
                anomalies.append({"rule_id":"TRACE-RULE-006","severity":"S3_HIGH","message":f"stage out of order {stage}"})
            last_pos = max(last_pos, pos)
            seen_stage_order.append(stage)
    missing = [s for s in expected if s not in seen_stage_order]
    for stage in missing:
        anomalies.append({"rule_id":"TRACE-RULE-007","severity":"S3_HIGH","message":f"missing expected stage {stage}"})
    return anomalies


def validate_trace_packet(packet: dict[str, Any]) -> dict[str, Any]:
    required = [
        "schema_version","packet_id","stage","created_at","objective_id","source_verification_packet_id",
        "trace_context","spans","expected_stage_order","anomaly_rules","trace_summary","result_hash",
    ]
    for key in required:
        require(key in packet, f"TRACE_MISSING_{key.upper()}")
    require(packet["schema_version"] == "mpp.trace_analysis_packet.v1", "TRACE_BAD_SCHEMA_VERSION")
    require(packet["stage"] == "TRACE_ANALYSIS", "TRACE_BAD_STAGE")
    ctx = packet["trace_context"]
    require(HEX32.match(ctx.get("trace_id","")) is not None, "TRACE_BAD_TRACE_ID")
    require(ctx.get("traceparent_format") in {"w3c_trace_context_v00","metablooms_internal"}, "TRACE_BAD_CONTEXT_FORMAT")
    require(HEX16.match(ctx.get("root_span_id","")) is not None, "TRACE_BAD_ROOT_SPAN_ID")
    spans = packet["spans"]
    require(spans, "TRACE_NO_SPANS")
    ids = set()
    root_seen = False
    for i, span in enumerate(spans):
        for key in ["span_id","parent_span_id","name","stage_name","start_index","end_index","duration_ms","status","artifact_refs","attributes"]:
            require(key in span, f"TRACE_SPAN_{i}_MISSING_{key.upper()}")
        require(HEX16.match(span["span_id"]) is not None, f"TRACE_SPAN_{i}_BAD_ID")
        require(span["span_id"] not in ids, f"TRACE_DUPLICATE_SPAN_{span['span_id']}")
        ids.add(span["span_id"])
        if span["span_id"] == ctx["root_span_id"]:
            root_seen = True
        require(span["end_index"] >= span["start_index"], f"TRACE_SPAN_{i}_END_BEFORE_START")
        require(span["duration_ms"] >= 0, f"TRACE_SPAN_{i}_NEGATIVE_DURATION")
        require(span["status"] in {"OK","ERROR","SKIPPED"}, f"TRACE_SPAN_{i}_BAD_STATUS")
    require(root_seen, "TRACE_ROOT_SPAN_NOT_PRESENT")
    for i, span in enumerate(spans):
        parent = span.get("parent_span_id")
        require(parent is None or parent in ids, f"TRACE_SPAN_{i}_UNKNOWN_PARENT")
    require(packet["expected_stage_order"], "TRACE_NO_EXPECTED_STAGE_ORDER")
    require(packet["anomaly_rules"], "TRACE_NO_ANOMALY_RULES")
    anomalies = _detect_anomalies(packet)
    summary = packet["trace_summary"]
    require(summary["span_count"] == len(spans), "TRACE_SUMMARY_SPAN_COUNT_MISMATCH")
    require(summary["error_count"] == sum(1 for s in spans if s["status"] == "ERROR"), "TRACE_SUMMARY_ERROR_COUNT_MISMATCH")
    require(summary["missing_artifact_span_count"] == sum(1 for s in spans if not s["artifact_refs"]), "TRACE_SUMMARY_MISSING_ARTIFACT_COUNT_MISMATCH")
    require(summary["out_of_order_span_count"] == sum(1 for a in anomalies if a["rule_id"] == "TRACE-RULE-006"), "TRACE_SUMMARY_OUT_OF_ORDER_COUNT_MISMATCH")
    expected = stable_hash(packet)
    require(packet["result_hash"] == expected, "TRACE_HASH_MISMATCH")
    return {"status":"PASS","packet_id":packet["packet_id"],"anomaly_count":len(anomalies),"result_hash":expected}


def run_anomaly_gate(packet: dict[str, Any]) -> dict[str, Any]:
    violations: list[str] = []
    warnings: list[str] = []
    anomalies: list[dict[str, Any]] = []
    try:
        validate_trace_packet(packet)
    except TraceValidationError as e:
        violations.append(str(e))
    anomalies = _detect_anomalies(packet)
    for a in anomalies:
        if a.get("severity") in {"S3_HIGH","S4_CRITICAL"}:
            violations.append(f"{a['rule_id']}:{a['message']}")
        else:
            warnings.append(f"{a['rule_id']}:{a['message']}")
    verdict = "FAIL" if violations else "PASS"
    result = {
        "schema_version":"mpp.trace_anomaly_gate_result.v1",
        "gate_id":f"TRACE-GATE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"TRACE_ANOMALY_GATE",
        "created_at":datetime.now(UTC).isoformat(),
        "packet_id":packet.get("packet_id","UNKNOWN"),
        "verdict":verdict,
        "violations":sorted(set(violations)),
        "warnings":warnings,
        "anomalies":anomalies,
        "result_hash":"",
    }
    result["result_hash"] = stable_hash(result)
    return result


def write_trace_packet(source_verification_packet_id: str, objective_id: str, out_path: Path) -> dict[str, Any]:
    trace_id = hashlib.sha256(f"{objective_id}:trace".encode()).hexdigest()[:32]
    root_span = hashlib.sha256(f"{objective_id}:root".encode()).hexdigest()[:16]
    verify_span = hashlib.sha256(f"{objective_id}:verify".encode()).hexdigest()[:16]
    packet = {
        "schema_version":"mpp.trace_analysis_packet.v1",
        "packet_id":f"TRACE-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        "stage":"TRACE_ANALYSIS",
        "created_at":datetime.now(UTC).isoformat(),
        "objective_id":objective_id,
        "source_verification_packet_id":source_verification_packet_id,
        "trace_context":{"trace_id":trace_id,"traceparent_format":"w3c_trace_context_v00","root_span_id":root_span},
        "spans":[
            {"span_id":root_span,"parent_span_id":None,"name":"R15 trace analysis root","stage_name":"TRACE_ANALYSIS","start_index":0,"end_index":1,"duration_ms":1.0,"status":"OK","artifact_refs":["TRACE_ANALYSIS_PACKET_SCHEMA_v1.json"],"attributes":{"mpp.stage":"R15"}},
            {"span_id":verify_span,"parent_span_id":root_span,"name":"R14 verification predecessor","stage_name":"VERIFICATION","start_index":1,"end_index":2,"duration_ms":1.0,"status":"OK","artifact_refs":["MPP_R14_VERIFICATION_EVIDENCE_SCHEMA_AND_TEST_RECEIPT_GATE_20260501T012800Z.zip"],"attributes":{"mpp.predecessor":"R14"}}
        ],
        "expected_stage_order":["TRACE_ANALYSIS","VERIFICATION"],
        "anomaly_rules":[
            {"rule_id":"TRACE-RULE-001","name":"duplicate_span_id","severity":"S4_CRITICAL","description":"No two spans may share an id."},
            {"rule_id":"TRACE-RULE-002","name":"invalid_span_order","severity":"S4_CRITICAL","description":"Span end index must not precede start index."},
            {"rule_id":"TRACE-RULE-003","name":"error_span","severity":"S4_CRITICAL","description":"Error spans block trace promotion."},
            {"rule_id":"TRACE-RULE-004","name":"missing_artifact_refs","severity":"S3_HIGH","description":"Every non-skipped span must bind to an artifact reference."},
            {"rule_id":"TRACE-RULE-005","name":"unknown_parent_span","severity":"S3_HIGH","description":"Parent spans must exist in the trace."},
            {"rule_id":"TRACE-RULE-006","name":"stage_out_of_order","severity":"S3_HIGH","description":"Stages must appear in expected order."},
            {"rule_id":"TRACE-RULE-007","name":"missing_expected_stage","severity":"S3_HIGH","description":"Expected stages must appear at least once."}
        ],
        "trace_summary":{"span_count":2,"error_count":0,"missing_artifact_span_count":0,"out_of_order_span_count":0},
        "result_hash":"",
    }
    packet["result_hash"] = stable_hash(packet)
    validate_trace_packet(packet)
    _mb_write_json_file(out_path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_mpp_v3_mpp_v3_trace_analysis_anomaly_gate_v1_py_L179', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate")
    parser.add_argument("--gate")
    args = parser.parse_args()
    if args.validate:
        packet = json.loads(Path(args.validate).read_text(encoding="utf-8"))
        print(json.dumps(validate_trace_packet(packet), sort_keys=True))
        return 0
    if args.gate:
        packet = json.loads(Path(args.gate).read_text(encoding="utf-8"))
        result = run_anomaly_gate(packet)
        print(json.dumps(result, sort_keys=True))
        return 0 if result["verdict"] == "PASS" else 1
    parser.error("provide --validate or --gate")


if __name__ == "__main__":
    raise SystemExit(main())
