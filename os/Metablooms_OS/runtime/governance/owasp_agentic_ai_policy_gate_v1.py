#!/usr/bin/env python3
import json, sys, datetime

POLICY_REQUIRED = {
    'filesystem_export': {'Tool Universe Resolver','BTS wrapper','pre_tool_action_gate_v1','post_tool_result_validation_v1','CRC proof','SHA sidecar','fresh boot proof','delivery guard'},
    'pointer_promotion': {'formal HITL approval token','authority pointer coherence proof','rollback path','post_tool_result_validation_v1'},
    'external_install': {'supply_chain_origin','version/hash pinning','sandbox smoke','negative capability registry check'},
    'privileged_mutation': {'formal HITL approval token','least privilege scope','T1 mutation receipt','rollback note'},
    'network_side_effect': {'SEE evidence binding','domain/source allowlist when applicable','HITL token if high impact','egress logging'},
    'broad_repair': {'stage budget approval','runaway breaker','bounded scope','failure learning ledger update'},
}
RISK_IDS = {f'ASI{i:02d}' for i in range(1, 11)}

def now():
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat()+'Z'

def evaluate(packet):
    action_class = packet.get('action_class')
    risk_ids = set(packet.get('risk_ids', []))
    controls = set(packet.get('controls_present', []))
    high_impact = bool(packet.get('high_impact', False))
    missing = []
    errors = []
    if high_impact and not action_class:
        errors.append('high_impact_action_missing_action_class')
    if risk_ids and not risk_ids <= RISK_IDS:
        errors.append('unknown_owasp_agentic_risk_id')
    if high_impact and not risk_ids:
        errors.append('high_impact_action_missing_owasp_agentic_risk_ids')
    required = POLICY_REQUIRED.get(action_class, set()) if action_class else set()
    missing = sorted(required - controls)
    decision = 'ALLOW' if not errors and not missing else 'DENY'
    return {
        'schema':'OWASPAgenticAIPolicyGateDecision_v1',
        'timestamp_utc':now(),
        'action_class':action_class,
        'risk_ids':sorted(risk_ids),
        'high_impact':high_impact,
        'controls_present':sorted(controls),
        'controls_missing':missing,
        'errors':errors,
        'decision':decision,
        'reason':'all_required_controls_present' if decision=='ALLOW' else 'missing_required_owasp_agentic_ai_controls_or_classification'
    }

def main(argv):
    if len(argv) != 2:
        print(json.dumps({'error':'usage: owasp_agentic_ai_policy_gate_v1.py packet.json'}, indent=2))
        return 2
    packet=json.load(open(argv[1], encoding='utf-8'))
    decision=evaluate(packet)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision['decision']=='ALLOW' else 1
if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
