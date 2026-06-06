#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, time
from pathlib import Path

def sha(p: Path) -> str:
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def load(p: Path): return json.loads(p.read_text(encoding='utf-8'))
def dump(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    Path(str(p)+'.sha256').write_text(f'{sha(p)}  {p.name}\n', encoding='utf-8')

def bind(root: Path, path: str):
    p=root/path
    return {'path':path,'exists':p.is_file(),'size_bytes':p.stat().st_size if p.exists() else 0,'sha256':sha(p) if p.is_file() else None}

def first_result_paths(pack):
    out=[]
    for r in pack.get('results',[])[:6]:
        p=r.get('path')
        if p and p not in out: out.append(p)
    return out

def build(root: Path):
    ts=time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    packs_path='runtime/state/operator_surface/AUDIT_QUERY_PACKS_LATEST.json'
    packs=load(root/packs_path)
    by_id={p.get('query_id'):p for p in packs.get('packs',[])}
    pack_defs=[
      ('show_audit_promoted_evidence_recovery','Show promoted evidence recovery','Show audit pack: promoted evidence recovery','show_audit_pack','audit_promoted_evidence_recovery'),
      ('show_audit_export_binding','Show export binding evidence','Show audit pack: export binding','show_audit_pack','audit_export_binding'),
      ('show_audit_blocker_or_failure','Show blocker/failure evidence','Show audit pack: blocker or failure','show_blocker_evidence','audit_blocker_or_failure'),
      ('show_audit_boot_guidance','Show current boot guidance','Show audit pack: boot guidance','show_current_boot_guidance','audit_boot_guidance'),
      ('show_audit_stage_validation','Show stage validation evidence','Show audit pack: stage validation','show_stage_validation','audit_stage_validation'),
      ('show_audit_trace_waterfall','Show trace waterfall evidence','Show audit pack: trace waterfall','show_trace_waterfall','audit_trace_waterfall')]
    export_defs=[
      ('export_promoted_evidence_packet','Export promoted evidence packet','Export evidence packet: promoted evidence recovery','export_evidence_packet','audit_promoted_evidence_recovery',['runtime/receipts/pinned_evidence/PINNED_EVIDENCE_RECEIPT_LATEST.json','runtime/traces/observability/PROMOTED_EVIDENCE_RECOVERY_REPLAY_LATEST.json','runtime/traces/observability/PINNED_EVIDENCE_EXPORT_BINDING_LATEST.json']),
      ('export_boot_guidance_packet','Export boot guidance packet','Export evidence packet: current boot guidance','export_evidence_packet','audit_boot_guidance',['runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json','runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.md','runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py']),
      ('export_stage_validation_packet','Export stage validation packet','Export evidence packet: stage validation','export_evidence_packet','audit_stage_validation',['runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE15_RECOVERY_REPLAY_AUDIT_QUERY_VALIDATION_LATEST.json','runtime/state/operator_surface/AUDIT_QUERY_PACKS_LATEST.json'])]
    commands=[]
    issues=[]
    for cid,label,phrase,action,pid in pack_defs:
        pack=by_id.get(pid)
        if not pack: issues.append({'code':'missing_source_pack','command_id':cid,'source_pack_id':pid}); paths=[]
        else: paths=first_result_paths(pack)
        commands.append({'command_id':cid,'label':label,'intent':phrase,'operator_phrase':phrase,'action':action,'source_pack_id':pid,'output_packet_path':None,'evidence_paths':paths,'fail_closed_if':['source pack missing','evidence path missing']})
    for cid,label,phrase,action,pid,base_paths in export_defs:
        pack=by_id.get(pid)
        paths=[] if not pack else first_result_paths(pack)
        for p in base_paths:
            if p not in paths: paths.insert(0,p)
        packet_path=f'runtime/exports/operator_packets/{cid}.json'
        commands.append({'command_id':cid,'label':label,'intent':phrase,'operator_phrase':phrase,'action':action,'source_pack_id':pid,'output_packet_path':packet_path,'evidence_paths':paths,'fail_closed_if':['source pack missing','artifact binding missing','sha mismatch']})
    command_surface={'artifact_type':'MB_AUDIT_QUERY_COMMAND_SURFACE.v1','stage_id':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE16_AUDIT_QUERY_COMMAND_SURFACE_AND_OPERATOR_EXPORT_PACKET','created_utc':ts,'source_audit_query_packs':packs_path,'source_audit_query_packs_sha256':sha(root/packs_path),'command_count':len(commands),'commands':commands,'issues':issues,'verdict':'PASS' if not issues else 'FAIL'}
    dump(root/'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json', command_surface)
    md=['# Audit Query Command Surface','','Use these stable phrases in a future chat/operator surface. They map to audit packs and export-bound evidence packets.','']
    for c in commands:
        md.append(f"## `{c['command_id']}`")
        md.append(f"- Phrase: **{c['operator_phrase']}**")
        md.append(f"- Action: `{c['action']}`")
        md.append(f"- Source pack: `{c['source_pack_id']}`")
        if c['output_packet_path']: md.append(f"- Output packet: `{c['output_packet_path']}`")
        md.append('')
    dump(root/'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.md', '\n'.join(md)+'\n')
    packets=[]
    for c in commands:
        if c['action']!='export_evidence_packet': continue
        bindings=[]; bind_issues=[]
        for p in c['evidence_paths']:
            b=bind(root,p); bindings.append(b)
            if not b['exists']: bind_issues.append({'code':'missing_binding','path':p})
        manifest={'packet_id':c['command_id'],'command_id':c['command_id'],'label':c['label'],'created_utc':ts,'source_pack_id':c['source_pack_id'],'artifact_bindings':bindings}
        manifest_bytes=json.dumps(manifest, sort_keys=True).encode('utf-8')
        manifest['manifest_sha256']=hashlib.sha256(manifest_bytes).hexdigest()
        manifest['issues']=bind_issues
        manifest['verdict']='PASS' if not bind_issues else 'FAIL'
        dump(root/c['output_packet_path'], manifest)
        packets.append(manifest)
    export_packet={'artifact_type':'MB_OPERATOR_EXPORT_PACKET.v1','stage_id':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE16_AUDIT_QUERY_COMMAND_SURFACE_AND_OPERATOR_EXPORT_PACKET','packet_id':'OPERATOR_AUDIT_EXPORT_PACKET_STAGE16','created_utc':ts,'source_command_surface':'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json','packets':packets,'issues':[i for p in packets for i in p.get('issues',[])],'verdict':'PASS' if command_surface['verdict']=='PASS' and all(p['verdict']=='PASS' for p in packets) else 'FAIL'}
    dump(root/'runtime/state/operator_surface/OPERATOR_EXPORT_PACKET_LATEST.json', export_packet)
    md=['# Operator Export Packet','','Formal, SHA-bound evidence packets generated from the command surface.','']
    for p in packets:
        md.append(f"## `{p['packet_id']}` · {p['verdict']}")
        for b in p['artifact_bindings'][:10]: md.append(f"- `{b['path']}` · `{str(b.get('sha256'))[:16]}`")
        md.append('')
    dump(root/'runtime/state/operator_surface/OPERATOR_EXPORT_PACKET_LATEST.md', '\n'.join(md)+'\n')
    print(json.dumps({'verdict':export_packet['verdict'],'command_count':len(commands),'packet_count':len(packets)}, sort_keys=True))
    return 0 if export_packet['verdict']=='PASS' else 1

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); args=ap.parse_args()
    raise SystemExit(build(Path(args.root)))
if __name__=='__main__': main()
