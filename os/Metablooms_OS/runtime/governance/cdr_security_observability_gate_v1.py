#!/usr/bin/env python3
"""Purpose: Validate CDR security and observability evidence packets.
Inputs: JSON packet with risk tier, security controls, observability controls.
Outputs: ALLOW/DENY with missing-control reasons.
Failure modes: Missing required controls or critical non-waivable N/A denies.
Debuggability: Names each absent control.
"""
import json, sys
SEC=['input_validation','access_control','secret_data_protection','file_path_safety','safe_error_logging','root_cause_recurrence']
OBS=['trace_span_contract','error_attributes','correlation','exportable_formats','log_integrity']
def ok(v): return isinstance(v,dict) and v.get('status') in ['PASS','N/A_JUSTIFIED'] and v.get('evidence') and v.get('evidence')!='none'
def evaluate(pkt):
    reasons=[]; critical=pkt.get('risk_tier')=='CRITICAL'
    for c in SEC:
        v=pkt.get('security_controls',{}).get(c)
        if not ok(v): reasons.append(f'missing_security_control:{c}')
        if critical and isinstance(v,dict) and v.get('status')=='N/A_JUSTIFIED': reasons.append(f'critical_non_waivable_na:{c}')
    for c in OBS:
        v=pkt.get('observability_controls',{}).get(c)
        if not ok(v): reasons.append(f'missing_observability_control:{c}')
        if critical and isinstance(v,dict) and v.get('status')=='N/A_JUSTIFIED': reasons.append(f'critical_non_waivable_na:{c}')
    return {'verdict':'DENY' if reasons else 'ALLOW','reasons':reasons}
if __name__=='__main__': print(json.dumps(evaluate(json.load(open(sys.argv[1]))),indent=2))
