#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,time
from pathlib import Path
def root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
 r=root(); issues=[]
 req=['0_kernel/scripts/agent_harness_executor_review_gate_v1.py','0_kernel/registry/agent_harness/MB_AGENT_HARNESS_EXECUTOR_REVIEW_GATE_SPEC_v1.json','0_kernel/registry/operator_surface/MB_CLI_COMMAND_SPEC_v20.json','runtime/receipts/agent_harness/AGENT_HARNESS_STAGE3_RECEIPT_LATEST.json','runtime/handoffs/agent_harness/AGENT_HARNESS_STAGE3_HANDOFF_LATEST.json']
 for rel in req:
  if not (r/rel).exists(): issues.append({'missing':rel})
 spec=load(r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_EXECUTOR_REVIEW_GATE_SPEC_v1.json') if not issues else {}
 ids=[g.get('gate_id') for g in spec.get('gates',[])]
 for gid in ['AH-GATE-301','AH-GATE-302','AH-GATE-303','AH-GATE-304']:
  if gid not in ids: issues.append({'missing_gate':gid})
 cp=subprocess.run(['python3','-S',str(r/'0_kernel/scripts/agent_harness_executor_review_gate_v1.py'),'--stage','IMPLEMENT_AGENT_HARNESS_STAGE_3_EXECUTOR_REVIEW_GATE','--json'],cwd=str(r),text=True,capture_output=True,timeout=30)
 try: report=json.loads(cp.stdout)
 except Exception: report={'parse_error':cp.stdout[-1000:]}
 if cp.returncode!=0: issues.append({'gate_smoke_rc':cp.returncode,'stdout_tail':cp.stdout[-1000:]})
 result={'artifact_type':'AGENT_HARNESS_STAGE3_VALIDATION_v1','created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','issues':issues,'gate_smoke_verdict':report.get('verdict'),'gate_blocker_count':report.get('blocker_count')}
 out=r/'runtime/evals/agent_harness/AGENT_HARNESS_STAGE3_VALIDATION_LATEST.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps(result,indent=2,sort_keys=True)); return 0 if not issues else 9
if __name__=='__main__': raise SystemExit(main())
