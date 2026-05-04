#!/usr/bin/env python3
"""
CDR Linchpin Recursive Audit Gate v1.
Purpose: Validate that CDR audits and improves itself as a linchpin coding-quality system.
Inputs: JSON packet path containing audit_cycles, gap_ledger, stop rule, inventory, eval summary.
Outputs: JSON decision packet with ALLOW or DENY and machine-readable reasons.
Failure modes: DENY on missing fields, missing audit cycles, invalid high-value gap handling, or missing proof.
Debuggability: emits exact reason codes, missing cycles, and unhandled high-value gaps.
"""
from __future__ import annotations
import json, sys
from pathlib import Path
REQUIRED_CYCLES={
 'definition_quality','code_acceptance','risk_tiered_tests','source_level_self_audit','style_debuggability','interface_contract','security_observability','static_complexity','scanner_baseline','scanner_profiles'
}
REQUIRED_FIELDS=['stage','audit_cycles','gap_ledger','high_value_stop_rule','source_inventory','eval_summary','world_class_basis','next_stage']
def _load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def evaluate(packet):
    reasons=[]
    for f in REQUIRED_FIELDS:
        if f not in packet: reasons.append(f'missing_field:{f}')
    cycles=set(packet.get('audit_cycles',[]))
    missing=sorted(REQUIRED_CYCLES-cycles)
    for c in missing: reasons.append(f'missing_cycle:{c}')
    stop=packet.get('high_value_stop_rule',{})
    if not stop.get('defined') or 'benefit_score' not in json.dumps(stop): reasons.append('missing_high_value_stop_rule')
    inv=packet.get('source_inventory',{})
    if inv.get('cdr_files_scanned',0) < 1 or inv.get('gate_files_scanned',0) < 1: reasons.append('missing_source_inventory')
    ev=packet.get('eval_summary',{})
    if ev.get('passed',0) < ev.get('total',1): reasons.append('evals_not_all_passing')
    basis=packet.get('world_class_basis',[])
    if len(basis) < 3: reasons.append('missing_world_class_basis')
    next_stage=packet.get('next_stage')
    for g in packet.get('gap_ledger',[]):
        hv=g.get('benefit_score',0)>=3 and g.get('risk_score',9)<=2 and g.get('scope_cost',9)<=2 and g.get('stage_fit') is True
        if hv and g.get('status') not in {'closed','scheduled'}:
            reasons.append('open_high_value_gap_without_next_stage:'+str(g.get('id','unknown')))
        if hv and not next_stage:
            reasons.append('missing_next_stage_for_high_value_gap')
    decision='DENY' if reasons else 'ALLOW'
    return {'decision':decision,'reasons':reasons,'missing_cycles':missing,'stage':packet.get('stage')}
def main(argv):
    if len(argv)<2:
        print(json.dumps({'decision':'DENY','reasons':['missing_packet_path']})); return 2
    result=evaluate(_load(argv[1])); print(json.dumps(result, indent=2, sort_keys=True)); return 0 if result['decision']=='ALLOW' else 1
if __name__=='__main__': raise SystemExit(main(sys.argv))
