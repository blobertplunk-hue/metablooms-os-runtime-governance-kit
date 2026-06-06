#!/usr/bin/env python3
"""Purpose: Validate source-level CDR self-audit packets.
Inputs: JSON packet listing source files, findings, fixtures, and evals.
Outputs: ALLOW/DENY with specific coverage gaps.
Failure modes: Blocking findings, missing fixtures, or missing evals deny.
Debuggability: Returns counts and missing coverage categories.
"""
import json, sys
def evaluate(pkt):
    reasons=[]
    if pkt.get('blocking_findings',0)>0: reasons.append('blocking_findings_present')
    if pkt.get('source_files_scanned',0)<1: reasons.append('no_source_files_scanned')
    fx=pkt.get('fixtures',{})
    if fx.get('valid',0)<1: reasons.append('missing_valid_fixture')
    if fx.get('invalid',0)<1: reasons.append('missing_invalid_fixture')
    if pkt.get('evals',0)<1: reasons.append('missing_eval')
    return {'verdict':'DENY' if reasons else 'ALLOW','reasons':reasons}
if __name__=='__main__': print(json.dumps(evaluate(json.load(open(sys.argv[1]))),indent=2))
