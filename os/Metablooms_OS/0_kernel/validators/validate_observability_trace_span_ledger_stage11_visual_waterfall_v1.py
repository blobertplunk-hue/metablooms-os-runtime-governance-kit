#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,subprocess,sys,time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE11_VISUAL_TRACE_WATERFALL_AND_EVIDENCE_FILTERS'
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,obj):
    s=json.dumps(obj,indent=2,sort_keys=True)+'\n'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8'); Path(str(p)+'.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'  '+p.name+'\n',encoding='utf-8')
def run(cmd,cwd):
    cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=240)
    try: out=json.loads(cp.stdout) if cp.stdout.strip() else {}
    except Exception: out={'raw_stdout':cp.stdout}
    return {'cmd':cmd,'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); args=ap.parse_args(argv)
    root=Path(args.root).resolve(); issues=[]; checks=[]
    required=['0_kernel/registry/observability/MB_VISUAL_TRACE_WATERFALL_EVIDENCE_FILTERS_SCHEMA_v1.json','0_kernel/registry/observability/MB_VISUAL_TRACE_WATERFALL_EVIDENCE_FILTERS_POLICY_v1.json','0_kernel/scripts/observability_visual_trace_waterfall_renderer_v1.py','runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.json','runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.md','OPEN_OPERATOR_VISUAL_TRACKER.html']
    for rel in required:
        p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok,'sha256':sha(p) if ok else None})
        if not ok: issues.append('missing_or_empty:'+rel)
    if not issues:
        model=load(root/'runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.json')
        policy=load(root/'0_kernel/registry/observability/MB_VISUAL_TRACE_WATERFALL_EVIDENCE_FILTERS_POLICY_v1.json')
        html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
        if model.get('artifact_type')!='MB_VISUAL_TRACE_WATERFALL_EVIDENCE_FILTERS.v1': issues.append('bad_model_artifact_type')
        if model.get('stage_id')!=STAGE: issues.append('model_stage_mismatch')
        if model.get('verdict')!='PASS': issues.append('model_not_pass')
        if len(model.get('waterfall_rows',[])) < 8: issues.append('too_few_waterfall_rows')
        if not model.get('mode_policy',{}).get('minimal_mode_default'): issues.append('minimal_mode_not_default')
        for f in ['all','issues','validators','exports','receipts','handoffs','boot']:
            if f not in model.get('filters',{}).get('quick_filters',[]): issues.append('missing_filter:'+f)
        for marker in policy.get('required_html_markers',[]):
            if marker not in html: issues.append('tracker_missing_marker:'+marker)
        for marker in ['mode-minimal','mode-evidence','applyFilter','data-status=','data-kind=','water-line','evidence-link','overflow-x:hidden','min-height:48px','word-break:break-word','overflow-wrap:anywhere']:
            if marker not in html: issues.append('tracker_missing_static:'+marker)
        for src in ['TRACE_SPAN_LEDGER_LATEST.jsonl','TRACE_SPAN_LEDGER_INDEX_LATEST.json','CAUSAL_STAGE_GRAPH_LATEST.json']:
            if src not in json.dumps(model) and src not in html: issues.append('missing_source_binding:'+src)
        ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
        if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append('authority_pointer_copies_not_identical')
        if ptrs[0].get('stage_id')!=STAGE or ptrs[0].get('last_stage')!=STAGE: issues.append('pointer_not_stage11')
        for key in ['visual_trace_waterfall','visual_trace_waterfall_validation','visual_trace_waterfall_policy','visual_trace_waterfall_renderer']:
            if key not in ptrs[0]: issues.append('pointer_missing:'+key)
    smoke=[]
    for name,cmd in [('renderer_passes',[sys.executable,str(root/'0_kernel/scripts/observability_visual_trace_waterfall_renderer_v1.py'),'--root',str(root),'--json']),('new_chat_validator_allows',[sys.executable,str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'),str(root)]),('runtime_wrapper_allows',[sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),'--root',str(root),'--json'])]:
        res=run(cmd,root); stdout=res.get('stdout') or {}; passed=res['returncode']==0 and (stdout.get('verdict') in ['PASS',None] or stdout.get('decision') in ['ALLOW',None])
        smoke.append({'name':name,'pass':passed,'result':res})
        if not passed: issues.append('smoke_failed:'+name)
    report={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE11_VISUAL_WATERFALL_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke,'issues':issues}
    write(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE11_VISUAL_WATERFALL_VALIDATION_LATEST.json', report)
    print(json.dumps(report,indent=2,sort_keys=True)); return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
