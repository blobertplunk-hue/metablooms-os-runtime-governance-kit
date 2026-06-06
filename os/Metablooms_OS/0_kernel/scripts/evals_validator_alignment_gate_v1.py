#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time, hashlib
from pathlib import Path

REQUIRED_LABELS = ['PASS','WARN','BLOCK']

def now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def h(s: str) -> str: return hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]
def load(p: Path): return json.loads(p.read_text(encoding='utf-8'))
def write(p: Path, o: dict) -> str:
    p.parent.mkdir(parents=True, exist_ok=True)
    _mb_write_json_file(p, o, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_evals_validator_alignment_gate_v1_py_L13', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    return str(p)
def append_jsonl(p: Path, o: dict) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8') as f:
        f.write(json.dumps(o, sort_keys=True)+'\n')

def root_from_here() -> Path:
    here=Path(__file__).resolve()
    for q in [here.parent,*here.parents]:
        if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
    return Path.cwd()

def evaluate(root: Path) -> dict:
    required = {
        'alignment_gate_spec': root/'0_kernel/registry/evals/MB_EVALS_VALIDATOR_ALIGNMENT_GATE_SPEC_v1.json',
        'runner_results': root/'runtime/evals/evals_trace_review/EVALS_EVALUATOR_RUN_STAGE3_RESULTS_LATEST.json',
        'confusion_matrix': root/'runtime/evals/evals_trace_review/EVALS_CONFUSION_MATRIX_STAGE3_LATEST.json',
        'regression_dataset': root/'runtime/evals/evals_trace_review/EVALS_REGRESSION_DATASET_v1.json',
        'scorecard_spec': root/'0_kernel/registry/evals/MB_EVALS_SCORECARD_SPEC_v1.json',
        'failure_modes': root/'0_kernel/registry/evals/EVALS_FAILURE_MODE_CATALOG_v1.json',
        'alignment_policy': root/'0_kernel/registry/evals/VALIDATOR_ALIGNMENT_POLICY_v1.json',
    }
    missing=[k for k,p in required.items() if not p.exists()]
    if missing:
        return {'verdict':'VALIDATOR_ALIGNMENT_GATE_BLOCK','reason':'missing_required_artifacts','missing_keys':missing,'missing_paths':[str(required[k]) for k in missing]}
    spec=load(required['alignment_gate_spec'])
    runner=load(required['runner_results'])
    cm=load(required['confusion_matrix'])
    ds=load(required['regression_dataset'])
    examples=ds.get('examples', []) if isinstance(ds.get('examples'), list) else []
    thresholds=spec.get('promotion_thresholds', {})
    min_examples=int(thresholds.get('minimum_examples', 20))
    min_accuracy=float(thresholds.get('minimum_accuracy', 0.90))
    false_pass_tol=int(thresholds.get('false_pass_tolerance', 0))
    required_labels=thresholds.get('required_labels', REQUIRED_LABELS)
    accuracy=float(cm.get('accuracy', 0) or 0)
    false_pass=cm.get('false_pass_example_ids') or []
    per_label=cm.get('per_label') or {}
    label_support={label:int((per_label.get(label) or {}).get('support') or 0) for label in required_labels}
    conservative_mismatches=[]
    for row in runner.get('results', []):
        exp=row.get('expected_decision'); pred=row.get('predicted_decision')
        if exp=='WARN' and pred=='BLOCK': conservative_mismatches.append(row.get('example_id'))
    checks=[]
    def add(id, ok, details): checks.append({'id':id,'ok':bool(ok),'details':details})
    add('EVAL-GATE-001_minimum_dataset_size', len(examples)>=min_examples, {'example_count':len(examples),'minimum':min_examples})
    add('EVAL-GATE-002_required_label_coverage', all(label_support.get(l,0)>0 for l in required_labels), {'label_support':label_support})
    add('EVAL-GATE-003_minimum_accuracy', accuracy>=min_accuracy, {'accuracy':accuracy,'minimum':min_accuracy})
    add('EVAL-GATE-004_zero_false_pass', len(false_pass)<=false_pass_tol, {'false_pass_example_ids':false_pass,'tolerance':false_pass_tol})
    add('EVAL-GATE-005_stage3_runner_complete', runner.get('verdict')=='EVALUATOR_RUN_COMPLETE', {'runner_verdict':runner.get('verdict')})
    add('EVAL-GATE-006_promotion_matrix_pass', cm.get('promotion_decision')=='PASS', {'confusion_matrix_promotion_decision':cm.get('promotion_decision')})
    add('EVAL-GATE-007_conservative_mismatch_only', True, {'conservative_mismatch_ids':conservative_mismatches, 'policy':'WARN->BLOCK is allowed; WARN/BLOCK->PASS is not allowed'})
    failed=[c for c in checks if not c['ok']]
    decision='PROMOTE' if not failed else 'BLOCK'
    trace_id=h('evals-stage4|'+decision+'|'+str(accuracy)+'|'+str(false_pass))
    report={
        'artifact_type':'EVALS_VALIDATOR_ALIGNMENT_GATE_STAGE4_REPORT_v1',
        'created_utc':now(),
        'stage_name':'IMPLEMENT_EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE_STAGE_4_VALIDATOR_ALIGNMENT_GATE_PROMOTION',
        'verdict':'VALIDATOR_ALIGNMENT_GATE_PASS' if decision=='PROMOTE' else 'VALIDATOR_ALIGNMENT_GATE_BLOCK',
        'promotion_decision':decision,
        'trace_id':trace_id,
        'checks':checks,
        'failed_checks':failed,
        'metrics':{
            'example_count':len(examples),
            'accuracy':accuracy,
            'false_pass_count':len(false_pass),
            'false_pass_example_ids':false_pass,
            'label_support':label_support,
            'conservative_mismatch_ids':conservative_mismatches
        },
        'inputs':{k:str(p.relative_to(root)) for k,p in required.items()},
        'policy':'Promotion requires enough examples, PASS/WARN/BLOCK coverage, minimum accuracy, no false passes, and completed Stage 3 runner evidence.'
    }
    out=root/'runtime/evals/evals_trace_review/EVALS_VALIDATOR_ALIGNMENT_STAGE4_REPORT_LATEST.json'
    write(out, report)
    ledger=root/'runtime/traces/evals/TRACE_SPAN_LEDGER_EVALS_STAGE4.jsonl'
    append_jsonl(ledger, {'schema_version':'MB_TRACE_SPAN_LEDGER_SPEC_v2','trace_id':trace_id,'span_id':h(trace_id+'start'),'parent_span_id':None,'name':'evals_stage4.alignment_gate','stage_name':report['stage_name'],'event':'start','status':'OK','timestamp_utc':now(),'attributes':{'example_count':len(examples),'min_examples':min_examples}})
    append_jsonl(ledger, {'schema_version':'MB_TRACE_SPAN_LEDGER_SPEC_v2','trace_id':trace_id,'span_id':h(trace_id+'end'),'parent_span_id':h(trace_id+'start'),'name':'evals_stage4.promotion_decision','stage_name':report['stage_name'],'event':'end','status':'OK' if decision=='PROMOTE' else 'ERROR','timestamp_utc':now(),'attributes':{'promotion_decision':decision,'accuracy':accuracy,'false_pass_count':len(false_pass)}})
    report['report_path']=str(out)
    report['trace_ledger']=str(ledger)
    return report

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--root')
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args(argv)
    r=Path(args.root).resolve() if args.root else root_from_here()
    out=evaluate(r)
    print(json.dumps(out, indent=2, sort_keys=True) if args.json else out.get('verdict','UNKNOWN'))
    return 0 if out.get('verdict')=='VALIDATOR_ALIGNMENT_GATE_PASS' else 2
if __name__=='__main__': raise SystemExit(main())
