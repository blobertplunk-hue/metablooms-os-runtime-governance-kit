#!/usr/bin/env python3
"""
CDR lint/security scanner integration gate.
Purpose: deny code acceptance when scanner baseline evidence is missing, stale, or violates risk-tier policy.
Inputs: CDRLintSecurityScannerPacket_v1 JSON path or packet object.
Outputs: JSON decision with ALLOW/DENY, reasons, findings, and remediation hints.
Failure modes: invalid JSON/schema -> DENY; missing baseline -> DENY; zero-tolerance findings -> DENY.
Debuggability: each denial includes reason codes and finding ids.
"""
import json, sys
from pathlib import Path

ZERO={'syntax_error','dynamic_exec','shell_true_subprocess','secret_literal','unsafe_path_traversal_pattern'}
THRESHOLDS={
 'LOW': {'max_complexity':15,'max_todo':5,'deny_levels':set()},
 'MEDIUM': {'max_complexity':12,'max_todo':3,'deny_levels':{'zero_tolerance'}},
 'HIGH': {'max_complexity':10,'max_todo':1,'deny_levels':{'zero_tolerance','high'}},
 'CRITICAL': {'max_complexity':8,'max_todo':0,'deny_levels':{'zero_tolerance','high','medium'}},
}
REQUIRED_BASELINE=['source_root','generated_at_utc','tool_availability','files_scanned','findings','summary','source_hashes']

def load_packet(arg):
    if isinstance(arg, dict):
        return arg
    return json.loads(Path(arg).read_text(encoding='utf-8'))

def evaluate(packet):
    reasons=[]; denied_findings=[]
    if packet.get('schema')!='CDRLintSecurityScannerPacket_v1':
        reasons.append('invalid_schema_name')
    tier=packet.get('risk_tier')
    if tier not in THRESHOLDS:
        reasons.append('invalid_risk_tier'); tier='CRITICAL'
    baseline=packet.get('baseline') or {}
    for k in REQUIRED_BASELINE:
        if k not in baseline:
            reasons.append('missing_baseline_field:'+k)
    if not baseline.get('source_hashes'):
        reasons.append('missing_source_hashes')
    availability=baseline.get('tool_availability') or {}
    if not availability.get('stdlib_ast_static_scan',{}).get('available'):
        reasons.append('missing_required_stdlib_ast_static_scan')
    if not packet.get('test_binding',{}).get('eval_path'):
        reasons.append('missing_test_binding_eval_path')
    findings=baseline.get('findings') or []
    th=THRESHOLDS[tier]
    max_complexity=0; todo_count=0
    for f in findings:
        ft=f.get('type')
        sev=f.get('severity','low')
        if ft in ZERO:
            denied_findings.append(f.get('id',ft)); reasons.append('zero_tolerance_finding:'+ft)
        if tier in ('HIGH','CRITICAL') and sev=='high':
            denied_findings.append(f.get('id',ft)); reasons.append('high_severity_finding:'+str(ft))
        if tier=='CRITICAL' and sev=='medium':
            denied_findings.append(f.get('id',ft)); reasons.append('critical_tier_medium_finding:'+str(ft))
        if ft=='function_complexity':
            max_complexity=max(max_complexity,int(f.get('value',0)))
        if ft=='todo_debt':
            todo_count+=int(f.get('value',1))
    if max_complexity>th['max_complexity']:
        reasons.append(f'complexity_over_threshold:{max_complexity}>{th["max_complexity"]}')
    if todo_count>th['max_todo']:
        reasons.append(f'todo_over_threshold:{todo_count}>{th["max_todo"]}')
    return {
        'schema':'CDRLintSecurityScannerGateResult_v1',
        'decision':'DENY' if reasons else 'ALLOW',
        'risk_tier':tier,
        'reasons':sorted(set(reasons)),
        'denied_findings':sorted(set(denied_findings)),
        'summary':{'finding_count':len(findings),'max_complexity':max_complexity,'todo_count':todo_count}
    }

def main(argv):
    if len(argv)<2:
        print(json.dumps({'decision':'DENY','reasons':['missing_packet_path']})); return 2
    res=evaluate(load_packet(argv[1]))
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res['decision']=='ALLOW' else 1
if __name__=='__main__':
    raise SystemExit(main(sys.argv))
