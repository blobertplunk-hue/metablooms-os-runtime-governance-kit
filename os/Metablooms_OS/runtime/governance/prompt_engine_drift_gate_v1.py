#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

def validate_prompt_engine_drift(root, packet):
    root=Path(root); errors=[]
    for k in ['task_type','selected_profile','optimized_prompt','improvement_rationale','validation_checks']:
        if k not in packet: errors.append('missing_field:'+k)
    reg_path=root/'runtime/cartridges/prompt_governance_v1/PROMPT_PROFILE_REGISTRY_v1.json'
    profiles=set()
    if reg_path.exists():
        data=json.loads(reg_path.read_text()); raw=data.get('profiles', [])
        if isinstance(raw, list):
            for x in raw:
                if isinstance(x, dict): profiles.add(x.get('profile_id') or x.get('id') or x.get('name'))
                elif isinstance(x, str): profiles.add(x)
        elif isinstance(raw, dict): profiles=set(raw.keys())
    if packet.get('selected_profile') and profiles and packet.get('selected_profile') not in profiles:
        errors.append('unregistered_profile:'+str(packet.get('selected_profile')))
    checks=packet.get('validation_checks') or {}
    if checks and not all(bool(v) for v in checks.values()): errors.append('validation_check_failed')
    return {'decision':'DENY' if errors else 'ALLOW','errors':errors,'drift_flags':errors}

if __name__=='__main__':
    import sys
    root=sys.argv[1] if len(sys.argv)>1 else Path.cwd()
    packet=json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv)>2 else {}
    r=validate_prompt_engine_drift(root, packet); print(json.dumps(r, indent=2)); raise SystemExit(0 if r['decision']=='ALLOW' else 1)
