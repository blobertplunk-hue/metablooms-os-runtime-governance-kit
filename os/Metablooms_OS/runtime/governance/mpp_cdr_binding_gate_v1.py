#!/usr/bin/env python3
"""
Purpose: Enforce that MPP cannot accept code-bearing work unless CDR passes.
Inputs: JSON packet path or JSON object describing MPP/CDR binding evidence.
Outputs: ALLOW/DENY JSON verdict with machine-readable reasons.
Failure modes: missing packet, invalid JSON, code work without CDR, code work with failed CDR, missing CDR evidence.
Debuggability: every denial includes stable reason codes under `reasons` and the inspected stage_id.
"""
import json, sys
from pathlib import Path

REQUIRED_EVIDENCE = [
    "cdr_packet_path", "cdr_gate_path", "cdr_eval_path", "cdr_gate_sha256",
    "code_acceptance_dimensions", "risk_tier", "test_summary"
]
CODE_CLASSES = {
    "python", "javascript", "typescript", "html_js", "shell", "node",
    "schema_driven_runtime", "validator", "gate", "policy", "export_script",
    "packaging_script", "runtime_config"
}

def load_packet(arg):
    if isinstance(arg, dict):
        return arg
    p = Path(arg)
    return json.loads(p.read_text(encoding="utf-8"))

def evaluate(packet):
    reasons=[]
    stage_id = packet.get("stage_id", "UNKNOWN")
    contains_code = bool(packet.get("stage_contains_code"))
    classes = set(packet.get("code_artifact_classes") or [])
    inferred_code = bool(classes & CODE_CLASSES)
    if inferred_code and not contains_code:
        reasons.append("stage_contains_code_false_but_code_classes_present")
        contains_code = True
    if packet.get("mpp_compliance_claimed") is not True:
        reasons.append("mpp_compliance_not_claimed")
    cdr = packet.get("cdr_gate_result") or {}
    cdr_evidence = packet.get("cdr_evidence") or {}
    if contains_code:
        if cdr.get("verdict") != "PASS":
            reasons.append("code_work_requires_cdr_pass")
        missing=[k for k in REQUIRED_EVIDENCE if not cdr_evidence.get(k)]
        if missing:
            reasons.append("missing_cdr_evidence:"+",".join(missing))
        dims = cdr_evidence.get("code_acceptance_dimensions") or []
        required_dims = {"correctness","completeness","comprehensibility","debuggability","adaptability","security","observability","testability","integration","regression_resistance","recursive_improvement"}
        if not required_dims.issubset(set(dims)):
            reasons.append("incomplete_cdr_dimension_coverage")
        if packet.get("stage_verdict_requested") == "PASS" and reasons:
            reasons.append("pass_requested_despite_cdr_binding_failure")
    verdict = "ALLOW" if not reasons else "DENY"
    return {"schema":"MPP_CDR_BINDING_GATE_RESULT_v1","stage_id":stage_id,"verdict":verdict,"reasons":reasons,"stage_contains_code_effective":contains_code}

def main(argv):
    if len(argv) != 2:
        print(json.dumps({"verdict":"DENY","reasons":["usage: gate packet.json"]}, indent=2)); return 2
    try:
        packet = load_packet(argv[1])
        result = evaluate(packet)
    except Exception as e:
        result = {"schema":"MPP_CDR_BINDING_GATE_RESULT_v1","verdict":"DENY","reasons":["exception:"+type(e).__name__],"detail":str(e)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("verdict") == "ALLOW" else 1
if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
