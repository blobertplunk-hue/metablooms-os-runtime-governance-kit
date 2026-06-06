#!/usr/bin/env python3
"""CDR gate module: cdr_adaptability_interface_contract_gate_v1.py.

Purpose:
    Enforce Coding Done Right adaptability and interface-contract requirements.
Inputs:
    Path to a CDRAdaptabilityInterfaceContractPacket_v1 JSON packet.
Outputs:
    JSON ALLOW or DENY result with machine-readable reasons; nonzero exit on DENY.
Failure modes:
    Missing interface contracts, missing compatibility/deprecation policy, missing change-impact proof, missing negative fixtures, or unstable authority-critical interfaces produce DENY.
Debuggability:
    Each denial reason identifies the exact interface_id or evidence group that failed.
"""
import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "interface_id", "owner_module", "version", "stability", "purpose", "inputs",
    "outputs", "error_contract", "side_effects", "security_boundary",
    "observability_contract", "compatibility_policy", "extension_points",
    "deprecation_policy", "migration_notes", "examples", "test_evidence",
]
STABLE_LEVELS = {"stable", "authority_critical"}
VALID_STABILITY = {"experimental", "internal", "stable", "authority_critical"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _empty(value):
    return value in (None, "", [], {})


def evaluate(packet):
    reasons = []
    warnings = []
    if packet.get("schema") != "CDRAdaptabilityInterfaceContractPacket_v1":
        reasons.append("bad_schema")
    changed = packet.get("changed_modules") or []
    if not changed:
        reasons.append("changed_modules_missing")
    contracts = packet.get("interface_contracts") or []
    no_change = packet.get("no_interface_change_proof") or {}
    if not contracts and no_change.get("verdict") != "NO_INTERFACE_CHANGE":
        reasons.append("missing_interface_contract_or_no_change_proof")
    for contract in contracts:
        iid = contract.get("interface_id", "UNKNOWN_INTERFACE")
        for field in REQUIRED_FIELDS:
            if field not in contract or _empty(contract.get(field)):
                reasons.append(f"interface_missing_required_field:{iid}:{field}")
        stability = contract.get("stability")
        if stability not in VALID_STABILITY:
            reasons.append(f"invalid_stability:{iid}:{stability}")
        if stability in STABLE_LEVELS:
            compat = contract.get("compatibility_policy") or {}
            if compat.get("backward_compatibility") not in {"preserved", "breaking_with_migration", "not_applicable_with_reason"}:
                reasons.append(f"stable_interface_missing_backward_compatibility_decision:{iid}")
            deprecation = contract.get("deprecation_policy") or {}
            if deprecation.get("policy") not in {"not_deprecated", "deprecation_notice_required", "breaking_change_requires_handoff_and_hitl"}:
                reasons.append(f"stable_interface_missing_deprecation_policy:{iid}")
            migration = contract.get("migration_notes") or {}
            if not migration.get("consumer_impact"):
                reasons.append(f"stable_interface_missing_consumer_impact:{iid}")
        tests = contract.get("test_evidence") or []
        test_kinds = {item.get("kind") for item in tests if isinstance(item, dict)}
        if "positive_interface" not in test_kinds:
            reasons.append(f"missing_positive_interface_test:{iid}")
        if "negative_interface" not in test_kinds:
            reasons.append(f"missing_negative_interface_test:{iid}")
        if contract.get("extension_points") and not any(isinstance(x, dict) and x.get("proof") for x in contract.get("extension_points", [])):
            reasons.append(f"extension_point_without_proof:{iid}")
    checks = packet.get("adaptability_checks") or {}
    required_checks = ["change_impact_analysis", "compatibility_assessment", "migration_or_deprecation_assessment", "extension_point_assessment"]
    for check in required_checks:
        if checks.get(check) != "PASS":
            reasons.append(f"adaptability_check_not_PASS:{check}")
    fixtures = packet.get("fixture_evidence") or []
    evals = packet.get("eval_evidence") or []
    if len(fixtures) < 2:
        reasons.append("fixture_evidence_minimum_not_met")
    if not any(isinstance(x, dict) and x.get("kind") == "negative" for x in fixtures):
        reasons.append("negative_fixture_missing")
    if not evals:
        reasons.append("eval_evidence_missing")
    return {"verdict": "DENY" if reasons else "ALLOW", "reasons": reasons, "warnings": warnings}


def main(argv):
    if len(argv) != 2:
        print(json.dumps({"verdict":"DENY","reasons":["usage: cdr_adaptability_interface_contract_gate_v1.py <packet.json>"]}, indent=2))
        return 2
    result = evaluate(load(argv[1]))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["verdict"] == "ALLOW" else 1

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
