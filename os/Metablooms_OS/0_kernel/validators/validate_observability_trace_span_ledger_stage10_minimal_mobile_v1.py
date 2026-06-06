#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,subprocess,sys,time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE10_BOOT_SURFACE_MINIMAL_MODE_AND_MOBILE_RENDER_HARDENING'

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''):
            h.update(c)
    return h.hexdigest()

def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,obj):
    s=json.dumps(obj,indent=2,sort_keys=True)+'\n'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8'); Path(str(p)+'.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'  '+p.name+'\n',encoding='utf-8')
def run(cmd,cwd):
    cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=180)
    try: out=json.loads(cp.stdout) if cp.stdout.strip() else {}
    except Exception: out={'raw_stdout':cp.stdout}
    return {'cmd':cmd,'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); args=ap.parse_args(argv)
    root=Path(args.root).resolve(); issues=[]; checks=[]
    required=[
      '0_kernel/registry/observability/MB_BOOT_SURFACE_MINIMAL_MODE_SCHEMA_v1.json',
      '0_kernel/registry/observability/MB_BOOT_SURFACE_MINIMAL_MODE_POLICY_v1.json',
      '0_kernel/scripts/observability_boot_surface_minimal_mode_renderer_v1.py',
      'runtime/state/operator_surface/BOOT_SURFACE_MINIMAL_MODE_LATEST.json',
      'runtime/state/operator_surface/BOOT_SURFACE_MINIMAL_MODE_LATEST.md',
      'OPEN_OPERATOR_VISUAL_TRACKER.html'
    ]
    for rel in required:
        p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok,'sha256':sha(p) if ok else None})
        if not ok: issues.append('missing_or_empty:'+rel)
    if not issues:
        model=load(root/'runtime/state/operator_surface/BOOT_SURFACE_MINIMAL_MODE_LATEST.json')
        policy=load(root/'0_kernel/registry/observability/MB_BOOT_SURFACE_MINIMAL_MODE_POLICY_v1.json')
        html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
        if model.get('artifact_type')!='MB_BOOT_SURFACE_MINIMAL_MODE.v1': issues.append('bad_model_artifact_type')
        if model.get('verdict')!='PASS': issues.append('model_not_pass')
        if model.get('stage_id')!=STAGE: issues.append('model_stage_mismatch')
        cmd=model.get('primary_action',{}).get('command_or_path','')
        if 'runtime_starter_smoke_contract_wrapper_v1.py' not in cmd or '--root /mnt/data/Metablooms_OS' not in cmd: issues.append('primary_action_not_wrapper_named_root')
        if model.get('blocker_state',{}).get('active_blockers') != 0: issues.append('minimal_model_reports_active_blocker')
        for marker in policy.get('required_html_markers',[]):
            if marker not in html: issues.append('tracker_missing_marker:'+marker)
        for frag in policy.get('forbidden_minimal_mode_fragments',[]):
            if frag in html: issues.append('tracker_forbidden_fragment:'+frag)
        static_checks={
          'viewport_meta':"<meta name='viewport'" in html or '<meta name="viewport"' in html,
          'overflow_x_hidden':'overflow-x:hidden' in html,
          'touch_target_48':'min-height:48px' in html,
          'code_word_break':'word-break:break-word' in html and 'overflow-wrap:anywhere' in html,
          'single_column_breakpoint':'@media(max-width:760px)' in html and '@media(min-width:760px)' in html,
          'details_disclosure':'<details' in html and '<summary>' in html,
          'skip_link':'Skip to evidence' in html
        }
        for k,v in static_checks.items():
            checks.append({'name':'mobile_static:'+k,'passed':bool(v)})
            if not v: issues.append('mobile_static_missing:'+k)
        for rel in ['runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json','runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json','runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json']:
            if rel not in html: issues.append('tracker_missing_deep_source:'+rel)
        ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
        if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append('authority_pointer_copies_not_identical')
        if ptrs[0].get('stage_id')!=STAGE or ptrs[0].get('last_stage')!=STAGE: issues.append('pointer_not_stage10')
        for key in ['boot_surface_minimal_mode','boot_surface_minimal_mode_validation','boot_surface_minimal_mode_policy','boot_surface_minimal_mode_renderer']:
            if key not in ptrs[0]: issues.append('pointer_missing:'+key)
    smoke=[]
    for name,cmd in [
      ('renderer_passes',[sys.executable,str(root/'0_kernel/scripts/observability_boot_surface_minimal_mode_renderer_v1.py'),'--root',str(root),'--json']),
      ('new_chat_validator_allows',[sys.executable,str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'),str(root)]),
      ('runtime_wrapper_allows',[sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),'--root',str(root),'--json'])
    ]:
        res=run(cmd,root); passed=res['returncode']==0 and (res['stdout'].get('verdict') in ['PASS',None] or res['stdout'].get('decision') in ['ALLOW',None])
        smoke.append({'name':name,'pass':passed,'result':res})
        if not passed: issues.append('smoke_failed:'+name)
    report={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE10_MINIMAL_MOBILE_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke,'issues':issues}
    write(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE10_MINIMAL_MOBILE_VALIDATION_LATEST.json', report)
    print(json.dumps(report,indent=2,sort_keys=True)); return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
