#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time
from pathlib import Path

def find_root():
    p=Path(__file__).resolve()
    for q in [p.parent,*p.parents]:
        if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
    return Path.cwd()

def load(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))

def main():
    root=find_root(); issues=[]; warnings=[]
    paths={
      'scorecard_spec': root/'0_kernel/registry/evals/MB_EVALS_SCORECARD_SPEC_v1.json',
      'regression_dataset': root/'runtime/evals/evals_trace_review/EVALS_REGRESSION_DATASET_v1.json',
      'failure_mode_catalog': root/'0_kernel/registry/evals/EVALS_FAILURE_MODE_CATALOG_v1.json',
      'baseline': root/'runtime/evals/evals_trace_review/EVALS_SCORECARD_BASELINE_v1.json',
      'stage1_spec': root/'0_kernel/registry/evals/MB_EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_SPEC_v1.json'
    }
    for k,p in paths.items():
        if not p.exists(): issues.append({'path':str(p),'reason':f'{k}_missing'})
    if issues:
        print(json.dumps({'verdict':'FAIL','issues':issues},indent=2,sort_keys=True)); return 2
    sc=load(paths['scorecard_spec']); ds=load(paths['regression_dataset']); cat=load(paths['failure_mode_catalog']); base=load(paths['baseline'])
    scorecards=sc.get('scorecards',[]); examples=ds.get('examples',[]); modes=cat.get('failure_modes',[])
    if len(scorecards) < 6: issues.append({'reason':'scorecard_count_below_6','count':len(scorecards)})
    if len(examples) < 20: issues.append({'reason':'regression_dataset_below_20','count':len(examples)})
    if len(examples) > 50: warnings.append({'reason':'manual_review_batch_above_50','count':len(examples)})
    decisions=sorted(set(e.get('expected_decision') for e in examples))
    for required in ['PASS','WARN','BLOCK']:
        if required not in decisions: issues.append({'reason':'missing_required_decision','decision':required})
    scorecard_ids={c.get('scorecard_id') for c in scorecards}
    for e in examples:
        if not e.get('example_id'): issues.append({'reason':'example_missing_id','example':e})
        if e.get('expected_decision') not in ['PASS','WARN','BLOCK']: issues.append({'reason':'bad_expected_decision','example_id':e.get('example_id')})
        scores=e.get('expected_scorecard_scores',{})
        if not isinstance(scores,dict) or not scores: issues.append({'reason':'missing_scorecard_scores','example_id':e.get('example_id')})
        for sid,val in scores.items():
            if sid not in scorecard_ids: issues.append({'reason':'unknown_scorecard_id','example_id':e.get('example_id'),'scorecard_id':sid})
            if val not in [0,1,2]: issues.append({'reason':'score_out_of_range','example_id':e.get('example_id'),'scorecard_id':sid,'score':val})
    mode_ids={m.get('failure_mode_id') for m in modes}
    covered={fm for e in examples for fm in e.get('failure_mode_ids',[])}
    missing_modes=sorted(mode_ids-covered)
    if missing_modes: issues.append({'reason':'failure_modes_not_covered','missing':missing_modes})
    block_false_success=[e.get('example_id') for e in examples if e.get('expected_decision')=='BLOCK' and all(v>0 for v in e.get('expected_scorecard_scores',{}).values())]
    if block_false_success: warnings.append({'reason':'block_examples_have_no_zero_score','example_ids':block_false_success[:10]})
    if base.get('example_count') != len(examples): issues.append({'reason':'baseline_example_count_mismatch','baseline':base.get('example_count'),'actual':len(examples)})
    out={
      'artifact_type':'EVALS_SCORECARDS_STAGE2_VALIDATION_v1',
      'created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),
      'verdict':'PASS' if not issues else 'FAIL',
      'root':str(root),
      'scorecard_count':len(scorecards),
      'example_count':len(examples),
      'decision_counts':{d:sum(1 for e in examples if e.get('expected_decision')==d) for d in ['PASS','WARN','BLOCK']},
      'failure_mode_count':len(modes),
      'failure_mode_coverage_count':len(covered),
      'issues':issues,
      'warnings':warnings,
      'paths':{k:str(v) for k,v in paths.items()}
    }
    outp=root/'runtime/evals/evals_trace_review/EVALS_SCORECARDS_STAGE2_VALIDATION_LATEST.json'
    outp.parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(outp, out, operation_id='STAGE4_ATOMIC_JSON_0_kernel_validators_validate_evals_scorecards_stage2_v1_py_L67', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    out['validation_path']=str(outp)
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
