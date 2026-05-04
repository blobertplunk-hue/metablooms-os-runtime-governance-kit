#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, sys
ROOT_DEFAULT=pathlib.Path('/mnt/data/Metablooms_OS')
BINDINGS='0_kernel/registry/tool_governance/LEGACY_EXECUTOR_RETROFIT_BINDINGS_v1.json'
ALLOW_CLASSES={'CANONICAL_GOVERNANCE_COMPONENT','TEST_OR_FIXTURE_EXECUTOR','REVIEWED_NON_EXECUTOR_OR_READ_ONLY_HELPER'}

def load(root):
    p=root/BINDINGS
    data=json.loads(p.read_text(encoding='utf-8'))
    table={b['path']:b for b in data.get('bindings',[])}
    return data,table

def decision(decision, code, reasons, binding=None):
    return {'schema':'LegacyExecutorRetrofitGateDecision_v1','decision':decision,'reason_code':code,'reasons':reasons,'binding':binding or {},'safe_to_invoke':decision=='ALLOW'}

def validate_inventory(root):
    data,table=load(root)
    total=data.get('total_findings_bound')
    if not total or total != len(table):
        return decision('DENY','BINDING_COUNT_MISMATCH',[f'total_findings_bound={total} actual={len(table)}'])
    unbound=data.get('unbound_candidates_after')
    if unbound != 0:
        return decision('DENY','UNBOUND_CANDIDATES_REMAIN',[f'unbound_candidates_after={unbound}'])
    return decision('ALLOW','ALL_AUDIT_FINDINGS_BOUND',[f'{len(table)} audit findings bound to invocation policy'])

def validate_packet(root, packet):
    data,table=load(root)
    path=packet.get('path') or packet.get('target_path')
    if not path:
        return decision('DENY','TARGET_PATH_REQUIRED',['packet requires path or target_path'])
    binding=table.get(path)
    if not binding:
        # unknown paths are not covered by this legacy retrofit gate; they still need other gates.
        return decision('ALLOW','PATH_NOT_IN_STAGE6Q_AUDIT_SCOPE',['not a Stage6Q-bound executor candidate'])
    controls=set(packet.get('controls_provided') or [])
    cls=binding.get('classification')
    if cls=='CANONICAL_GOVERNANCE_COMPONENT':
        if {'governance_component_call_context','receipt_output'} <= controls:
            return decision('ALLOW','CANONICAL_GOVERNANCE_COMPONENT_WITH_RECEIPT',['canonical governance component controls present'],binding)
        return decision('DENY','CANONICAL_COMPONENT_CONTEXT_MISSING',['canonical component requires governance_component_call_context and receipt_output'],binding)
    if cls=='TEST_OR_FIXTURE_EXECUTOR':
        if {'test_scope','bounded_temp_root','no_authority_export'} <= controls:
            return decision('ALLOW','TEST_FIXTURE_CONFINED',['test fixture controls present'],binding)
        return decision('DENY','TEST_FIXTURE_CONFINEMENT_MISSING',['test fixture must be confined and non-exporting'],binding)
    if cls=='REVIEWED_NON_EXECUTOR_OR_READ_ONLY_HELPER':
        if 'read_only_or_no_side_effects_assertion' in controls:
            return decision('ALLOW','READ_ONLY_HELPER_ASSERTED',['read-only/no-side-effect assertion present'],binding)
        return decision('DENY','READ_ONLY_ASSERTION_MISSING',['read-only helper requires no-side-effect assertion'],binding)
    if cls=='EXEMPT_QUARANTINED_LEGACY_REFERENCE':
        if {'hitl_approval_token','legacy_replay_scope','no_pointer_promotion'} <= controls:
            return decision('ALLOW','LEGACY_REPLAY_APPROVED_AND_CONFINED',['legacy replay approval controls present'],binding)
        return decision('DENY','LEGACY_DIRECT_INVOCATION_DENIED',['legacy/quarantined reference requires explicit replay approval and no pointer promotion'],binding)
    # Active executors/mutation helpers/vendor tool paths require full governed chain.
    required=set(binding.get('required_controls') or [])
    if required <= controls:
        return decision('ALLOW','FULL_GOVERNANCE_CHAIN_PRESENT',['all required retrofit controls present'],binding)
    missing=sorted(required-controls)
    return decision('DENY','GOVERNANCE_CHAIN_MISSING',[f'missing controls: {missing}'],binding)

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default=str(ROOT_DEFAULT))
    ap.add_argument('--packet')
    ap.add_argument('--inventory', action='store_true')
    ap.add_argument('--out')
    ns=ap.parse_args(argv)
    root=pathlib.Path(ns.root)
    if ns.inventory or not ns.packet:
        res=validate_inventory(root)
    else:
        res=validate_packet(root,json.loads(pathlib.Path(ns.packet).read_text(encoding='utf-8')))
    if ns.out:
        out=pathlib.Path(ns.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(res,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(res,indent=2,sort_keys=True))
    return 0 if res.get('decision')=='ALLOW' else 20
if __name__=='__main__':
    raise SystemExit(main())
