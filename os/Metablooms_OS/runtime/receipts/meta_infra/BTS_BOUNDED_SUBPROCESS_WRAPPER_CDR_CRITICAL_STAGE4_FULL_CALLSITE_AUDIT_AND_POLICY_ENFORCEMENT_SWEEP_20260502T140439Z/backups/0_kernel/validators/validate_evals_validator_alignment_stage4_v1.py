#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def root():
    here=Path(__file__).resolve()
    for q in [here.parent,*here.parents]:
        if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
    return Path.cwd()

def load(p): return json.loads(p.read_text(encoding='utf-8'))

def main():
    r=root()
    required=[
        '0_kernel/registry/evals/MB_EVALS_VALIDATOR_ALIGNMENT_GATE_SPEC_v1.json',
        '0_kernel/scripts/evals_validator_alignment_gate_v1.py',
        'runtime/evals/evals_trace_review/EVALS_EVALUATOR_RUN_STAGE3_RESULTS_LATEST.json',
        'runtime/evals/evals_trace_review/EVALS_CONFUSION_MATRIX_STAGE3_LATEST.json',
        'runtime/evals/evals_trace_review/EVALS_REGRESSION_DATASET_v1.json',
    ]
    missing=[p for p in required if not (r/p).exists()]
    if missing:
        print(json.dumps({'verdict':'FAIL','missing':missing},indent=2)); return 2
    gate=r/'0_kernel/scripts/evals_validator_alignment_gate_v1.py'
    proc=subprocess.run(['python3','-S',str(gate),'--json'],cwd=str(r),text=True,capture_output=True,timeout=90)
    try: payload=json.loads(proc.stdout)
    except Exception: payload={'parse_error':True,'stdout_tail':proc.stdout[-2000:],'stderr_tail':proc.stderr[-1000:]}
    issues=[]
    if proc.returncode!=0: issues.append('alignment_gate_returncode_nonzero')
    if payload.get('verdict')!='VALIDATOR_ALIGNMENT_GATE_PASS': issues.append('alignment_gate_not_pass')
    if payload.get('promotion_decision')!='PROMOTE': issues.append('promotion_decision_not_promote')
    metrics=payload.get('metrics',{}) if isinstance(payload,dict) else {}
    if metrics.get('false_pass_count') != 0: issues.append('false_pass_count_nonzero')
    if (metrics.get('example_count') or 0) < 20: issues.append('insufficient_regression_examples')
    out={'artifact_type':'EVALS_VALIDATOR_ALIGNMENT_STAGE4_VALIDATION_v1','verdict':'PASS' if not issues else 'FAIL','issues':issues,'gate_payload':payload}
    out_path=r/'runtime/evals/evals_trace_review/EVALS_VALIDATOR_ALIGNMENT_STAGE4_VALIDATION_LATEST.json'
    out_path.parent.mkdir(parents=True,exist_ok=True); out_path.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
