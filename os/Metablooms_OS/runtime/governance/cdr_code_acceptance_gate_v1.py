#!/usr/bin/env python3
"""Purpose: Validate CDR code acceptance packets.
Inputs: JSON packet path or object.
Outputs: ALLOW/DENY decision with reasons.
Failure modes: Missing dimensions/evidence or unresolved high-value work denies.
Debuggability: Reports exact missing dimensions and evidence gaps.
"""
import json, sys
REQ=['correctness','completeness','comprehensibility','debuggability','adaptability','security','observability','testability','integration','regression_resistance','recursive_improvement']
def evaluate(pkt):
    reasons=[]; dims=pkt.get('dimensions',{})
    for d in REQ:
        item=dims.get(d,{})
        if item.get('status')!='PASS': reasons.append(f'dimension_not_pass:{d}')
        if not item.get('evidence'): reasons.append(f'missing_evidence:{d}')
    rec=pkt.get('recursive_improvement',{})
    if rec.get('open_high_value_improvements') and not rec.get('handoff'):
        reasons.append('open_high_value_improvement_without_handoff')
    return {'verdict':'DENY' if reasons else 'ALLOW','reasons':reasons}
if __name__=='__main__':
    print(json.dumps(evaluate(json.load(open(sys.argv[1]))), indent=2))
