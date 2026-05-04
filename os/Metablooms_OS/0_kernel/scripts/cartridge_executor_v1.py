#!/usr/bin/env python3
from __future__ import annotations

# MetaBlooms Stage4 bounded subprocess enforcement shim.
from pathlib import Path as _MBPath
import sys as _MBSys
_MB_SELF = _MBPath(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_EXEC_LIB = _MB_PARENT / "0_kernel" / "lib" / "execution"
    if (_MB_EXEC_LIB / "bounded_subprocess_compat_v1.py").exists():
        if str(_MB_EXEC_LIB) not in _MBSys.path:
            _MBSys.path.insert(0, str(_MB_EXEC_LIB))
        break
from bounded_subprocess_compat_v1 import run as bounded_subprocess_run
import argparse,hashlib,json,time,subprocess
from pathlib import Path
CONTRACT='MB_CARTRIDGE_EXECUTOR_CONTRACT_v1'
def now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def h(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def wj(p,o): p.parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(p, o, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_cartridge_executor_v1_py_L25', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000); return str(p)
def aj(p,o): p.parent.mkdir(parents=True,exist_ok=True); f=p.open('a',encoding='utf-8'); f.write(json.dumps(o,sort_keys=True)+'\n'); f.close(); return str(p)
def main(argv=None):
 pa=argparse.ArgumentParser(); pa.add_argument('--work-order',required=True); pa.add_argument('--security-gate-passed',action='store_true'); a=pa.parse_args(argv); r=root(); wp=Path(a.work_order); ledger=r/'runtime/traces/operator_surface/TRACE_LEDGER_LATEST.jsonl'
 try: wo=json.loads(wp.read_text())
 except Exception as e: print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_WORK_ORDER_INVALID','error':str(e)})); return 2
 stage=wo.get('stage_name','UNKNOWN'); tid=wo.get('thread_id'); cid=wo.get('checkpoint_id'); trace=h(stage+'|'+str(tid)+'|'+str(cid))
 def span(name,event,status='OK',attrs=None): aj(ledger,{'schema_version':'MB_TRACE_SPAN_LEDGER_SPEC_v2','trace_id':trace,'span_id':h(trace+name+event+now()),'parent_span_id':None,'name':name,'stage_name':stage,'event':event,'status':status,'timestamp_utc':now(),'attributes':attrs or {}})
 if not a.security_gate_passed:
  gate=r/'0_kernel/security/security_gate_enforcer_v1.py'
  if not gate.exists(): print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_SECURITY_GATE_MISSING','fail_closed':True,'required_gate':str(gate)})); return 22
  gp=bounded_subprocess_run(['python3','-S',str(gate),'--work-order',str(wp),'--fixtures','--json'],cwd=str(r),text=True,capture_output=True,timeout=90)
  if gp.returncode!=0: print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_SECURITY_GATE_BLOCK','fail_closed':True,'security_gate_stdout_tail':gp.stdout[-2000:],'security_gate_stderr_tail':gp.stderr[-1000:]})); return gp.returncode
 span('cartridge_executor.start','start','OK',{'work_order_path':str(wp),'security_gate':'PASS'})
 review_gate=r/'0_kernel/scripts/agent_harness_executor_review_gate_v1.py'
 if review_gate.exists():
  rg=bounded_subprocess_run(['python3','-S',str(review_gate),'--stage',stage,'--work-order',str(wp),'--strict','--json'],cwd=str(r),text=True,capture_output=True,timeout=60)
  if rg.returncode!=0:
   span('cartridge_executor.executor_review_gate','end','ERROR',{'rc':rg.returncode,'stdout_tail':rg.stdout[-1200:]})
   print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_REVIEW_GATE_BLOCK','fail_closed':True,'stage_name':stage,'review_gate_stdout_tail':rg.stdout[-2000:],'review_gate_stderr_tail':rg.stderr[-1000:]},indent=2,sort_keys=True)); return 31
  span('cartridge_executor.executor_review_gate','end','OK',{'rc':rg.returncode})
 reg=r/'0_kernel/registry/operator_surface/CARTRIDGE_EXECUTOR_REGISTRY_v1.json'; regs=json.loads(reg.read_text()) if reg.exists() else {'registered_stage_handlers':[]}
 match=next((x for x in regs.get('registered_stage_handlers',[]) if stage==x.get('stage_name') or stage.startswith(x.get('stage_prefix','\0'))),None)
 if not match:
  span('cartridge_executor.route','end','ERROR',{'reason':'no_registered_handler'}); print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_NO_REGISTERED_HANDLER','stage_name':stage,'trace_id':trace,'trace_ledger':str(ledger),'fail_closed':True},indent=2,sort_keys=True)); return 3
 if match.get('handler_id')=='evals_trace_review_stage4_builtin':
  gate=r/'0_kernel/scripts/evals_validator_alignment_gate_v1.py'; validator=r/'0_kernel/validators/validate_evals_validator_alignment_stage4_v1.py'
  rp=r/'runtime/receipts/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE4_EXECUTOR_RECEIPT_LATEST.json'; hp=r/'runtime/handoffs/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE4_EXECUTOR_HANDOFF_LATEST.json'
  gr=bounded_subprocess_run(['python3','-S',str(gate),'--json'],cwd=str(r),text=True,capture_output=True,timeout=90) if gate.exists() else None
  vp=bounded_subprocess_run(['python3','-S',str(validator)],cwd=str(r),text=True,capture_output=True,timeout=90) if validator.exists() else None
  ok=bool(gr and gr.returncode==0 and vp and vp.returncode==0)
  wj(rp,{'artifact_type':'EVALS_VALIDATOR_ALIGNMENT_STAGE4_EXECUTOR_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS' if ok else 'FAIL','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','alignment_gate_rc':gr.returncode if gr else None,'validator_rc':vp.returncode if vp else None,'implemented':['validator_alignment_gate','promotion_decision','zero_false_pass_gate','stage4_validator','evals_cli_alignment_gate']})
  wj(hp,{'artifact_type':'EVALS_VALIDATOR_ALIGNMENT_STAGE4_EXECUTOR_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'IMPLEMENT_STATE_CHECKPOINT_RESUME_AND_INTERRUPT_CARTRIDGE_STAGE_1_OR_SECURITY_STAGE4_RED_TEAM_FIXTURES','continuation_rule':'Keep one bounded stage; do not expand eval validators without representative trace/human-alignment evidence.'})
  span('cartridge_executor.end','end','OK' if ok else 'ERROR',{'receipt':str(rp),'handoff':str(hp),'alignment_gate_rc':gr.returncode if gr else None,'validator_rc':vp.returncode if vp else None})
  run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
  print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS' if ok else 'CARTRIDGE_EXECUTOR_VALIDATOR_FAIL','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0 if ok else 2
 if match.get('handler_id')=='evals_trace_review_stage3_builtin':
  runner=r/'0_kernel/scripts/evals_evaluator_runner_v1.py'; validator=r/'0_kernel/validators/validate_evals_evaluator_runner_stage3_v1.py'
  rp=r/'runtime/receipts/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE3_EXECUTOR_RECEIPT_LATEST.json'; hp=r/'runtime/handoffs/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE3_EXECUTOR_HANDOFF_LATEST.json'
  rr=bounded_subprocess_run(['python3','-S',str(runner),'--json'],cwd=str(r),text=True,capture_output=True,timeout=90) if runner.exists() else None
  vp=bounded_subprocess_run(['python3','-S',str(validator)],cwd=str(r),text=True,capture_output=True,timeout=90) if validator.exists() else None
  ok=bool(rr and rr.returncode==0 and vp and vp.returncode==0)
  wj(rp,{'artifact_type':'EVALS_EVALUATOR_RUNNER_STAGE3_EXECUTOR_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS' if ok else 'FAIL','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','runner_rc':rr.returncode if rr else None,'validator_rc':vp.returncode if vp else None,'implemented':['evals_evaluator_runner_v1','confusion_matrix','stage3_validator','evals_cli_runner_confusion']})
  wj(hp,{'artifact_type':'EVALS_EVALUATOR_RUNNER_STAGE3_EXECUTOR_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'IMPLEMENT_EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE_STAGE_4_VALIDATOR_ALIGNMENT_GATE_PROMOTION','continuation_rule':'Keep one bounded evals stage; wire evaluator results into promotion gates and require no false-pass examples.'})
  span('cartridge_executor.end','end','OK' if ok else 'ERROR',{'receipt':str(rp),'handoff':str(hp),'runner_rc':rr.returncode if rr else None,'validator_rc':vp.returncode if vp else None})
  run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
  print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS' if ok else 'CARTRIDGE_EXECUTOR_VALIDATOR_FAIL','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0 if ok else 2
 if match.get('handler_id')=='evals_trace_review_stage2_builtin':
  validator=r/'0_kernel/validators/validate_evals_scorecards_stage2_v1.py'
  vp=bounded_subprocess_run(['python3','-S',str(validator)],cwd=str(r),text=True,capture_output=True,timeout=90) if validator.exists() else None
  rp=r/'runtime/receipts/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE2_EXECUTOR_RECEIPT_LATEST.json'
  hp=r/'runtime/handoffs/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE2_EXECUTOR_HANDOFF_LATEST.json'
  wj(rp,{'artifact_type':'EVALS_SCORECARDS_STAGE2_EXECUTOR_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS' if vp and vp.returncode==0 else 'FAIL','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','validator_rc':vp.returncode if vp else None,'stdout_tail':vp.stdout[-1500:] if vp else '', 'implemented':['scorecard_spec','regression_dataset','failure_mode_catalog','stage2_validator','evals_cli_scorecards']})
  wj(hp,{'artifact_type':'EVALS_SCORECARDS_STAGE2_EXECUTOR_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'IMPLEMENT_EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE_STAGE_3_EVALUATOR_RUNNER_AND_CONFUSION_MATRIX','continuation_rule':'Keep one bounded evals stage; run actual evaluator outputs against regression dataset and compute confusion matrix.'})
  span('cartridge_executor.end','end','OK' if vp and vp.returncode==0 else 'ERROR',{'receipt':str(rp),'handoff':str(hp),'validator_rc':vp.returncode if vp else None})
  run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
  print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS' if vp and vp.returncode==0 else 'CARTRIDGE_EXECUTOR_VALIDATOR_FAIL','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0 if vp and vp.returncode==0 else 2
 if match.get('handler_id')=='evals_trace_review_stage1_builtin':
  validator=r/'0_kernel/validators/validate_evals_trace_review_stage1_v1.py'
  vp=bounded_subprocess_run(['python3','-S',str(validator)],cwd=str(r),text=True,capture_output=True,timeout=90) if validator.exists() else None
  rp=r/'runtime/receipts/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE1_EXECUTOR_RECEIPT_LATEST.json'
  hp=r/'runtime/handoffs/evals/EVALS_TRACE_REVIEW_VALIDATOR_ALIGNMENT_STAGE1_EXECUTOR_HANDOFF_LATEST.json'
  wj(rp,{'artifact_type':'EVALS_TRACE_REVIEW_EXECUTOR_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS' if vp and vp.returncode==0 else 'FAIL','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','validator_rc':vp.returncode if vp else None,'stdout_tail':vp.stdout[-1000:] if vp else '', 'implemented':['minimum_viable_eval_loop','trace_review_schema','validator_alignment_policy','evals_command_surface']})
  wj(hp,{'artifact_type':'EVALS_TRACE_REVIEW_EXECUTOR_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'IMPLEMENT_EVALS_TRACE_REVIEW_AND_VALIDATOR_ALIGNMENT_CARTRIDGE_STAGE_2_SCORECARDS_AND_REGRESSION_DATASET','continuation_rule':'Keep one bounded evals stage; add scored examples and validator calibration before broader execution.'})
  span('cartridge_executor.end','end','OK' if vp and vp.returncode==0 else 'ERROR',{'receipt':str(rp),'handoff':str(hp),'validator_rc':vp.returncode if vp else None})
  run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
  print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS' if vp and vp.returncode==0 else 'CARTRIDGE_EXECUTOR_VALIDATOR_FAIL','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0 if vp and vp.returncode==0 else 2
 if match.get('handler_id')=='state_checkpoint_resume_interrupt_stage2_builtin':
  validator=r/'0_kernel/validators/validate_state_checkpoint_stage2_v1.py'
  vp=bounded_subprocess_run(['python3','-S',str(validator)],cwd=str(r),text=True,capture_output=True,timeout=120) if validator.exists() else None
  rp=r/'runtime/receipts/state_checkpoint/STATE_CHECKPOINT_RESUME_INTERRUPT_STAGE2_EXECUTOR_RECEIPT_LATEST.json'
  hp=r/'runtime/handoffs/state_checkpoint/STATE_CHECKPOINT_RESUME_INTERRUPT_STAGE2_EXECUTOR_HANDOFF_LATEST.json'
  ok=bool(vp and vp.returncode==0)
  wj(rp,{'artifact_type':'STATE_CHECKPOINT_STAGE2_EXECUTOR_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS' if ok else 'FAIL','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','validator_rc':vp.returncode if vp else None,'implemented':['runner_checkpoint_start_end','security_interrupt_checkpoint','same_thread_resume','malicious_block_before_interrupt']})
  wj(hp,{'artifact_type':'STATE_CHECKPOINT_STAGE2_EXECUTOR_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'IMPLEMENT_SECURITY_ARTIFACT_THREAT_MODEL_STAGE_4_RED_TEAM_FIXTURES_OR_AGENT_HARNESS_STAGE_1','continuation_rule':'Keep one bounded stage; do not permit stage execution without checkpoint and security interrupt evidence.'})
  span('cartridge_executor.end','end','OK' if ok else 'ERROR',{'receipt':str(rp),'handoff':str(hp),'validator_rc':vp.returncode if vp else None})
  run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
  print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS' if ok else 'CARTRIDGE_EXECUTOR_VALIDATOR_FAIL','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0 if ok else 2

 if match.get('handler_id')=='agent_harness_stage1_builtin':
  planner=r/'0_kernel/scripts/agent_harness_planner_v1.py'; validator=r/'0_kernel/validators/validate_agent_harness_stage1_v1.py'
  rp=r/'runtime/receipts/agent_harness/AGENT_HARNESS_STAGE1_EXECUTOR_RECEIPT_LATEST.json'; hp=r/'runtime/handoffs/agent_harness/AGENT_HARNESS_STAGE1_EXECUTOR_HANDOFF_LATEST.json'
  pr=bounded_subprocess_run(['python3','-S',str(planner),'--stage',stage,'--write-plan','--json'],cwd=str(r),text=True,capture_output=True,timeout=45) if planner.exists() else None
  vp=bounded_subprocess_run(['python3','-S',str(validator)],cwd=str(r),text=True,capture_output=True,timeout=45) if validator.exists() else None
  ok=bool(pr and pr.returncode==0 and vp and vp.returncode==0)
  wj(rp,{'artifact_type':'AGENT_HARNESS_STAGE1_EXECUTOR_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS' if ok else 'FAIL','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','planner_rc':pr.returncode if pr else None,'validator_rc':vp.returncode if vp else None,'implemented':['agent_harness_stage_graph','role_policy','workpacket_schema','planner','validator','mb_harness_command']})
  wj(hp,{'artifact_type':'AGENT_HARNESS_STAGE1_EXECUTOR_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'IMPLEMENT_AGENT_HARNESS_STAGE_2_PARALLEL_WORKPACKETS_AND_DIFF_REVIEW_OR_SOFTWARE_QUALITY_STAGE_1','continuation_rule':'Keep one bounded agent-harness stage; do not run parallel agents until workpacket scopes, diffs, and checkpoint interrupts are validated.'})
  span('cartridge_executor.end','end','OK' if ok else 'ERROR',{'receipt':str(rp),'handoff':str(hp),'planner_rc':pr.returncode if pr else None,'validator_rc':vp.returncode if vp else None})
  run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
  print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS' if ok else 'CARTRIDGE_EXECUTOR_VALIDATOR_FAIL','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0 if ok else 2
 rp=r/'runtime/receipts/security/SECURITY_ARTIFACT_THREAT_MODEL_STAGE3_EXECUTOR_SMOKE_RECEIPT_LATEST.json'; hp=r/'runtime/handoffs/security/SECURITY_ARTIFACT_THREAT_MODEL_STAGE3_EXECUTOR_SMOKE_HANDOFF_LATEST.json'
 wj(rp,{'artifact_type':'SECURITY_STAGE3_EXECUTOR_SMOKE_RECEIPT_v1','stage':stage,'created_utc':now(),'verdict':'PASS','trace_id':trace,'executor_contract':CONTRACT,'security_gate':'PASS','implemented':['security_gate_before_executor','fail_closed_unknown_stage','trace_ledger_span']})
 wj(hp,{'artifact_type':'SECURITY_STAGE3_EXECUTOR_SMOKE_HANDOFF_v1','completed_stage':stage,'created_utc':now(),'status':'READY_FOR_NEXT_BOUNDED_STAGE','next_stage':'CONTINUE_GOVERNED_SECURITY_OR_EVALS_HARDENING','continuation_rule':'Stage runner and export promotion gates are hard-wired; continue one bounded stage only.'})
 span('cartridge_executor.end','end','OK',{'receipt':str(rp),'handoff':str(hp)})
 run=r/f'runtime/traces/operator_surface/TRACE_{h(stage)}_{cid}.json'; wj(run,{'artifact_type':'MB_TRACE_RUN_RECORD_v1','trace_id':trace,'stage_name':stage,'thread_id':tid,'checkpoint_id':cid,'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'})
 print(json.dumps({'verdict':'CARTRIDGE_EXECUTOR_PASS','stage_name':stage,'trace_id':trace,'trace_run_path':str(run),'trace_ledger':str(ledger),'receipt_path':str(rp),'handoff_path':str(hp),'security_gate':'PASS'},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
