#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,subprocess,sys,time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE13_EVIDENCE_QUERY_UI_INTERACTIONS_AND_RESULT_PINNING'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,o):
 s=json.dumps(o,indent=2,sort_keys=True)+'\n'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8'); Path(str(p)+'.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'  '+p.name+'\n',encoding='utf-8')
def run(cmd,cwd):
 cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=240)
 try: out=json.loads(cp.stdout) if cp.stdout.strip() else {}
 except Exception: out={'raw_stdout':cp.stdout}
 return {'cmd':[str(x) for x in cmd],'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); root=Path(a.root).resolve(); issues=[]; checks=[]
 req=['0_kernel/registry/observability/MB_EVIDENCE_QUERY_UI_INTERACTION_SCHEMA_v1.json','0_kernel/registry/observability/MB_EVIDENCE_RESULT_PINNING_SCHEMA_v1.json','0_kernel/registry/observability/MB_EVIDENCE_PINNING_POLICY_v1.json','0_kernel/scripts/render_evidence_query_interactions_v1.py','runtime/state/operator_surface/EVIDENCE_QUERY_UI_INTERACTIONS_LATEST.json','runtime/state/operator_surface/EVIDENCE_QUERY_UI_INTERACTIONS_LATEST.md','runtime/state/operator_surface/EVIDENCE_RESULT_PINNING_MODEL_LATEST.json','runtime/state/operator_surface/EVIDENCE_RESULT_PINNING_MODEL_LATEST.md','runtime/traces/observability/SEARCHABLE_EVIDENCE_INDEX_LATEST.json','runtime/state/operator_surface/TRACE_QUERY_PACKET_LATEST.json','OPEN_OPERATOR_VISUAL_TRACKER.html']
 for rel in req:
  p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok,'sha256':sha(p) if ok else None})
  if not ok: issues.append('missing_or_empty:'+rel)
 if not issues:
  ui=load(root/'runtime/state/operator_surface/EVIDENCE_QUERY_UI_INTERACTIONS_LATEST.json'); pins=load(root/'runtime/state/operator_surface/EVIDENCE_RESULT_PINNING_MODEL_LATEST.json'); html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
  if ui.get('artifact_type')!='MB_EVIDENCE_QUERY_UI_INTERACTIONS.v1': issues.append('bad_ui_artifact_type')
  if pins.get('artifact_type')!='MB_EVIDENCE_RESULT_PINNING_MODEL.v1': issues.append('bad_pin_artifact_type')
  if ui.get('stage_id')!=STAGE or pins.get('stage_id')!=STAGE: issues.append('stage_id_mismatch')
  if len(ui.get('queries',[]))<6: issues.append('too_few_interactive_queries')
  for q in ui.get('queries',[]):
   if not q.get('results'): issues.append('interactive_query_no_results:'+str(q.get('query_id')))
   for r in q.get('results',[]):
    if not r.get('path') or not r.get('sha256'): issues.append('result_missing_path_or_sha:'+str(r.get('pin_id')))
  markers=["data-section=\'evidence_query_interactions\'","data-section=\'evidence_result_pinning\'","id=\'pin-tray\'","data-action=\'pin-result\'","function pinEvidence","function toggleQuery","function copyPinnedManifest","localStorage","stage13-pin-seed","pin-manifest"]
  for m in markers:
   if m not in html: issues.append('tracker_missing_marker:'+m)
  if 'mode-minimal' not in html or 'data-section="boot_surface_minimal_mode"' not in html: issues.append('minimal_mode_not_preserved')
  ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
  if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append('authority_pointer_copies_not_identical')
  if ptrs[0].get('stage_id')!=STAGE or ptrs[0].get('last_stage')!=STAGE: issues.append('pointer_not_stage13')
  for key in ['evidence_query_ui_interactions','evidence_result_pinning_model','evidence_pinning_policy','evidence_query_ui_validation']:
   if key not in ptrs[0]: issues.append('pointer_missing:'+key)
 smoke=[]
 for name,cmd in [('new_chat_validator',[sys.executable,str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'),str(root)]),('runtime_wrapper',[sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),'--root',str(root),'--json']),('query_indexer',[sys.executable,str(root/'0_kernel/scripts/observability_trace_query_indexer_v1.py'),'--root',str(root),'--query','pinned evidence export proof','--json'])]:
  res=run(cmd,root); out=res.get('stdout') or {}; ok=res['returncode']==0 and (out.get('verdict') in ['PASS',None] or out.get('decision') in ['ALLOW',None]); smoke.append({'name':name,'pass':ok,'result':res})
  if not ok: issues.append('smoke_failed:'+name)
 report={'artifact_type':'TRACE_SPAN_LEDGER_STAGE13_EVIDENCE_QUERY_UI_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke,'issues':issues}
 write(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE13_EVIDENCE_QUERY_UI_VALIDATION_LATEST.json', report)
 print(json.dumps(report,indent=2,sort_keys=True)); return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
