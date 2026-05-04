#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from datetime import datetime, timezone

PROTECTED = {
    'broad_repair', 'full_authority_export', 'pointer_promotion',
    'privileged_filesystem_mutation', 'external_install', 'destructive_delete',
    'network_side_effect', 'release_delivery'
}

def utc():
    return datetime.now(timezone.utc)

def parse_dt(s):
    return datetime.fromisoformat(str(s).replace('Z', '+00:00'))

def decision(packet, allow, code, reasons):
    return {
        'schema': 'FormalHITLApprovalTokenGateDecision_v1',
        'gate_id': 'FORMAL_HITL_APPROVAL_TOKEN_GATE_v1',
        'stage_id': packet.get('stage_id') or packet.get('action', {}).get('stage_id'),
        'decision': 'ALLOW' if allow else 'DENY',
        'reason_code': code,
        'reasons': reasons,
        'safe_to_execute': bool(allow),
        'decided_at_utc': utc().isoformat().replace('+00:00', 'Z'),
    }

def validate(packet):
    action = packet.get('action') or {}
    token = packet.get('approval_token')
    action_type = action.get('action_type')
    risk = action.get('risk_tier')
    if action_type not in PROTECTED and risk not in ('high', 'critical'):
        return decision(packet, True, 'UNPROTECTED_LOW_RISK_ACTION', ['Formal HITL token not required for this low-risk action.'])
    if not isinstance(token, dict):
        return decision(packet, False, 'APPROVAL_TOKEN_REQUIRED', ['Protected/high-impact action has no approval_token object.'])
    required = ['schema','token_id','status','approval_scope','approved_action_types','approved_risk_tiers','approved_by','issued_at_utc','expires_at_utc','nonce','authority_binding','constraints','rationale']
    missing = [k for k in required if k not in token]
    if missing:
        return decision(packet, False, 'TOKEN_REQUIRED_FIELD_MISSING', [f'missing: {missing}'])
    if token.get('schema') != 'HITLApprovalToken_v1':
        return decision(packet, False, 'TOKEN_SCHEMA_INVALID', ['schema must be HITLApprovalToken_v1'])
    if token.get('status') != 'APPROVED':
        return decision(packet, False, 'TOKEN_NOT_APPROVED', [f"status={token.get('status')}"])
    try:
        if parse_dt(token['expires_at_utc']) <= utc():
            return decision(packet, False, 'TOKEN_EXPIRED', ['expires_at_utc is not in the future'])
    except Exception as exc:
        return decision(packet, False, 'TOKEN_TIME_INVALID', [str(exc)])
    scope = token.get('approval_scope') or {}
    constraints = token.get('constraints') or {}
    binding = token.get('authority_binding') or {}
    if scope.get('stage_id') != action.get('stage_id'):
        return decision(packet, False, 'TOKEN_STAGE_SCOPE_MISMATCH', [f"token stage {scope.get('stage_id')} != action stage {action.get('stage_id')}"])
    if action_type not in token.get('approved_action_types', []):
        return decision(packet, False, 'TOKEN_ACTION_SCOPE_MISMATCH', [f'{action_type} not approved'])
    if risk not in token.get('approved_risk_tiers', []):
        return decision(packet, False, 'TOKEN_RISK_SCOPE_MISMATCH', [f'{risk} not approved'])
    if packet.get('authority_zip_sha256') and binding.get('authority_zip_sha256') != packet.get('authority_zip_sha256'):
        return decision(packet, False, 'TOKEN_AUTHORITY_BINDING_MISMATCH', ['authority_zip_sha256 mismatch'])
    artifacts = action.get('write_paths') or []
    allowed = scope.get('allowed_artifact_roots') or []
    for p in artifacts:
        if not any(str(p).startswith(root) for root in allowed):
            return decision(packet, False, 'TOKEN_ARTIFACT_ROOT_MISMATCH', [f'write path outside approval roots: {p}'])
    if len(artifacts) > int(constraints.get('max_files', 0)):
        return decision(packet, False, 'TOKEN_FILE_BUDGET_EXCEEDED', ['write path count exceeds token max_files'])
    if constraints.get('requires_post_tool_validation') is not True or constraints.get('requires_receipt') is not True or constraints.get('requires_handoff') is not True:
        return decision(packet, False, 'TOKEN_REQUIRED_DOWNSTREAM_GATES_MISSING', ['constraints must require post validation, receipt, and handoff'])
    return decision(packet, True, 'HITL_APPROVAL_TOKEN_VALID', ['token approved','stage/action/risk scope matched','authority binding matched','artifact roots and budgets matched','downstream gates required'])

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('packet')
    ap.add_argument('--out')
    ns = ap.parse_args(argv)
    packet = json.loads(Path(ns.packet).read_text())
    res = validate(packet)
    if ns.out:
        Path(ns.out).write_text(json.dumps(res, indent=2, sort_keys=True) + '\n')
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res['decision'] == 'ALLOW' else 20

if __name__ == '__main__':
    raise SystemExit(main())
