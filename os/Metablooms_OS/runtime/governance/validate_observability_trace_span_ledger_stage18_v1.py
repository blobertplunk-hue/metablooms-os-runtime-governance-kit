#!/usr/bin/env python3
import argparse, json, zipfile, hashlib
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true'); ns=ap.parse_args()
    root=Path(ns.root); issues=[]
    req=[
      '0_kernel/registry/observability/MB_OPERATOR_PACKET_BOOTSTRAP_SMOKE_SCHEMA_v1.json',
      '0_kernel/registry/observability/MB_SMALL_BUNDLE_FIRST_START_POLICY_v1.json',
      'runtime/governance/operator_packet_bootstrap_smoke_v1.py',
      'runtime/traces/observability/OPERATOR_PACKET_BOOTSTRAP_SMOKE_LATEST.json',
      'runtime/state/operator_surface/OPERATOR_PACKET_BOOTSTRAP_SMOKE_LATEST.md',
      'runtime/state/operator_surface/OPERATOR_ONLY_AUDIT_PACKET_MANIFEST_LATEST.json',
      'OPEN_OPERATOR_VISUAL_TRACKER.html'
    ]
    for r in req:
        if not (root/r).exists(): issues.append('missing:'+r)
    smoke={}
    p=root/'runtime/traces/observability/OPERATOR_PACKET_BOOTSTRAP_SMOKE_LATEST.json'
    if p.exists():
        smoke=json.loads(p.read_text())
        if smoke.get('verdict')!='PASS': issues.append('bootstrap_smoke_not_pass')
        if smoke.get('audit_commands',0)<6: issues.append('too_few_audit_commands')
        if smoke.get('failed_audit_commands') not in (0, None): issues.append('failed_audit_commands')
        if not smoke.get('full_os_locator'): issues.append('full_os_locator_missing')
    tracker=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(errors='ignore') if (root/'OPEN_OPERATOR_VISUAL_TRACKER.html').exists() else ''
    for marker in ['data-section="operator-packet-bootstrap"','Small Bundle First Start','OPERATOR_PACKET_BOOTSTRAP_SMOKE_LATEST.json']:
        if marker not in tracker: issues.append('tracker_marker_missing:'+marker)
    result={'artifact_type':'MB_TRACE_SPAN_LEDGER_STAGE18_VALIDATION.v1','stage':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE18_OPERATOR_PACKET_BOOTSTRAP_SMOKE_AND_SMALL_BUNDLE_FIRST_START','issues':issues,'verdict':'PASS' if not issues else 'DENY'}
    if ns.json: print(json.dumps(result, indent=2, sort_keys=True))
    else: print(result['verdict'])
    return 0 if not issues else 1
if __name__=='__main__': raise SystemExit(main())
