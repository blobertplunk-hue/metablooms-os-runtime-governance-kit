#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,time,hashlib
from pathlib import Path
POLICY_REL='0_kernel/registry/runtime_governance/RUNAWAY_TURN_BREAKER_POLICY_v1.json'; TRACE_REL='runtime/traces/runtime_governance/TRACE_SPAN_LEDGER_RUNAWAY_TURN_BREAKER.jsonl'; RECEIPT_DIR='runtime/receipts/runtime_governance'
def utc_now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def find_root():
 env=os.environ.get('METABLOOMS_ROOT')
 if env and (Path(env)/'boot_manifest_v1.json').exists(): return Path(env)
 here=Path(__file__).resolve()
 for p in [here.parent,*here.parents]:
  if (p/'boot_manifest_v1.json').exists() and (p/'0_kernel').exists(): return p
 return Path.cwd()
def load_policy(root):
 p=root/POLICY_REL
 return json.loads(p.read_text()) if p.exists() else {'default_budget':{'max_wall_clock_seconds':180,'max_command_count':12,'max_files_touched':60,'max_trace_metadata_bytes':8000,'allow_broad_extract':False}}
def trace(root,payload):
 t=root/TRACE_REL; t.parent.mkdir(parents=True,exist_ok=True); seed=json.dumps(payload,sort_keys=True,separators=(',',':'))
 rec={'schema_version':'MB_TRACE_SPAN_LEDGER_SPEC_v2','trace_id':hashlib.sha256(seed.encode()).hexdigest()[:32],'span_id':hashlib.sha256((seed+'span').encode()).hexdigest()[:16],'parent_span_id':None,'name':'runaway_turn_breaker_preflight','stage_name':payload.get('stage_name'),'event':'budget_preflight','status':payload.get('verdict'),'timestamp_utc':utc_now(),'attributes':{k:v for k,v in payload.items() if k!='budget'}}
 with t.open('a',encoding='utf-8') as f: f.write(json.dumps(rec,sort_keys=True)+'\n')
 return str(t)
def receipt(root,payload):
 d=root/RECEIPT_DIR; d.mkdir(parents=True,exist_ok=True); safe=''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in str(payload.get('stage_name') or 'UNKNOWN'))[:80]
 path=d/f'RUNAWAY_TURN_BREAKER_STAGE0_{safe}_{utc_now()}_RECEIPT.json'; text=json.dumps(payload,indent=2,sort_keys=True)+'\n'; path.write_text(text); (d/'RUNAWAY_TURN_BREAKER_STAGE0_RECEIPT_LATEST.json').write_text(text); return str(path)
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument('--stage-name',default='UNSPECIFIED_STAGE'); ap.add_argument('--mode',default='preflight'); ap.add_argument('--timeout',type=int,default=120); ap.add_argument('--command-count',type=int,default=1); ap.add_argument('--files-touched',type=int,default=1); ap.add_argument('--trace-metadata-bytes',type=int,default=0); ap.add_argument('--broad-extract',action='store_true'); ap.add_argument('--allow-broad-extract',action='store_true'); ap.add_argument('--has-receipt-plan',action='store_true'); ap.add_argument('--has-handoff-plan',action='store_true'); ap.add_argument('--json',action='store_true'); a=ap.parse_args(argv); root=find_root(); pol=load_policy(root); b=pol.get('default_budget',{}); issues=[]; warnings=[]
 if a.timeout>int(b.get('max_wall_clock_seconds',180)): issues.append({'gate_id':'RTB-001','reason':'timeout_exceeds_budget','timeout':a.timeout})
 if a.command_count>int(b.get('max_command_count',12)): issues.append({'gate_id':'RTB-002','reason':'command_count_exceeds_budget','command_count':a.command_count})
 if a.files_touched>int(b.get('max_files_touched',60)): issues.append({'gate_id':'RTB-003','reason':'files_touched_exceeds_budget','files_touched':a.files_touched})
 if a.broad_extract and not a.allow_broad_extract: issues.append({'gate_id':'RTB-004','reason':'broad_extract_denied_by_default'})
 if not a.has_receipt_plan or not a.has_handoff_plan: issues.append({'gate_id':'RTB-005','reason':'receipt_handoff_plan_required'})
 if a.trace_metadata_bytes>int(b.get('max_trace_metadata_bytes',8000)): warnings.append({'gate_id':'RTB-006','reason':'trace_metadata_large_use_diff_summary'})
 payload={'artifact_type':'RUNAWAY_TURN_BREAKER_DECISION_v1','created_utc':utc_now(),'root':str(root),'stage_name':a.stage_name,'mode':a.mode,'verdict':'RUNAWAY_BUDGET_PASS' if not issues else 'RUNAWAY_BUDGET_BLOCK','issues':issues,'warnings':warnings,'budget':b}
 payload['trace_path']=trace(root,payload); payload['receipt_path']=receipt(root,payload); print(json.dumps(payload,indent=2,sort_keys=True) if a.json else payload['verdict']); return 0 if not issues else 124
if __name__=='__main__': raise SystemExit(main())
