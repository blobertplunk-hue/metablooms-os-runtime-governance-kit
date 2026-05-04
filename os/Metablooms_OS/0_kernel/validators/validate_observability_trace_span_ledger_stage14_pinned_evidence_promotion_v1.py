#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, subprocess, sys, time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE14_PINNED_EVIDENCE_RECEIPT_PROMOTION_AND_EXPORT_BINDING'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
 return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,o):
 s=json.dumps(o,indent=2,sort_keys=True)+'\n'; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8'); Path(str(p)+'.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+'  '+p.name+'\n',encoding='utf-8')
def run(cmd,cwd):
 cp=subprocess.run([str(x) for x in cmd],cwd=str(cwd),text=True,capture_output=True,timeout=240)
 try: out=json.loads(cp.stdout) if cp.stdout.strip() else {}
 except Exception: out={'raw_stdout':cp.stdout}
 return {'cmd':[str(x) for x in cmd],'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); root=Path(a.root).resolve(); issues=[]; checks=[]
 req=['0_kernel/registry/observability/MB_PINNED_EVIDENCE_RECEIPT_PROMOTION_SCHEMA_v1.json','0_kernel/registry/observability/MB_PINNED_EVIDENCE_EXPORT_BINDING_SCHEMA_v1.json','0_kernel/registry/observability/MB_PINNED_EVIDENCE_RECEIPT_PROMOTION_POLICY_v1.json','0_kernel/scripts/promote_pinned_evidence_receipt_v1.py','runtime/receipts/pinned_evidence/PINNED_EVIDENCE_RECEIPT_LATEST.json','runtime/state/operator_surface/PINNED_EVIDENCE_RECEIPT_PROMOTION_LATEST.json','runtime/traces/observability/PINNED_EVIDENCE_EXPORT_BINDING_LATEST.json','OPEN_OPERATOR_VISUAL_TRACKER.html']
 for r in req:
  p=root/r; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':r,'exists_nonempty':ok,'sha256':sha(p) if ok else None})
  if not ok: issues.append('missing_or_empty:'+r)
 if not issues:
  receipt=load(root/'runtime/receipts/pinned_evidence/PINNED_EVIDENCE_RECEIPT_LATEST.json'); binding=load(root/'runtime/traces/observability/PINNED_EVIDENCE_EXPORT_BINDING_LATEST.json'); html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
  if receipt.get('artifact_type')!='MB_PROMOTED_PINNED_EVIDENCE_RECEIPT.v1': issues.append('bad_promoted_receipt_type')
  if binding.get('artifact_type')!='MB_PINNED_EVIDENCE_EXPORT_BINDING.v1': issues.append('bad_export_binding_type')
  if receipt.get('stage_id')!=STAGE or binding.get('stage_id')!=STAGE: issues.append('stage_id_mismatch')
  if receipt.get('verdict')!='PASS': issues.append('promoted_receipt_not_pass')
  if receipt.get('pin_count',0)<1: issues.append('no_pins_promoted')
  for pin in receipt.get('pins',[]):
   if not pin.get('path') or not pin.get('actual_sha256'): issues.append('pin_missing_path_or_sha')
   if not (root/pin.get('path','')).is_file(): issues.append('pin_artifact_missing:'+str(pin.get('path')))
  for marker in ["data-section='pinned_evidence_receipt_promotion'", "data-section='pinned_evidence_export_binding'", 'promote_pinned_evidence_receipt_v1.py', 'Formal Evidence Promotion']:
   if marker not in html: issues.append('tracker_missing_marker:'+marker)
  if "data-section='evidence_result_pinning'" not in html and 'data-section="evidence_result_pinning"' not in html: issues.append('stage13_pin_surface_missing')
  ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
  if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append('authority_pointer_copies_not_identical')
  if ptrs[0].get('stage_id')!=STAGE or ptrs[0].get('last_stage')!=STAGE: issues.append('pointer_not_stage14')
  for key in ['pinned_evidence_receipt_promotion','pinned_evidence_export_binding','pinned_evidence_promotion_validation']:
   if key not in ptrs[0]: issues.append('pointer_missing:'+key)
 smoke=[]
 for name,cmd in [('promoter',[sys.executable,str(root/'0_kernel/scripts/promote_pinned_evidence_receipt_v1.py'),'--root',str(root),'--json']),('new_chat_validator',[sys.executable,str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'),str(root)]),('runtime_wrapper',[sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),'--root',str(root),'--json'])]:
  res=run(cmd,root); out=res.get('stdout') or {}; ok=res['returncode']==0 and (out.get('verdict') in ['PASS',None] or out.get('decision') in ['ALLOW',None]); smoke.append({'name':name,'pass':ok,'result':res})
  if not ok: issues.append('smoke_failed:'+name)
 report={'artifact_type':'TRACE_SPAN_LEDGER_STAGE14_PINNED_EVIDENCE_PROMOTION_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke,'issues':issues}
 write(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE14_PINNED_EVIDENCE_PROMOTION_VALIDATION_LATEST.json', report)
 print(json.dumps(report,indent=2,sort_keys=True)); return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
