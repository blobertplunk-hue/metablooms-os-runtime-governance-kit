#!/usr/bin/env python3
from __future__ import annotations
import json, sys, importlib.util
from pathlib import Path

import importlib.util as _mb_atomic_importlib_util
_ATOMIC_JSON_COMPAT_PATH = Path(__file__).resolve().parents[3] / '0_kernel/lib/io/atomic_json_compat_v1.py'
_ATOMIC_JSON_COMPAT_SPEC = _mb_atomic_importlib_util.spec_from_file_location('atomic_json_compat_v1_stage5', _ATOMIC_JSON_COMPAT_PATH)
_mb_atomic_json = _mb_atomic_importlib_util.module_from_spec(_ATOMIC_JSON_COMPAT_SPEC)
assert _ATOMIC_JSON_COMPAT_SPEC and _ATOMIC_JSON_COMPAT_SPEC.loader
_ATOMIC_JSON_COMPAT_SPEC.loader.exec_module(_mb_atomic_json)
ROOT=Path(__file__).resolve().parents[3]
def load(rel,name):
 spec=importlib.util.spec_from_file_location(name, ROOT/rel); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def main():
 router=load('runtime/governance/tool_selection_evidence_router_v1.py','router')
 chat=load('runtime/governance/chat_governance_kernel_v1.py','chat')
 loader=load('runtime/governance/boot_critical_governance_loader_v1.py','loader')
 results={}
 results['router_archive']=router.select_tool(ROOT, {'task':'archive export duplicate-free zip validation','is_decision_packet_request':True})
 results['deny_missing_packet']=router.validate_decision_packet(ROOT, {'task':'archive export duplicate-free zip validation','used_tool':'python zipfile'})
 valid_packet={'task':'archive export duplicate-free zip validation','turn_text':'MetaBlooms OS governance tool export','explicit_meta_task':True,'authority_boot_verified':True,'sandbox_policy_loaded':True,'tool_selection_decision_packet_written':True,'will_use_tool':True,'used_tool':results['router_archive']['selected_method'],'router_decision':'os_governance','web_sources':['NIST','OpenAI','OWASP'],'SEE_artifact':'runtime/research/H0C1_TOOL_SELECTION_ROUTER_SEE_v1.json','CE_artifact':'runtime/research/H0C1_TOOL_SELECTION_ROUTER_CE_v1.json','final_response_ready':False,'will_code':False,'will_modify_runtime':False}
 results['chat_valid']=chat.validate_turn(ROOT, valid_packet)
 invalid=dict(valid_packet); invalid.pop('tool_selection_decision_packet_written',None)
 results['chat_deny_missing_tool_packet']=chat.validate_turn(ROOT, invalid)
 results['boot_loader']=loader.validate_boot_critical_governance(ROOT, run_scatter=False)
 errors=[]
 if results['router_archive'].get('decision')!='ALLOW': errors.append('router_archive_not_allowed')
 if results['deny_missing_packet'].get('decision')!='DENY': errors.append('missing_packet_not_denied')
 if results['chat_valid'].get('decision')!='ALLOW': errors.append('chat_valid_not_allowed')
 if results['chat_deny_missing_tool_packet'].get('decision')!='DENY': errors.append('chat_missing_packet_not_denied')
 if results['boot_loader'].get('decision')!='ALLOW': errors.append('boot_loader_not_allowed')
 out={'status':'PASS' if not errors else 'FAIL','errors':errors,'results':results}
 p=ROOT/'runtime/evals/tool_governance/H0C1_TOOL_SELECTION_BEHAVIOR_TEST_RESULTS.json'; _mb_atomic_json.write_json_file(p, out, operation_id='H0C1_TOOL_SELECTION_BEHAVIOR_TEST_RESULTS', allowed_roots=[str(ROOT)], indent=2, sort_keys=True)
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not errors else 1
if __name__=='__main__': raise SystemExit(main())
