#!/usr/bin/env python3
import argparse, json, zipfile, hashlib, tempfile
from pathlib import Path

def sha256_path(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--packet', required=True)
    ap.add_argument('--json', action='store_true')
    ns=ap.parse_args()
    packet=Path(ns.packet)
    required=[
      'CURRENT_FULL_AUTHORITY_POINTER_v1.json',
      'OPEN_OPERATOR_VISUAL_TRACKER.html',
      'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json',
      'runtime/state/operator_surface/AUDIT_QUERY_PACKS_LATEST.json',
      'runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json',
      'runtime/state/operator_surface/OPERATOR_ONLY_AUDIT_PACKET_MANIFEST_LATEST.json',
      'runtime/traces/observability/AUDIT_COMMAND_EXECUTION_REPLAY_LATEST.json'
    ]
    result={'artifact_type':'MB_OPERATOR_PACKET_BOOTSTRAP_SMOKE_RESULT.v1','packet_zip':str(packet),'packet_sha256':sha256_path(packet) if packet.exists() else None,'zip_integrity':'FAIL','missing_required_members':[], 'audit_commands':0, 'failed_audit_commands':None, 'full_os_locator':None, 'issues':[], 'verdict':'DENY'}
    if not packet.exists():
        result['issues'].append('packet_missing')
    else:
        with zipfile.ZipFile(packet) as z:
            bad=z.testzip()
            names=set(z.namelist())
            result['zip_integrity']='PASS' if bad is None else f'FAIL:{bad}'
            result['missing_required_members']=[m for m in required if m not in names]
            if result['missing_required_members']:
                result['issues'].append('missing_required_members')
            try:
                ptr=json.loads(z.read('CURRENT_FULL_AUTHORITY_POINTER_v1.json'))
                result['full_os_locator']=ptr.get('authority_zip') or ptr.get('export_zip') or ptr.get('final_export_zip')
                if not result['full_os_locator']:
                    result['issues'].append('full_os_locator_missing')
            except Exception as e:
                result['issues'].append('pointer_unreadable:'+str(e))
            try:
                replay=json.loads(z.read('runtime/traces/observability/AUDIT_COMMAND_EXECUTION_REPLAY_LATEST.json'))
                cmds=replay.get('command_replays',[])
                result['audit_commands']=len(cmds)
                fails=[c for c in cmds if c.get('verdict')!='PASS' or c.get('missing_paths')]
                result['failed_audit_commands']=len(fails)
                if fails: result['issues'].append('audit_command_replay_failures')
            except Exception as e:
                result['issues'].append('audit_replay_unreadable:'+str(e))
    if result['zip_integrity']=='PASS' and not result['missing_required_members'] and result['audit_commands']>=6 and result['failed_audit_commands']==0 and result['full_os_locator'] and not result['issues']:
        result['verdict']='PASS'
    if ns.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(result['verdict'])
    return 0 if result['verdict']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
