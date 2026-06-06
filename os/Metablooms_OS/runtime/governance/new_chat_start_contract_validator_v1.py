#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def load_json(p: Path): return json.loads(p.read_text(encoding='utf-8'))

FORBIDDEN_LIVE_FRAGMENTS = [
  'Run runtime/governance/runtime_starter_smoke_v1.py',
  'Run `runtime/governance/runtime_starter_smoke_v1.py`',
  'python runtime/governance/runtime_starter_smoke_v1.py',
  'python3 runtime/governance/runtime_starter_smoke_v1.py',
]

def validate_new_chat_start_contract(root: str|Path):
    root=Path(root); errors=[]; checks=[]
    required=[
      'CURRENT_FULL_AUTHORITY_POINTER_v1.json',
      'runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
      '0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
      '0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md',
      'NEW_CHAT_START_HERE.md',
      'runtime/governance/new_chat_start_contract_validator_v1.py',
      'runtime/governance/boot_critical_governance_loader_v1.py',
      'runtime/governance/governance_scatter_prevention_v1.py',
      'runtime/governance/fresh_chat_boot_rehearsal_v1.py',
      'runtime/cartridges/prompt_governance_v1/validate_prompt_governance_cartridge_v1.py',
      'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py',
      '0_kernel/registry/observability/MB_BOOT_SEQUENCE_WRAPPER_ENFORCEMENT_v1.json',
      '0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json',
      'runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json',
      '0_kernel/validators/validate_observability_trace_span_ledger_stage8_historical_callsite_quarantine_v1.py'
    ]
    for rel in required:
        ok=(root/rel).is_file(); checks.append({'name':'exists:'+rel,'passed':ok})
        if not ok: errors.append('missing:'+rel)
    if not errors:
        a=load_json(root/'CURRENT_FULL_AUTHORITY_POINTER_v1.json')
        b=load_json(root/'runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json')
        c=load_json(root/'0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json')
        if a != b or a != c: errors.append('pointer_copies_not_identical')
        for key in ['authority_zip','authority_zip_sha256_sidecar','canonical_working_root','boot_entry_contract','required_start_sequence','fail_closed_if']:
            if key not in a: errors.append('pointer_missing_key:'+key)
        contract=(root/'0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md').read_text(encoding='utf-8')
        for phrase in ['Verify the authority ZIP SHA-256','/mnt/data/Metablooms_OS','boot_critical_governance_loader_v1.py','governance_scatter_prevention_v1.py','fresh_chat_boot_rehearsal_v1.py','prompt_governance_v1','runtime_starter_smoke_contract_wrapper_v1.py','MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json']:
            if phrase not in contract: errors.append('contract_missing_phrase:'+phrase)
        for rel in ['0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md','NEW_CHAT_START_HERE.md']:
            txt=(root/rel).read_text(encoding='utf-8')
            for frag in FORBIDDEN_LIVE_FRAGMENTS:
                if frag in txt:
                    errors.append('live_doc_uses_direct_runtime_starter_smoke_operator_command:'+rel)
    return {'decision':'DENY' if errors else 'ALLOW','errors':errors,'checks':checks}

if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
    result=validate_new_chat_start_contract(root)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['decision']=='ALLOW' else 1)
