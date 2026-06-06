#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys, time, hashlib
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE8_BOOT_RECEIPT_WRAPPER_ONLY_ENFORCEMENT_AND_HISTORICAL_CALLSITE_QUARANTINE'

def sha_file(p:Path):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
 return h.hexdigest()
def load(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def run(cmd,cwd):
 cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=45)
 try: out=json.loads(cp.stdout)
 except Exception: out={'raw_stdout':cp.stdout,'stderr':cp.stderr}
 return {'cmd':cmd,'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}

def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true'); args=ap.parse_args(argv)
 root=Path(args.root).resolve(); issues=[]; checks=[]
 required=[
  '0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json',
  '0_kernel/scripts/observability_historical_callsite_quarantine_v1.py',
  'runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json',
  'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py',
  'runtime/governance/new_chat_start_contract_validator_v1.py',
  '0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md',
  'NEW_CHAT_START_HERE.md',
  'CURRENT_FULL_AUTHORITY_POINTER_v1.json',
  'runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
  '0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
  'OPEN_OPERATOR_VISUAL_TRACKER.html'
 ]
 for rel in required:
  p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok,'sha256':sha_file(p) if ok else None})
  if not ok: issues.append('missing_or_empty:'+rel)
 if not issues:
  policy=load(root/'0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json')
  index=load(root/'runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json')
  if index.get('verdict')!='PASS': issues.append('quarantine_index_not_pass')
  bad_classes=[h for h in index.get('hits',[]) if h.get('class')=='unclassified']
  live_bad=[h for h in index.get('hits',[]) if h.get('live_forbidden_fragments')]
  if bad_classes: issues.append('unclassified_direct_references_present')
  if live_bad: issues.append('live_operator_direct_commands_present')
  for rel in policy.get('live_operator_surfaces',[]):
   p=root/rel
   if not p.is_file(): issues.append('live_operator_surface_missing:'+rel); continue
   txt=p.read_text(encoding='utf-8', errors='ignore')
   if policy.get('required_operator_entrypoint') and policy['required_operator_entrypoint'] not in txt and rel in ['NEW_CHAT_START_HERE.md','0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md','OPEN_OPERATOR_VISUAL_TRACKER.html']:
    issues.append('live_surface_omits_wrapper_entrypoint:'+rel)
   for frag in policy.get('forbidden_live_operator_command_fragments',[]):
    if frag in txt: issues.append('live_surface_forbidden_fragment:'+rel)
  ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
  if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append('authority_pointer_copies_not_identical')
  if ptrs[0].get('stage_id')!=STAGE or ptrs[0].get('last_stage')!=STAGE: issues.append('pointer_not_stage8')
  if 'historical_callsite_quarantine_index' not in ptrs[0]: issues.append('pointer_missing_quarantine_index')
  html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
  if 'data-section="historical_callsite_quarantine"' not in html: issues.append('tracker_missing_historical_quarantine_section')
 # regenerate to catch staleness
 scanner=run([sys.executable,str(root/'0_kernel/scripts/observability_historical_callsite_quarantine_v1.py'),'--root',str(root),'--json'],root)
 wrapper_good=run([sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),'--root',str(root),'--json'],root)
 wrapper_bad=run([sys.executable,str(root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'),str(root),'--json'],root)
 newchat=run([sys.executable,str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'),str(root)],root)
 smoke_checks=[
  {'name':'scanner_passes','pass':scanner['returncode']==0 and scanner['stdout'].get('verdict')=='PASS','result':scanner},
  {'name':'wrapper_named_root_allows','pass':wrapper_good['returncode']==0 and wrapper_good['stdout'].get('decision')=='ALLOW','result':wrapper_good},
  {'name':'wrapper_positional_root_denies','pass':wrapper_bad['returncode']!=0 and wrapper_bad['stdout'].get('decision')=='DENY','result':wrapper_bad},
  {'name':'new_chat_validator_allows','pass':newchat['returncode']==0 and newchat['stdout'].get('decision')=='ALLOW','result':newchat},
 ]
 for c in smoke_checks:
  if not c['pass']: issues.append('smoke_check_failed:'+c['name'])
 report={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE8_HISTORICAL_CALLSITE_QUARANTINE_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke_checks,'issues':issues}
 out=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE8_HISTORICAL_CALLSITE_QUARANTINE_VALIDATION_LATEST.json'
 out.parent.mkdir(parents=True,exist_ok=True)
 text=json.dumps(report,indent=2,sort_keys=True)+'\n'; out.write_text(text,encoding='utf-8')
 (Path(str(out)+'.sha256')).write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+out.name+'\n',encoding='utf-8')
 print(json.dumps(report,indent=2,sort_keys=True))
 return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
