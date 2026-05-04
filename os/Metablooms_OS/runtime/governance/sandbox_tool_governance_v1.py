#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import datetime, json
BOOTSTRAP_ID='SANDBOX_TOOL_GOVERNANCE_BOOTSTRAP_v1'
REQUIRED_POLICY_PATHS=['0_kernel/sandbox_governance/SANDBOX_TOOL_USE_POLICY_v1.json','0_kernel/sandbox_governance/SANDBOX_BOOTSTRAP_CONTRACT_v1.json','0_kernel/sandbox_governance/SANDBOX_METHOD_ROUTER_v1.json','0_kernel/sandbox_governance/CODING_PLAN_REQUIREMENT_v1.json']
def _now(): return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
def resolve_root(start):
 p=Path(start).resolve(); p=p.parent if p.is_file() else p
 for c in [p,p/'Metablooms_OS',p.parent]:
  if (c/'runtime/governance').exists() and (c/'0_kernel').exists(): return c
 cur=p
 for _ in range(8):
  if (cur/'runtime/governance').exists() and (cur/'0_kernel').exists(): return cur
  cur=cur.parent
 return p
def load_policy(root):
 root=resolve_root(root); missing=[r for r in REQUIRED_POLICY_PATHS if not (root/r).exists()]
 return {'bootstrap_id':BOOTSTRAP_ID,'timestamp_utc':_now(),'root':str(root),'missing':missing,'decision':'DENY' if missing else 'ALLOW'}
def validate_sandbox_plan(root, packet:Dict[str,Any]):
 root=resolve_root(root); errors:List[str]=[]; boot=load_policy(root)
 if boot['decision']!='ALLOW': errors += ['missing_policy:'+m for m in boot['missing']]
 if packet.get('metablooms_turn') and not packet.get('sandbox_policy_loaded'): errors.append('sandbox_policy_not_loaded_at_chat_start')
 if packet.get('will_code') or packet.get('will_modify_runtime'):
  if not packet.get('coding_plan_artifact'): errors.append('coding_plan_missing_before_code_change')
  method=(packet.get('python_method') or '').strip()
  if method=='python3' and not packet.get('normal_python_probe_artifact'): errors.append('normal_python_used_without_probe_or_justification')
  if packet.get('stdlib_only_task') and method and method!='python3 -S' and not packet.get('method_exception_artifact'): errors.append('stdlib_task_not_using_python3_dash_S')
 if packet.get('archive_or_hash_work') and not packet.get('export_latency_controls'): errors.append('archive_hash_work_missing_export_latency_controls')
 if packet.get('final_response_ready') and not packet.get('sandbox_receipt_artifact'): errors.append('final_response_missing_sandbox_receipt')
 return {'bootstrap_id':BOOTSTRAP_ID,'timestamp_utc':_now(),'root':str(root),'decision':'DENY' if errors else 'ALLOW','errors':errors,'policy_loaded':boot['decision']=='ALLOW'}
if __name__=='__main__':
 import argparse, sys
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--packet')
 ns=ap.parse_args(); result=load_policy(ns.root) if not ns.packet else validate_sandbox_plan(ns.root,json.loads(Path(ns.packet).read_text()))
 print(json.dumps(result,indent=2)); sys.exit(0 if result.get('decision')=='ALLOW' else 1)
