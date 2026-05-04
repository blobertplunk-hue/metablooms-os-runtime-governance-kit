#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List
import datetime, importlib.util, json, re
KERNEL_ID='CHAT_GOVERNANCE_KERNEL_v1.3_TOOL_SELECTOR_ROOT_RESOLVED'
META_TASK_MARKERS={'metablooms','os','governance','kernel','cartridge','runtime','boot','bundle','export','receipt','handoff','tracker'}
RESEARCH_TRIGGERS={'research','current','latest','web','see','external','evidence','architecture','policy','standards'}
SANDBOX_MODULE_REL='runtime/governance/sandbox_tool_governance_v1.py'
TOOL_SELECTOR_REL='runtime/governance/tool_selection_evidence_router_v1.py'
def _now(): return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z'
def resolve_root(start: str|Path)->Path:
 p=Path(start).resolve()
 if p.is_file(): p=p.parent
 candidates=[p,p/'Metablooms_OS',p.parent]
 cur=p
 for _ in range(8): candidates.append(cur); cur=cur.parent
 for c in candidates:
  if (c/'0_kernel').exists() and (c/'runtime').exists(): return c
 return p
def _tokens(text:str): return set(re.findall(r"[a-z0-9_]+", (text or '').lower()))
def _exists(root,rel):
 try: return bool(rel) and (root/rel).exists()
 except Exception: return False
def _load(path,name):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def classify_turn(turn_text, explicit_meta=False):
 text=(turn_text or '').lower(); toks=_tokens(text); marker_hits=sorted(m for m in META_TASK_MARKERS if m in toks or (m=='os' and 'os' in toks)); research_hits=sorted(r for r in RESEARCH_TRIGGERS if r in toks)
 is_meta=bool(explicit_meta or marker_hits)
 requires_research=bool(is_meta and (research_hits or any(k in toks for k in ['implement','plan','harden','repair','router','gate','sandbox','tool'])))
 route='non_meta'
 if is_meta:
  if any(k in text for k in ['html','google sites','activity']): route='html_activity'
  elif any(k in toks for k in ['csv','blooket']): route='csv_blooket'
  elif any(k in toks for k in ['docx','document','purple']): route='docx'
  elif any(k in toks for k in ['boot','os','governance','kernel','gate','router','export','bundle','sandbox','tool']): route='os_governance'
  elif any(k in toks for k in ['research','see','ce']): route='research_ce'
  else: route='governance_planning'
 return {'is_meta_task':is_meta,'marker_hits':marker_hits,'requires_research':requires_research,'research_hits':research_hits,'route':route}
def validate_turn(root, packet:Dict[str,Any]):
 root=resolve_root(root); errors:List[str]=[]; warnings:List[str]=[]; classification=packet.get('classification') or classify_turn(packet.get('turn_text',''),bool(packet.get('explicit_meta_task')))
 if not classification.get('is_meta_task'): return {'kernel_id':KERNEL_ID,'timestamp_utc':_now(),'decision':'ALLOW','classification':classification,'errors':[],'warnings':['non_meta_task_kernel_pass_through']}
 required=['0_kernel/chat_governance/CHAT_GOVERNANCE_KERNEL_v1.json','0_kernel/chat_governance/TURN_LIFECYCLE_CONTRACT_v1.json','0_kernel/chat_governance/ROUTER_CONTRACT_v1.json','governance/invariants/CHAT_GOVERNANCE_KERNEL_ALWAYS_ON_v1.json','runtime/governance/chat_governance_kernel_v1.py',SANDBOX_MODULE_REL,TOOL_SELECTOR_REL,'0_kernel/tool_governance/TOOL_SELECTION_EVIDENCE_ROUTER_v1.json','0_kernel/tool_governance/TOOL_METHOD_REGISTRY_v1.json','0_kernel/tool_governance/TOOL_DECISION_PACKET_SCHEMA_v1.json','0_kernel/sandbox_governance/SANDBOX_TOOL_USE_POLICY_v1.json','0_kernel/sandbox_governance/SANDBOX_BOOTSTRAP_CONTRACT_v1.json','0_kernel/sandbox_governance/SANDBOX_METHOD_ROUTER_v1.json','0_kernel/sandbox_governance/CODING_PLAN_REQUIREMENT_v1.json']
 for rel in required:
  if not _exists(root,rel): errors.append('missing_boot_critical_governance_path:'+rel)
 if not packet.get('authority_boot_verified'): errors.append('authority_boot_not_verified')
 if not packet.get('sandbox_policy_loaded'): errors.append('sandbox_policy_not_loaded_at_chat_start')
 if _exists(root,SANDBOX_MODULE_REL):
  sres=_load(root/SANDBOX_MODULE_REL,'sandbox_tool_governance_v1_imported').validate_sandbox_plan(root,dict(packet,metablooms_turn=True))
  if sres.get('decision')!='ALLOW': errors += ['sandbox:'+e for e in sres.get('errors',[])]
 if packet.get('will_use_tool') or packet.get('used_tool') or packet.get('will_modify_runtime') or packet.get('will_code') or packet.get('promotion_requested'):
  if not packet.get('tool_selection_decision_packet_written'): errors.append('tool_selection_decision_packet_missing')
  if _exists(root,TOOL_SELECTOR_REL):
   tres=_load(root/TOOL_SELECTOR_REL,'tool_selection_router_imported').validate_decision_packet(root,dict(packet, is_decision_packet_request=False))
   if tres.get('decision')!='ALLOW': errors += ['tool_selector:'+e for e in tres.get('errors',[])]
 if not packet.get('router_decision'): errors.append('router_decision_missing')
 elif packet.get('router_decision')!=classification.get('route') and packet.get('router_override_justification') is None: errors.append(f"router_decision_mismatch:{packet.get('router_decision')}!={classification.get('route')}")
 if classification.get('requires_research') or packet.get('SEE_required'):
  if not packet.get('web_sources'): errors.append('SEE_required_but_web_sources_missing')
  if not packet.get('SEE_artifact'): errors.append('SEE_required_but_SEE_artifact_missing')
  if not packet.get('CE_artifact'): errors.append('SEE_required_but_CE_artifact_missing')
 if packet.get('will_implement') or packet.get('will_modify_runtime') or packet.get('will_code'):
  for key in ['implementation_plan_artifact','coding_plan_artifact','test_plan_artifact','fixture_manifest_artifact','sandbox_tool_plan_artifact']:
   if not packet.get(key): errors.append('implementation_missing_'+key)
 if packet.get('final_response_ready'):
  if not packet.get('tracker_preview_rendered'): errors.append('final_response_without_tracker_preview')
  if not packet.get('receipt_artifact'): errors.append('final_response_without_receipt')
  if not packet.get('handoff_artifact'): errors.append('final_response_without_handoff')
  if not packet.get('sandbox_receipt_artifact'): errors.append('final_response_without_sandbox_receipt')
 if packet.get('promotion_requested'):
  for key in ['location_verification_artifact','behavior_test_artifact','whole_system_export_path','whole_system_export_sha256','fresh_extract_test_artifact']:
   if not packet.get(key): errors.append('promotion_missing_'+key)
 return {'kernel_id':KERNEL_ID,'timestamp_utc':_now(),'root':str(root),'decision':'DENY' if errors else 'ALLOW','classification':classification,'errors':errors,'warnings':warnings}
def validate_packet_file(root,packet_path): return validate_turn(root,json.loads(Path(packet_path).read_text()))
if __name__=='__main__':
 import argparse, sys
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--packet',required=True); ns=ap.parse_args(); res=validate_packet_file(ns.root,ns.packet); print(json.dumps(res,indent=2)); sys.exit(0 if res.get('decision')=='ALLOW' else 1)
