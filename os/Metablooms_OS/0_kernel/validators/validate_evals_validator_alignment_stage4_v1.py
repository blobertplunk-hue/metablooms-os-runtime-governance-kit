#!/usr/bin/env python3
from __future__ import annotations

# MetaBlooms Stage4 bounded subprocess enforcement shim.
from pathlib import Path as _MBPath
import sys as _MBSys
_MB_SELF = _MBPath(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_EXEC_LIB = _MB_PARENT / "0_kernel" / "lib" / "execution"
    if (_MB_EXEC_LIB / "bounded_subprocess_compat_v1.py").exists():
        if str(_MB_EXEC_LIB) not in _MBSys.path:
            _MBSys.path.insert(0, str(_MB_EXEC_LIB))
        break
from bounded_subprocess_compat_v1 import run as bounded_subprocess_run
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
    proc=bounded_subprocess_run(['python3','-S',str(gate),'--json'],cwd=str(r),text=True,capture_output=True,timeout=90)
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
    out_path.parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(out_path, out, operation_id='STAGE4_ATOMIC_JSON_0_kernel_validators_validate_evals_validator_alignment_stage4_v1_py_L51', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
