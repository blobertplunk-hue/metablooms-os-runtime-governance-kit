#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, sys
POLICY_ID='PYTHON_RESILIENT_EXECUTION_POLICY_v1'
ALLOWED_LANES={'shell_coreutils','jq_node','python3_dash_S_stdlib','normal_python_quarantine'}
RANK={'shell_coreutils':1,'jq_node':2,'python3_dash_S_stdlib':3,'normal_python_quarantine':4}
def validate_request(request):
    errors=[]; warnings=[]
    probe=request.get('tool_probe_path')
    if not probe: errors.append('missing_tool_probe_path')
    elif not Path(probe).exists(): errors.append('tool_probe_path_not_found')
    lane=request.get('execution_lane')
    if lane not in ALLOWED_LANES: errors.append('invalid_or_missing_execution_lane')
    fallbacks=request.get('fallback_lanes') or []
    if not isinstance(fallbacks,list) or not fallbacks: errors.append('missing_fallback_lanes')
    if request.get('failure_lane_switch_required') is not True: errors.append('failure_lane_switch_required_not_true')
    if request.get('archive_or_filesystem_work') is True and lane in ('normal_python_quarantine',):
        errors.append('archive_filesystem_work_must_not_default_to_normal_python')
    if request.get('normal_python_used') is True:
        timeout=request.get('timeout_seconds')
        if not isinstance(timeout,(int,float)) or timeout<=0 or timeout>45: errors.append('normal_python_requires_timeout_le_45')
        if not request.get('alternate_verifier_lane'): errors.append('normal_python_requires_alternate_verifier_lane')
    if lane=='python3_dash_S_stdlib' and request.get('timeout_seconds') and request.get('timeout_seconds')>45:
        errors.append('python3_dash_S_timeout_too_high')
    return {'policy_id':POLICY_ID,'decision':'ALLOW' if not errors else 'DENY','errors':errors,'warnings':warnings,'lane':lane,'fallback_lanes':fallbacks}
if __name__=='__main__':
    req=json.loads(Path(sys.argv[1]).read_text()) if len(sys.argv)>1 else json.load(sys.stdin)
    result=validate_request(req)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['decision']=='ALLOW' else 1)
