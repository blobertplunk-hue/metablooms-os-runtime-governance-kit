#!/usr/bin/env python3
"""
Purpose: Enforce explicit stage_contains_code declarations on MPP stage contracts.
Inputs: JSON packet path describing a stage contract declaration.
Outputs: ALLOW/DENY JSON verdict with stable reason codes and inferred code classification.
Failure modes: missing JSON, missing explicit code flag, mismatch between code classes and flag, code-bearing stage without CDR requirement.
Debuggability: denial includes stage_id, effective inferred flag, code classes, and exact reason codes.
"""
import json, sys
from pathlib import Path

CODE_CLASSES={
    "python","javascript","typescript","html_js","shell","node","schema_driven_runtime",
    "validator","gate","policy","export_script","packaging_script","runtime_config",
    "html_activity","spreadsheet_macro","browser_extension","tampermonkey_script"
}
REQUIRED=["stage_id","stage_contains_code","code_artifact_classes","cdr_required","mpp_cdr_binding_policy_version","declaration_source","declared_by","stage_verdict_requested"]

def load_packet(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def evaluate(packet):
    reasons=[]
    missing=[k for k in REQUIRED if k not in packet]
    if missing:
        reasons.append("missing_required_fields:"+",".join(missing))
    stage_id=packet.get('stage_id','UNKNOWN')
    classes=set(packet.get('code_artifact_classes') or [])
    inferred=bool(classes & CODE_CLASSES)
    explicit=packet.get('stage_contains_code')
    cdr_required=packet.get('cdr_required')
    if explicit is not True and explicit is not False:
        reasons.append('stage_contains_code_not_explicit_boolean')
    if inferred and explicit is False:
        reasons.append('code_classes_require_stage_contains_code_true')
    effective = bool(explicit) or inferred
    if effective and cdr_required is not True:
        reasons.append('code_bearing_stage_requires_cdr_required_true')
    if effective and packet.get('stage_verdict_requested') == 'PASS' and not packet.get('cdr_binding_packet_path'):
        reasons.append('code_bearing_pass_requires_cdr_binding_packet_path')
    if packet.get('mpp_cdr_binding_policy_version') not in ('MPP_CODE_WORK_REQUIRES_CDR_v1','MPP_CDR_STAGE_CONTRACT_CODE_BEARING_POLICY_v1'):
        reasons.append('unknown_or_missing_policy_version')
    return {
        'schema':'MPP_CDR_STAGE_CONTRACT_CODE_BEARING_DECLARATION_GATE_RESULT_v1',
        'stage_id':stage_id,
        'verdict':'ALLOW' if not reasons else 'DENY',
        'reasons':reasons,
        'explicit_stage_contains_code':explicit,
        'inferred_code_bearing':inferred,
        'effective_stage_contains_code':effective,
        'code_artifact_classes':sorted(classes)
    }

def main(argv):
    if len(argv)!=2:
        print(json.dumps({'verdict':'DENY','reasons':['usage: gate packet.json']}, indent=2)); return 2
    try:
        result=evaluate(load_packet(argv[1]))
    except Exception as e:
        result={'schema':'MPP_CDR_STAGE_CONTRACT_CODE_BEARING_DECLARATION_GATE_RESULT_v1','verdict':'DENY','reasons':['exception:'+type(e).__name__],'detail':str(e)}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get('verdict')=='ALLOW' else 1
if __name__=='__main__':
    raise SystemExit(main(sys.argv))
