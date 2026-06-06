#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time,hashlib
from pathlib import Path
def now(): return time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())
def h(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def load(p):
 try: return json.loads(Path(p).read_text(encoding='utf-8'))
 except Exception as e: return {'_load_error':str(e),'_path':str(p)}
def wj(p,o): p.parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(p, o, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_agent_harness_executor_review_gate_v1_py_L15', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000); return str(p)
def aj(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.open('a',encoding='utf-8').write(json.dumps(o,sort_keys=True)+'\n'); return str(p)
def main(argv=None):
 pa=argparse.ArgumentParser(); pa.add_argument('--stage',default='IMPLEMENT_AGENT_HARNESS_STAGE_3_EXECUTOR_REVIEW_GATE'); pa.add_argument('--work-order'); pa.add_argument('--strict',action='store_true'); pa.add_argument('--json',action='store_true'); a=pa.parse_args(argv); r=root()
 spec=load(r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_EXECUTOR_REVIEW_GATE_SPEC_v1.json')
 plan_path=r/'runtime/agent_harness/AGENT_HARNESS_STAGE2_PARALLEL_WORKPACKET_PLAN_LATEST.json'; diff_path=r/'runtime/agent_harness/diff_reviews/AGENT_HARNESS_STAGE2_DIFF_REVIEW_LATEST.json'
 plan=load(plan_path) if plan_path.exists() else {'workpackets':[],'missing':True}; diff=load(diff_path) if diff_path.exists() else {'missing':True,'blockers':[]}
 wo=load(Path(a.work_order)) if a.work_order else {'stage_name':a.stage}
 packets=plan.get('workpackets',[]) if isinstance(plan,dict) else []; impl=[p for p in packets if 'implement' in str(p.get('role','')).lower()]
 blockers=[]; warnings=[]
 if diff.get('blockers'): blockers.append({'gate':'diff_review','reason':'diff_review_blockers_present','count':len(diff.get('blockers',[]))})
 if diff.get('verdict') and diff.get('verdict') not in ('DIFF_REVIEW_PASS','PASS'): blockers.append({'gate':'diff_review','reason':'diff_review_verdict_not_pass','verdict':diff.get('verdict')})
 for p in impl:
  if not p.get('diff_review_required',True): blockers.append({'gate':'executor_review_required','workpacket_id':p.get('workpacket_id'),'reason':'implementation_packet_without_diff_review_required'})
  if not p.get('write_scope'): blockers.append({'gate':'write_scope','workpacket_id':p.get('workpacket_id'),'reason':'implementation_packet_missing_write_scope'})
  if len(p.get('write_scope',[])) > spec.get('limits',{}).get('max_write_scope_entries_per_packet',25): blockers.append({'gate':'write_scope','workpacket_id':p.get('workpacket_id'),'reason':'write_scope_too_broad'})
 if a.strict and not plan_path.exists() and str(a.stage).startswith('IMPLEMENT_AGENT_HARNESS'): blockers.append({'gate':'plan_presence','reason':'harness_stage_requires_workpacket_plan'})
 elif not plan_path.exists(): warnings.append({'gate':'plan_presence','reason':'no_harness_plan_for_non_harness_stage'})
 verdict='AGENT_HARNESS_EXECUTOR_REVIEW_PASS' if not blockers else 'AGENT_HARNESS_EXECUTOR_REVIEW_BLOCK'
 report={'artifact_type':'AGENT_HARNESS_STAGE3_EXECUTOR_REVIEW_GATE_REPORT_v1','created_utc':now(),'stage_name':a.stage,'verdict':verdict,'strict':bool(a.strict),'work_order_stage':wo.get('stage_name'),'plan_path':str(plan_path),'diff_review_path':str(diff_path),'workpacket_count':len(packets),'implementation_packet_count':len(impl),'blocker_count':len(blockers),'warning_count':len(warnings),'blockers':blockers[:25],'warnings':warnings[:25],'decision':'ALLOW' if not blockers else 'BLOCK','gate_invariants':['diff_review_required_before_executor_promotion','bounded_write_scope_required','review_gate_blocks_before_cartridge_execution','trace_receipt_handoff_required']}
 out=r/'runtime/agent_harness/executor_reviews/AGENT_HARNESS_STAGE3_EXECUTOR_REVIEW_LATEST.json'; wj(out,report)
 aj(r/'runtime/traces/agent_harness/TRACE_SPAN_LEDGER_AGENT_HARNESS_STAGE3.jsonl',{'schema_version':'MB_TRACE_SPAN_LEDGER_SPEC_v2','trace_id':h(a.stage),'span_id':h(a.stage+'executor_review'+now()),'parent_span_id':None,'name':'agent_harness.stage3.executor_review_gate','stage_name':a.stage,'event':'end','status':'OK' if not blockers else 'ERROR','timestamp_utc':now(),'attributes':{'blocker_count':len(blockers),'warning_count':len(warnings),'report_path':str(out)}})
 print(json.dumps(report,indent=2,sort_keys=True) if a.json else verdict); return 0 if not blockers else 31
if __name__=='__main__': raise SystemExit(main())
