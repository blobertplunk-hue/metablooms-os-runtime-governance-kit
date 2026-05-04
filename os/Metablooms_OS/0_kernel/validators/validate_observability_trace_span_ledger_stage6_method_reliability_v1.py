#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys, hashlib, time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE6_METHOD_RELIABILITY_LEDGER_AND_SUPPRESSED_FAILURE_LESSON_BINDING'
def sha_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
    return h.hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def exists(root, rel):
    p=root/rel
    return {'path':rel,'exists_nonempty':p.exists() and p.stat().st_size>0,'sha256':sha_file(p) if p.exists() and p.is_file() else None}
def run_wrapper(root:Path, args:list[str]):
    p=root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'
    cp=subprocess.run([sys.executable, str(p), *args], cwd=str(root), text=True, capture_output=True, timeout=20)
    try: out=json.loads(cp.stdout)
    except Exception: out={'parse_error':cp.stdout,'stderr':cp.stderr}
    return {'argv':args,'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true'); args=ap.parse_args(argv)
    root=Path(args.root).resolve(); issues=[]; checks=[]
    required=['0_kernel/registry/observability/MB_METHOD_RELIABILITY_LEDGER_POLICY_v1.json','0_kernel/registry/observability/METHOD_RELIABILITY_LESSON_RUNTIME_STARTER_SMOKE_CLI_SHAPE_v1.json','runtime/traces/observability/METHOD_RELIABILITY_LEDGER_LATEST.json','runtime/traces/observability/METHOD_RELIABILITY_ROUTER_UPDATE_LATEST.json','runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py','runtime/fixtures/observability/method_reliability_stage6/SHA256SUMS.txt','runtime/state/operator_surface/OPERATOR_METHOD_RELIABILITY_SUMMARY_LATEST.json','OPEN_OPERATOR_VISUAL_TRACKER.html']
    for r in required:
        c=exists(root,r); checks.append(c)
        if not c['exists_nonempty']: issues.append('missing_or_empty:'+r)
    if not issues:
        ledger=load(root/'runtime/traces/observability/METHOD_RELIABILITY_LEDGER_LATEST.json')
        lesson=load(root/'0_kernel/registry/observability/METHOD_RELIABILITY_LESSON_RUNTIME_STARTER_SMOKE_CLI_SHAPE_v1.json')
        update=load(root/'runtime/traces/observability/METHOD_RELIABILITY_ROUTER_UPDATE_LATEST.json')
        records=ledger.get('method_records',[])
        if ledger.get('artifact_type')!='MB_METHOD_RELIABILITY_LEDGER.v1': issues.append('bad_ledger_artifact_type')
        if len(records)!=1: issues.append('expected_one_method_record')
        else:
            r=records[0]
            if r.get('failure_class')!='cli_invocation_or_amended_receipt_superseded': issues.append('missing_cli_failure_class')
            if 'runtime_starter_smoke_contract_wrapper_v1.py' not in r.get('replacement_wrapper',''): issues.append('missing_wrapper_replacement')
            if not r.get('evidence_refs'): issues.append('missing_evidence_refs')
            if r.get('recommended_decision')!='PROMOTE': issues.append('method_not_promoted')
        if lesson.get('status')!='SUPPRESSED_LESSON_BOUND': issues.append('lesson_not_bound')
        if update.get('verdict')!='PASS': issues.append('router_update_not_pass')
        html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
        if 'data-section="method_reliability_ledger"' not in html: issues.append('tracker_missing_method_reliability_section')
    correct=run_wrapper(root,['--root',str(root),'--json'])
    wrong=run_wrapper(root,[str(root),'--json'])
    missing=run_wrapper(root,['--json'])
    fixture_results=[
        {'fixture':'correct_named_root','expected':'ALLOW','actual':correct['stdout'].get('decision'),'pass':correct['stdout'].get('decision')=='ALLOW' and correct['returncode']==0},
        {'fixture':'wrong_positional_root','expected':'DENY','actual':wrong['stdout'].get('decision'),'error_code':wrong['stdout'].get('error_code'),'pass':wrong['stdout'].get('decision')=='DENY' and wrong['stdout'].get('error_code')=='MB_CLI_CONTRACT_DENY_POSITIONAL_ARGS'},
        {'fixture':'missing_target','expected':'DENY','actual':missing['stdout'].get('decision'),'error_code':missing['stdout'].get('error_code'),'pass':missing['stdout'].get('decision')=='DENY' and missing['stdout'].get('error_code')=='MB_CLI_CONTRACT_DENY_EXACTLY_ONE_TARGET'}]
    for fr in fixture_results:
        if not fr['pass']: issues.append('fixture_failed:'+fr['fixture'])
    report={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE6_METHOD_RELIABILITY_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'fixture_results':fixture_results,'issues':issues}
    out=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE6_METHOD_RELIABILITY_VALIDATION_LATEST.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    text=json.dumps(report, indent=2, sort_keys=True)+'\n'; out.write_text(text, encoding='utf-8'); out.with_suffix(out.suffix+'.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+out.name+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
