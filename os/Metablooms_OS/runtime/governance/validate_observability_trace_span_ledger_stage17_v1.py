#!/usr/bin/env python3
import json, hashlib, zipfile, argparse, sys
from pathlib import Path

def sha256_path(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def load(root, rel):
    return json.loads((Path(root)/rel).read_text(encoding='utf-8'))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args()
    root=Path(args.root)
    issues=[]
    required = [
      'runtime/traces/observability/AUDIT_COMMAND_EXECUTION_REPLAY_LATEST.json',
      'runtime/state/operator_surface/OPERATOR_ONLY_AUDIT_PACKET_MANIFEST_LATEST.json',
      'runtime/traces/observability/OPERATOR_ONLY_AUDIT_PACKET_CONTAINMENT_PROOF_LATEST.external.json',
      'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json',
      'runtime/state/operator_surface/OPERATOR_EXPORT_PACKET_LATEST.json',
      '0_kernel/registry/observability/MB_AUDIT_COMMAND_EXECUTION_REPLAY_SCHEMA_v1.json',
      '0_kernel/registry/observability/MB_OPERATOR_BUNDLE_PARTITION_SCHEMA_v1.json',
      '0_kernel/registry/observability/MB_AUDIT_COMMAND_REPLAY_AND_BUNDLE_PARTITION_POLICY_v1.json',
      'OPEN_OPERATOR_VISUAL_TRACKER.html'
    ]
    for rel in required:
        if not (root/rel).exists(): issues.append({'type':'missing_required_artifact','path':rel})
    if not issues:
        replay=load(root,'runtime/traces/observability/AUDIT_COMMAND_EXECUTION_REPLAY_LATEST.json')
        surface=load(root,'runtime/state/operator_surface/AUDIT_QUERY_COMMAND_SURFACE_LATEST.json')
        manifest=load(root,'runtime/state/operator_surface/OPERATOR_ONLY_AUDIT_PACKET_MANIFEST_LATEST.json')
        proof=load(root,'runtime/traces/observability/OPERATOR_ONLY_AUDIT_PACKET_CONTAINMENT_PROOF_LATEST.external.json')
        if replay.get('verdict')!='PASS': issues.append({'type':'replay_not_pass','verdict':replay.get('verdict')})
        if replay.get('command_count') != surface.get('command_count'):
            issues.append({'type':'command_count_mismatch','replay':replay.get('command_count'),'surface':surface.get('command_count')})
        failed=[c for c in replay.get('command_replays',[]) if c.get('verdict')!='PASS']
        if failed: issues.append({'type':'failed_command_replays','count':len(failed)})
        if manifest.get('verdict')!='PASS': issues.append({'type':'partition_manifest_not_pass'})
        if proof.get('verdict')!='PASS': issues.append({'type':'operator_packet_proof_not_pass'})
        if proof.get('duplicate_members') != 0: issues.append({'type':'operator_packet_duplicate_members','count':proof.get('duplicate_members')})
        if proof.get('bad_member') is not None: issues.append({'type':'operator_packet_bad_member','bad_member':proof.get('bad_member')})
        tracker=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8', errors='replace')
        for marker in ['Stage 17', 'Audit Command Replay', 'Operator-only Audit Packet', 'data-section="audit-command-replay"']:
            if marker not in tracker: issues.append({'type':'tracker_marker_missing','marker':marker})
    out={'artifact_type':'MB_TRACE_SPAN_LEDGER_STAGE17_VALIDATION.v1','verdict':'PASS' if not issues else 'FAIL','issues':issues}
    print(json.dumps(out, indent=2, sort_keys=True) if args.json else out['verdict'])
    return 0 if not issues else 1
if __name__ == '__main__':
    raise SystemExit(main())
