#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,subprocess,sys,time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE12_TRACE_QUERY_PACKET_AND_SEARCHABLE_EVIDENCE_INDEX'
def sha(p):
 h=hashlib.sha256();
 with Path(p).open('rb') as f:
  [h.update(c) for c in iter(lambda:f.read(1024*1024),b'')]
 return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,o):
 s=json.dumps(o,indent=2,sort_keys=True)+'\n'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8'); Path(str(p)+'.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'  '+p.name+'\n',encoding='utf-8')
def run(cmd,cwd):
 cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=240)
 try: out=json.loads(cp.stdout) if cp.stdout.strip() else {}
 except Exception: out={'raw_stdout':cp.stdout}
 return {'cmd':cmd,'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); root=Path(a.root).resolve(); issues=[]; checks=[]
 req=['0_kernel/registry/observability/MB_TRACE_QUERY_PACKET_SCHEMA_v1.json','0_kernel/registry/observability/MB_SEARCHABLE_EVIDENCE_INDEX_SCHEMA_v1.json','0_kernel/registry/observability/MB_TRACE_QUERY_INDEX_POLICY_v1.json','0_kernel/scripts/observability_trace_query_indexer_v1.py','runtime/traces/observability/SEARCHABLE_EVIDENCE_INDEX_LATEST.json','runtime/state/operator_surface/TRACE_QUERY_PACKET_LATEST.json','runtime/state/operator_surface/TRACE_QUERY_PACKET_LATEST.md','OPEN_OPERATOR_VISUAL_TRACKER.html']
 for rel in req:
  p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok,'sha256':sha(p) if ok else None})
  if not ok: issues.append('missing_or_empty:'+rel)
 if not issues:
  idx=load(root/'runtime/traces/observability/SEARCHABLE_EVIDENCE_INDEX_LATEST.json'); qp=load(root/'runtime/state/operator_surface/TRACE_QUERY_PACKET_LATEST.json'); pol=load(root/'0_kernel/registry/observability/MB_TRACE_QUERY_INDEX_POLICY_v1.json'); html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
  if idx.get('artifact_type')!='MB_SEARCHABLE_EVIDENCE_INDEX.v1': issues.append('bad_index_artifact_type')
  if qp.get('artifact_type')!='MB_TRACE_QUERY_PACKET.v1': issues.append('bad_query_packet_artifact_type')
  if idx.get('stage_id')!=STAGE or qp.get('stage_id')!=STAGE: issues.append('stage_id_mismatch')
  if idx.get('document_count',0)<20: issues.append('too_few_index_documents')
  if idx.get('term_count',0)<100: issues.append('too_few_index_terms')
  if qp.get('verdict')!='PASS': issues.append('query_packet_not_pass')
  if len(qp.get('queries',[]))<6: issues.append('too_few_queries')
  for q in qp.get('queries',[]):
   if not q.get('results'): issues.append('query_no_results:'+q.get('query_id','?'))
  for marker in pol.get('required_html_markers',[]):
   if marker not in html: issues.append('tracker_missing_marker:'+marker)
  ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
  if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append('authority_pointer_copies_not_identical')
  if ptrs[0].get('stage_id')!=STAGE or ptrs[0].get('last_stage')!=STAGE: issues.append('pointer_not_stage12')
  for key in ['trace_query_packet','searchable_evidence_index','trace_query_index_policy','trace_query_indexer','trace_query_validation']:
   if key not in ptrs[0]: issues.append('pointer_missing:'+key)
 smoke=[]
 for name,cmd in [('query_indexer',[sys.executable,str(root/'0_kernel/scripts/observability_trace_query_indexer_v1.py'),'--root',str(root),'--query','export containment proof sha256','--json']),('new_chat_validator',[sys.executable,str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'),str(root)]),('runtime_wrapper',[sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),'--root',str(root),'--json'])]:
  res=run(cmd,root); out=res.get('stdout') or {}; ok=res['returncode']==0 and (out.get('verdict') in ['PASS',None] or out.get('decision') in ['ALLOW',None]); smoke.append({'name':name,'pass':ok,'result':res})
  if not ok: issues.append('smoke_failed:'+name)
 report={'artifact_type':'TRACE_SPAN_LEDGER_STAGE12_TRACE_QUERY_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke,'issues':issues}
 write(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE12_TRACE_QUERY_VALIDATION_LATEST.json',report); print(json.dumps(report,indent=2,sort_keys=True)); return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
