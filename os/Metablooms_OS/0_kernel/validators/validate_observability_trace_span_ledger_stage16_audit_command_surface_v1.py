#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, sys
from pathlib import Path

def sha(p: Path):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def load(p: Path): return json.loads(p.read_text(encoding='utf-8'))

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true'); args=ap.parse_args(argv)
    root=Path(args.root); issues=[]; checks=[]
    required=[
      '0_kernel/registry/observability/MB_AUDIT_QUERY_COMMAND_SURFACE_SCHEMA_v1.json',
      '0_kernel/registry/observability/MB_OPERATOR_EXPORT_PACKET_SCHEMA_v1.json',
      '0_kernel/registry/observability/MB_AUDIT_QUERY_COMMAND_SURFACE_POLICY_v1.json',
      'runtime/governance/audit_query_command_surface_v1.py',
      'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json',
      'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.md',
      'runtime/state/operator_surface/OPERATOR_EXPORT_PACKET_LATEST.json',
      'runtime/state/operator_surface/OPERATOR_EXPORT_PACKET_LATEST.md',
      'OPEN_OPERATOR_VISUAL_TRACKER.html']
    for rel in required:
        ok=(root/rel).is_file(); checks.append({'check':'exists','path':rel,'passed':ok})
        if not ok: issues.append({'code':'missing_required_artifact','path':rel})
    if not issues:
        policy=load(root/'0_kernel/registry/observability/MB_AUDIT_QUERY_COMMAND_SURFACE_POLICY_v1.json')
        surface=load(root/'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json')
        packet=load(root/'runtime/state/operator_surface/OPERATOR_EXPORT_PACKET_LATEST.json')
        ids=[c.get('command_id') for c in surface.get('commands',[])]
        for rid in policy.get('required_command_ids',[]):
            if rid not in ids: issues.append({'code':'missing_required_command','command_id':rid})
        if surface.get('command_count') != len(surface.get('commands',[])): issues.append({'code':'command_count_mismatch'})
        packs=load(root/surface.get('source_audit_query_packs',''))
        pack_ids={p.get('query_id') for p in packs.get('packs',[])}
        for c in surface.get('commands',[]):
            if c.get('source_pack_id') not in pack_ids: issues.append({'code':'command_source_pack_missing','command_id':c.get('command_id')})
            if not c.get('operator_phrase'): issues.append({'code':'command_missing_operator_phrase','command_id':c.get('command_id')})
        if packet.get('verdict')!='PASS': issues.append({'code':'operator_export_packet_not_pass'})
        packet_paths=set()
        for p in packet.get('packets',[]):
            if p.get('verdict')!='PASS': issues.append({'code':'packet_not_pass','packet_id':p.get('packet_id')})
            packet_paths.add('runtime/exports/operator_packets/'+p.get('packet_id','')+'.json')
            for b in p.get('artifact_bindings',[]):
                bp=root/b.get('path','')
                if not bp.is_file(): issues.append({'code':'bound_artifact_missing','path':b.get('path')}); continue
                if b.get('sha256') != sha(bp): issues.append({'code':'bound_artifact_sha_mismatch','path':b.get('path')})
        for c in surface.get('commands',[]):
            pp=c.get('output_packet_path')
            if pp:
                if not (root/pp).is_file(): issues.append({'code':'command_output_packet_missing','command_id':c.get('command_id'),'path':pp})
        html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
        for marker in ['stage16-audit-query-command-surface','audit_query_command_cards','AUDIT_QUERY_COMMAND_SURFACE_LATEST.json','OPERATOR_EXPORT_PACKET_LATEST.json']:
            if marker not in html: issues.append({'code':'tracker_missing_marker','marker':marker})
    result={'artifact_type':'MB_TRACE_SPAN_LEDGER_STAGE16_AUDIT_QUERY_COMMAND_SURFACE_VALIDATION.v1','verdict':'PASS' if not issues else 'FAIL','issues':issues,'checks':checks}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not issues else 1
if __name__=='__main__':
    raise SystemExit(main())
