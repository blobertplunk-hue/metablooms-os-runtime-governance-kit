#!/usr/bin/env python3
"""
MetaBlooms SEE Packet Validator v1.

Purpose:
- Validate SEE packets proving external research when required.
- Require web.run evidence, sources, source-bound claims, gaps/contradictions, synthesis, limitations, and SEE verdict.
- Write validation receipts.

Mutation scope:
- Writes only SEE validation receipts to the requested receipt directory.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_ROOT = Path("/mnt/data/Metablooms_OS_refined")
DEFAULT_SCHEMA = DEFAULT_ROOT / "0_kernel/schemas/SEE_PACKET_SCHEMA_v1.json"
DEFAULT_RECEIPT_DIR = DEFAULT_ROOT / "0_kernel/registry/see_validation_receipts"

REQUIRED_TOP_FIELDS = [
    "version",
    "created_at",
    "stage",
    "original_request",
    "research_trigger",
    "query_plan",
    "web_run_evidence",
    "sources",
    "claim_source_bindings",
    "gaps_and_contradictions",
    "synthesis",
    "limitations",
    "see_verdict",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nonempty_str(value: Any, min_len: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= min_len


def nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and len(value) > 0


def validate_schema_minimal(packet: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    required = schema.get("required", REQUIRED_TOP_FIELDS)

    for field in required:
        if field not in packet:
            issues.append(f"missing_required_field:{field}")

    if packet.get("stage") != "SEE_PASS":
        issues.append("stage_must_be_SEE_PASS")

    if packet.get("see_verdict") not in {"PASS", "FAIL"}:
        issues.append("see_verdict_must_be_PASS_or_FAIL")

    if not nonempty_str(packet.get("original_request"), 1):
        issues.append("original_request_missing")

    trigger = packet.get("research_trigger")
    if not isinstance(trigger, dict):
        issues.append("research_trigger_missing_or_not_object")
    else:
        if trigger.get("required") is not True:
            issues.append("research_trigger_required_false")
        if not nonempty_str(trigger.get("trigger_reason"), 5):
            issues.append("research_trigger.trigger_reason_missing")
        if not nonempty_list(trigger.get("trigger_terms")):
            issues.append("research_trigger.trigger_terms_empty")

    query_plan = packet.get("query_plan")
    if not nonempty_list(query_plan):
        issues.append("query_plan_missing_or_empty")
    elif isinstance(query_plan, list):
        for i, item in enumerate(query_plan):
            if not isinstance(item, dict):
                issues.append(f"query_plan[{i}]_not_object")
                continue
            if not nonempty_str(item.get("query"), 3):
                issues.append(f"query_plan[{i}].query_missing")
            if not nonempty_str(item.get("purpose"), 5):
                issues.append(f"query_plan[{i}].purpose_missing")

    evidence = packet.get("web_run_evidence")
    if not isinstance(evidence, dict):
        issues.append("web_run_evidence_missing_or_not_object")
    else:
        if evidence.get("web_run_called") is not True:
            issues.append("web_run_called_false")
        call_count = evidence.get("call_count")
        if not isinstance(call_count, int) or call_count < 1:
            issues.append("web_run_call_count_zero")
        if evidence.get("tool_reference_required") is not True:
            issues.append("web_run_tool_reference_required_false")

    sources = packet.get("sources")
    if not nonempty_list(sources):
        issues.append("sources_missing_or_empty")
    elif isinstance(sources, list):
        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                issues.append(f"sources[{i}]_not_object")
                continue
            for key in ["source_id", "title", "url_or_ref", "source_type"]:
                if not nonempty_str(source.get(key), 1):
                    issues.append(f"sources[{i}].{key}_missing")
            if not nonempty_list(source.get("used_for")):
                issues.append(f"sources[{i}].used_for_empty")

    bindings = packet.get("claim_source_bindings")
    if not nonempty_list(bindings):
        issues.append("claim_source_bindings_missing_or_empty")
    elif isinstance(bindings, list):
        for i, binding in enumerate(bindings):
            if not isinstance(binding, dict):
                issues.append(f"claim_source_bindings[{i}]_not_object")
                continue
            if not nonempty_str(binding.get("claim"), 5):
                issues.append(f"claim_source_bindings[{i}].claim_missing")
            if not nonempty_list(binding.get("source_ids")):
                issues.append(f"claim_source_bindings[{i}].source_ids_empty")
            if binding.get("confidence") not in {"high", "medium", "low"}:
                issues.append(f"claim_source_bindings[{i}].confidence_invalid")

    gaps = packet.get("gaps_and_contradictions")
    if not isinstance(gaps, dict):
        issues.append("gaps_and_contradictions_missing_or_not_object")
    else:
        if not isinstance(gaps.get("gaps"), list):
            issues.append("gaps_and_contradictions.gaps_missing")
        if not isinstance(gaps.get("contradictions"), list):
            issues.append("gaps_and_contradictions.contradictions_missing")

    if not nonempty_str(packet.get("synthesis"), 20):
        issues.append("synthesis_missing_or_too_short")

    if not isinstance(packet.get("limitations"), list):
        issues.append("limitations_missing_or_not_list")

    return not issues, issues


def validate_source_bindings(packet: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    sources = packet.get("sources", [])
    bindings = packet.get("claim_source_bindings", [])

    source_ids = set()
    if isinstance(sources, list):
        for source in sources:
            if isinstance(source, dict) and isinstance(source.get("source_id"), str):
                source_ids.add(source["source_id"])

    if not source_ids:
        issues.append("no_source_ids_available")

    if isinstance(bindings, list):
        for i, binding in enumerate(bindings):
            if not isinstance(binding, dict):
                continue
            for sid in binding.get("source_ids", []) if isinstance(binding.get("source_ids"), list) else []:
                if sid not in source_ids:
                    issues.append(f"source_binding_references_missing_source:{i}:{sid}")

    # At least one source should be used by at least one claim.
    bound_ids = set()
    if isinstance(bindings, list):
        for binding in bindings:
            if isinstance(binding, dict) and isinstance(binding.get("source_ids"), list):
                bound_ids.update(binding["source_ids"])
    if source_ids and not (source_ids & bound_ids):
        issues.append("no_claims_bound_to_any_source")

    return not issues, issues


def validate_web_run_evidence(packet: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    evidence = packet.get("web_run_evidence")
    if not isinstance(evidence, dict):
        return False, ["web_run_evidence_missing"]

    if evidence.get("web_run_called") is not True:
        issues.append("web_run_called_false")

    call_count = evidence.get("call_count")
    if not isinstance(call_count, int) or call_count < 1:
        issues.append("web_run_call_count_zero")

    if evidence.get("tool_reference_required") is not True:
        issues.append("tool_reference_required_false")

    sources = packet.get("sources")
    if evidence.get("web_run_called") is True and not nonempty_list(sources):
        issues.append("web_run_called_but_no_sources")

    return not issues, issues


def semantic_validate(packet: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    trigger = packet.get("research_trigger", {})
    if isinstance(trigger, dict) and trigger.get("required") is not True:
        issues.append("research_trigger_required_false")

    # Reject packets that look like a summary without source-grounded synthesis.
    synthesis = packet.get("synthesis")
    if isinstance(synthesis, str):
        lower = synthesis.lower()
        if len(synthesis.strip()) < 20:
            issues.append("summary_without_synthesis")
        if "source" not in lower and "evidence" not in lower and "research" not in lower:
            issues.append("synthesis_lacks_evidence_language")
    else:
        issues.append("summary_without_synthesis")

    if packet.get("see_verdict") == "PASS":
        # PASS must not contain unresolved severe missing-evidence conditions.
        evidence = packet.get("web_run_evidence", {})
        if not isinstance(evidence, dict) or evidence.get("web_run_called") is not True:
            issues.append("pass_verdict_without_web_run_evidence")
        if not nonempty_list(packet.get("sources")):
            issues.append("pass_verdict_without_sources")
        if not nonempty_list(packet.get("claim_source_bindings")):
            issues.append("pass_verdict_without_claim_bindings")

    return not issues, issues


def validate_packet(packet: Dict[str, Any], schema: Dict[str, Any], strict: bool = False) -> Dict[str, Any]:
    schema_ok, schema_issues = validate_schema_minimal(packet, schema)
    web_ok, web_issues = validate_web_run_evidence(packet)
    binding_ok, binding_issues = validate_source_bindings(packet)
    semantic_ok, semantic_issues = semantic_validate(packet)

    issues: List[str] = []
    for group in [schema_issues, web_issues, binding_issues, semantic_issues]:
        for issue in group:
            if issue not in issues:
                issues.append(issue)

    verdict = "PASS" if not issues else "FAIL"
    return {
        "version": "1.0",
        "created_at": time.time(),
        "stage": "SEE_VALIDATION",
        "schema_validation": {"passed": schema_ok, "issues": schema_issues},
        "web_run_evidence_validation": {"passed": web_ok, "issues": web_issues},
        "source_binding_validation": {"passed": binding_ok, "issues": binding_issues},
        "semantic_validation": {"passed": semantic_ok, "issues": semantic_issues},
        "verdict": verdict,
        "issues": issues,
        "next_stage": "PLAN_OR_SYNTHESIS" if verdict == "PASS" else "BLOCK_WITH_SEE_VALIDATION_RECEIPT",
    }


def write_receipt(result: Dict[str, Any], receipt_dir: Path, source: str, schema_path: str) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    result["packet_source"] = source
    result["schema_path"] = schema_path
    path = receipt_dir / f"SEE_VALIDATION_RECEIPT_{int(time.time() * 1000)}.json"
    result["receipt_path"] = str(path)
    _mb_write_json_file(path, result, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_see_packet_validator_v1_py_L277', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="MetaBlooms SEE packet validator v1")
    parser.add_argument("--packet", default=None, help="Inline SEE packet JSON")
    parser.add_argument("--packet-file", default=None, help="Path to SEE packet JSON")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Path to SEE packet schema")
    parser.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR), help="Receipt output directory")
    parser.add_argument("--json", action="store_true", help="Print full validation result")
    parser.add_argument("--strict", action="store_true", help="Reserved for future stricter validation")
    args = parser.parse_args(argv)

    if not args.packet and not args.packet_file:
        print(json.dumps({"verdict": "FAIL", "issues": ["missing_packet_input"]}, indent=2), file=sys.stderr)
        return 1

    try:
        schema = load_json(Path(args.schema))
        if args.packet_file:
            packet = load_json(Path(args.packet_file))
            source = str(args.packet_file)
        else:
            packet = json.loads(args.packet or "")
            source = "(inline)"
    except Exception as exc:
        failure = {
            "version": "1.0",
            "created_at": time.time(),
            "stage": "SEE_VALIDATION",
            "schema_validation": {"passed": False, "issues": [f"parse_error:{exc!r}"]},
            "web_run_evidence_validation": {"passed": False, "issues": []},
            "source_binding_validation": {"passed": False, "issues": []},
            "semantic_validation": {"passed": False, "issues": []},
            "verdict": "FAIL",
            "issues": [f"parse_error:{exc!r}"],
            "next_stage": "BLOCK_WITH_SEE_VALIDATION_RECEIPT",
        }
        try:
            receipt = write_receipt(failure, Path(args.receipt_dir), args.packet_file or "(inline)", args.schema)
            failure["receipt_path"] = str(receipt)
        except Exception:
            pass
        print(json.dumps(failure, indent=2), file=sys.stderr)
        return 2

    if not isinstance(packet, dict):
        failure = {"verdict": "FAIL", "issues": ["packet_not_object"]}
        print(json.dumps(failure, indent=2), file=sys.stderr)
        return 1

    result = validate_packet(packet, schema, strict=args.strict)

    try:
        receipt = write_receipt(result, Path(args.receipt_dir), source, args.schema)
    except Exception as exc:
        print(json.dumps({"verdict": "FAIL", "issues": [f"receipt_write_failed:{exc!r}"]}, indent=2), file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps({
            "verdict": result["verdict"],
            "issues": result["issues"],
            "receipt_path": str(receipt),
            "next_stage": result["next_stage"],
        }, indent=2))

    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
