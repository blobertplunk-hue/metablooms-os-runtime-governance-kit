#!/usr/bin/env python3
from __future__ import annotations
import json, time, shutil, sys
from pathlib import Path
from typing import Any, Dict, List
ROUTER_ID='TOOL_SELECTION_EVIDENCE_ROUTER_v1.1'
def _now(): return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
def resolve_root(start: str|Path)->Path:
    p=Path(start).resolve()
    if p.is_file(): p=p.parent
    candidates=[p,p/'Metablooms_OS',p.parent]
    cur=p
    for _ in range(8):
        candidates.append(cur); cur=cur.parent
    for c in candidates:
        if (c/'0_kernel').exists() and (c/'runtime').exists(): return c
    return p
def _cmd_exists(cmd:str)->bool: return shutil.which(cmd) is not None
def probe_capabilities()->Dict[str,bool]:
    caps={'shell/coreutils':True,'artifact-specific libraries':True}
    for cmd,name in [('python3','python3 -S'),('zipinfo','zipinfo'),('unzip','unzip'),('zip','zip -0'),('jq','jq'),('node','node')]: caps[name]=_cmd_exists(cmd)
    caps['normal python']=False
    caps['python zipfile']=caps.get('python3 -S',False)
    return caps
def classify_task(packet:Dict[str,Any])->str:
    text=(packet.get('task') or packet.get('task_type') or packet.get('intent') or '').lower()
    if any(k in text for k in ['zip','archive','export','checksum','duplicate']): return 'archive_export'
    if any(k in text for k in ['json','manifest','registry','contract','governance','kernel','gate']): return 'structured_governance'
    if any(k in text for k in ['html','javascript','node']): return 'js_html'
    if any(k in text for k in ['docx','pdf','slides','spreadsheet','xlsx']): return 'artifact_specific'
    if any(k in text for k in ['research','web','see']): return 'research'
    return 'filesystem'
def select_tool(root: str|Path, packet:Dict[str,Any])->Dict[str,Any]:
    r=resolve_root(root); caps=probe_capabilities(); task=classify_task(packet); candidates=[]; rejected=[]
    def add(method, score, fit, allowed=True, reason=''):
        item={'method':method,'available':bool(caps.get(method,False)),'score':score,'fit':fit,'reason':reason}
        if allowed and item['available']: candidates.append(item)
        else: rejected.append(dict(item, rejected_reason=reason or 'not allowed or unavailable'))
    add('shell/coreutils',92 if task in {'filesystem'} else 70,'fast filesystem/checksum support')
    add('python3 -S',90 if task in {'structured_governance','archive_export'} else 78,'stdlib structured validation and scripts')
    add('python zipfile',94 if task=='archive_export' else 80,'duplicate-free stream archive work')
    add('zipinfo',86 if task=='archive_export' else 55,'central directory validation')
    add('unzip',60,'targeted extraction only', allowed=not packet.get('requires_full_extraction',False), reason='full extraction denied by latency policy' if packet.get('requires_full_extraction',False) else '')
    add('zip -0',65 if task=='archive_export' else 40,'low-compression archive fallback')
    add('jq',58 if task=='structured_governance' else 30,'JSON query validation')
    add('node',80 if task=='js_html' else 25,'JS/HTML tasks only')
    add('artifact-specific libraries',90 if task=='artifact_specific' else 20,'domain-specific artifact handling')
    add('normal python',10,'denied unless probed and necessary', allowed=bool(packet.get('normal_python_probe_passed') and packet.get('normal_python_necessary')), reason='normal python denied unless probed and necessary')
    candidates=sorted(candidates,key=lambda x:(x['score'],x['method']),reverse=True)
    selected=candidates[0] if candidates else None; errors=[]
    if not selected: errors.append('no_viable_tool_route')
    if packet.get('selected_method') and selected and packet['selected_method']!=selected['method'] and not packet.get('override_justification'):
        errors.append('requested_selected_method_mismatch_without_override')
    if packet.get('selected_method')=='normal python' and not packet.get('normal_python_probe_passed'):
        errors.append('normal_python_selected_without_probe')
    if packet.get('requires_full_extraction') and not packet.get('latency_exception'):
        errors.append('full_extraction_requested_without_latency_exception')
    return {'router_id':ROUTER_ID,'timestamp_utc':_now(),'root':str(r),'task_type':task,'decision':'DENY' if errors else 'ALLOW','selected_method':None if not selected else selected['method'],'candidate_methods':candidates,'rejected_methods':rejected,'observed_evidence':[{'capabilities':caps},{'policy':'lowest-latency verified correct route; normal python denied; full extraction denied'}],'errors':errors,'rationale':'selected highest-scoring available safe method for task type'}
def validate_decision_packet(root: str|Path, packet:Dict[str,Any])->Dict[str,Any]:
    base=select_tool(root,packet); errors=list(base.get('errors',[]))
    if not packet.get('tool_selection_decision_packet_written') and not packet.get('is_decision_packet_request'):
        errors.append('tool_selection_decision_packet_missing')
    if packet.get('used_tool') and packet.get('used_tool')!=base.get('selected_method') and not packet.get('override_justification'):
        errors.append('used_tool_did_not_match_router_selection')
    base['decision']='DENY' if errors else 'ALLOW'; base['errors']=errors
    return base
def write_decision_packet(root: str|Path, packet:Dict[str,Any], out_path: str|Path)->Dict[str,Any]:
    res=select_tool(root, packet); out=Path(out_path); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(res,indent=2,sort_keys=True),encoding='utf-8'); res['receipt_path']=str(out); return res
if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--packet'); ap.add_argument('--write')
    ns=ap.parse_args(); pkt=json.loads(Path(ns.packet).read_text()) if ns.packet else {'task':'archive export governance patch','is_decision_packet_request':True}
    res=write_decision_packet(ns.root,pkt,ns.write) if ns.write else select_tool(ns.root,pkt)
    print(json.dumps(res,indent=2,sort_keys=True)); sys.exit(0 if res.get('decision')=='ALLOW' else 1)
