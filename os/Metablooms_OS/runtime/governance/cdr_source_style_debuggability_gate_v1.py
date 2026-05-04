#!/usr/bin/env python3
"""Purpose: Validate CDR source-style and debuggability packets.
Inputs: JSON packet containing module headers and denial/debug contract.
Outputs: ALLOW/DENY with header or debug gaps.
Failure modes: Missing required header fields or structured denial reasons deny.
Debuggability: Reports each missing header field explicitly.
"""
import json, sys
REQ=['Purpose','Inputs','Outputs','Failure modes','Debuggability']
def evaluate(pkt):
    reasons=[]
    for mod,h in pkt.get('module_headers',{}).items():
        for r in REQ:
            if not h.get(r): reasons.append(f'missing_header:{mod}:{r}')
    contract=pkt.get('structured_denial_contract',{})
    if not any(contract.get(k) for k in ['reasons','violations','gaps']): reasons.append('missing_structured_denial_reasons')
    if pkt.get('warnings_after',0)>pkt.get('warnings_before',0): reasons.append('warnings_increased')
    return {'verdict':'DENY' if reasons else 'ALLOW','reasons':reasons}
if __name__=='__main__': print(json.dumps(evaluate(json.load(open(sys.argv[1]))),indent=2))
