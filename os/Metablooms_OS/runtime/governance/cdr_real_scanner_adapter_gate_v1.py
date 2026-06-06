#!/usr/bin/env python3
"""
Purpose: Validate CDR real scanner adapter/install profile packets.
Inputs: JSON packet containing scanner profiles, availability, fallback baseline, install decision, and normalization contract.
Outputs: ALLOW/DENY JSON result with machine-readable reasons.
Failure modes: DENY on missing fallback, unsafe install decision, missing normalization contract, or scanner unavailable without fallback.
Debuggability: Emits reason codes SCAN_PROFILE_MISSING, FALLBACK_MISSING, UNSAFE_INSTALL, NORMALIZATION_MISSING, AVAILABILITY_BLOCKING.
"""
import json, sys
from pathlib import Path

REQUIRED_PROFILE_FIELDS = {"tool_id", "safe_default_command", "fallback", "outputs", "fail_closed_on"}
REQUIRED_NORM_FIELDS = {"raw_output_path", "normalized_packet_path", "source_hash_binding", "finding_severity_map"}

def evaluate(packet):
    reasons=[]
    profiles=packet.get('scanner_profiles') or []
    if not profiles:
        reasons.append('SCAN_PROFILE_MISSING')
    for idx,p in enumerate(profiles):
        missing=sorted(REQUIRED_PROFILE_FIELDS-set(p))
        if missing:
            reasons.append(f'SCAN_PROFILE_MISSING_FIELDS:{idx}:{"|".join(missing)}')
    fallback=packet.get('fallback_baseline') or {}
    if not fallback.get('exists') or not fallback.get('path') or not fallback.get('sha256'):
        reasons.append('FALLBACK_MISSING')
    for item in packet.get('availability') or []:
        if item.get('status') == 'UNAVAILABLE_BLOCKING':
            reasons.append('AVAILABILITY_BLOCKING:'+str(item.get('tool_id','unknown')))
    decision=packet.get('install_decision') or {}
    if decision.get('mode') == 'INSTALLED_AND_SMOKED' and not decision.get('bts_receipt'):
        reasons.append('UNSAFE_INSTALL:missing_bts_receipt')
    if decision.get('mode') not in {'NOT_INSTALLED_PROFILE_ONLY','INSTALLED_AND_SMOKED','BLOCKED_BY_POLICY'}:
        reasons.append('UNSAFE_INSTALL:unknown_mode')
    norm=packet.get('normalization_contract') or {}
    missing_norm=sorted(REQUIRED_NORM_FIELDS-set(norm))
    if missing_norm:
        reasons.append('NORMALIZATION_MISSING:'+'|'.join(missing_norm))
    verdict='DENY' if reasons else 'ALLOW'
    return {'schema':'CDRRealScannerAdapterGateResult_v1','verdict':verdict,'reasons':reasons,'checked_profiles':len(profiles)}

def main(argv=None):
    argv=argv or sys.argv[1:]
    if not argv:
        print(json.dumps({'verdict':'DENY','reasons':['NO_PACKET']})); return 2
    packet=json.loads(Path(argv[0]).read_text())
    result=evaluate(packet)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['verdict']=='ALLOW' else 1
if __name__ == '__main__':
    raise SystemExit(main())
