#!/usr/bin/env python3
"""Purpose: Enforce CDR risk-tiered test evidence.
Inputs: JSON packet with declared tier, triggers, evidence categories, and improvement candidates.
Outputs: ALLOW/DENY with missing evidence and tier reasons.
Failure modes: Undertiered or missing required evidence denies.
Debuggability: Returns required tier and missing categories.
"""
import json, sys
ORDER=['LOW','MEDIUM','HIGH','CRITICAL']
REQ={'LOW':['static_review','unit','regression'],'MEDIUM':['static_review','unit','negative','integration','regression','failure_mode'],'HIGH':['static_review','unit','negative','integration','regression','failure_mode','security','observability','rollback_recovery'],'CRITICAL':['static_review','unit','negative','integration','regression','failure_mode','security','observability','rollback_recovery','performance_resource','fresh_extract_e2e','hitl_approval','export_integrity','adversarial_abuse']}
ESC={'export_authority':'CRITICAL','destructive_action':'CRITICAL','privileged_filesystem_mutation':'CRITICAL','runtime_critical':'HIGH','security_sensitive':'HIGH','tool_execution':'HIGH','external_io':'HIGH','data_mutation':'HIGH','user_facing':'MEDIUM','public_api_change':'MEDIUM','schema_change':'MEDIUM'}
def max_tier(triggers):
    t='LOW'
    for x in triggers:
        et=ESC.get(x,'LOW')
        if ORDER.index(et)>ORDER.index(t): t=et
    return t
def evaluate(pkt):
    reasons=[]; tier=pkt.get('declared_tier','LOW'); required=max_tier(pkt.get('triggers',[]))
    if ORDER.index(tier)<ORDER.index(required): reasons.append(f'undertiered:{tier}<required:{required}')
    cats=set(pkt.get('evidence_categories',[])); missing=[c for c in REQ[required] if c not in cats]
    reasons += [f'missing_evidence_category:{m}' for m in missing]
    for c in pkt.get('improvement_candidates',[]):
        high=c.get('benefit_score',0)>=3 and c.get('risk_score',9)<=2 and c.get('scope_cost',9)<=2 and c.get('stage_fit') is True
        if high and c.get('decision')=='rejected' and not c.get('handoff'):
            reasons.append('high_value_candidate_rejected_without_handoff')
    return {'verdict':'DENY' if reasons else 'ALLOW','required_tier':required,'reasons':reasons}
if __name__=='__main__': print(json.dumps(evaluate(json.load(open(sys.argv[1]))),indent=2))
