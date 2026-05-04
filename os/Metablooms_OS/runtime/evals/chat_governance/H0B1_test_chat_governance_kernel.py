#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import importlib.util, json, sys

import importlib.util as _mb_atomic_importlib_util
_ATOMIC_JSON_COMPAT_PATH = Path(__file__).resolve().parents[3] / '0_kernel/lib/io/atomic_json_compat_v1.py'
_ATOMIC_JSON_COMPAT_SPEC = _mb_atomic_importlib_util.spec_from_file_location('atomic_json_compat_v1_stage5', _ATOMIC_JSON_COMPAT_PATH)
_mb_atomic_json = _mb_atomic_importlib_util.module_from_spec(_ATOMIC_JSON_COMPAT_SPEC)
assert _ATOMIC_JSON_COMPAT_SPEC and _ATOMIC_JSON_COMPAT_SPEC.loader
_ATOMIC_JSON_COMPAT_SPEC.loader.exec_module(_mb_atomic_json)

def load_mod(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name, path)
    mod=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def main(root_arg: str) -> int:
    root=Path(root_arg)
    kernel_path=root/'runtime/governance/chat_governance_kernel_v1.py'
    iae_path=root/'runtime/governance/invariant_activation_engine_v1.py'
    required=[
      '0_kernel/chat_governance/CHAT_GOVERNANCE_KERNEL_v1.json',
      '0_kernel/chat_governance/TURN_LIFECYCLE_CONTRACT_v1.json',
      '0_kernel/chat_governance/ROUTER_CONTRACT_v1.json',
      'governance/invariants/CHAT_GOVERNANCE_KERNEL_ALWAYS_ON_v1.json',
      '0_kernel/registry/invariants/CHAT_GOVERNANCE_KERNEL_ALWAYS_ON_v1.json',
      'runtime/governance/chat_governance_kernel_v1.py',
      'runtime/evals/chat_governance/H0B1_FIXTURES_MANIFEST_v1.json'
    ]
    errors=[]
    for rel in required:
        if not (root/rel).exists(): errors.append('missing:'+rel)
    kernel=load_mod(kernel_path,'chat_governance_kernel_v1')
    manifest=json.loads((root/'runtime/evals/chat_governance/H0B1_FIXTURES_MANIFEST_v1.json').read_text())
    fixture_dir=root/'runtime/evals/chat_governance/fixtures'
    results={}
    for name, expected in manifest['expected'].items():
        packet=json.loads((fixture_dir/(name+'.json')).read_text())
        result=kernel.validate_turn(root, packet)
        results[name]=result['decision']
        if result['decision'] != expected:
            errors.append(f'fixture:{name}:expected:{expected}:got:{result["decision"]}:errors:{result.get("errors")}')
    iae=load_mod(iae_path,'invariant_activation_engine_v1_imported')
    boot=iae.boot(root)
    ids=[i.get('id') for i in boot.get('invariants',[])]
    if 'CHAT_GOVERNANCE_KERNEL_ALWAYS_ON_v1' not in ids:
        errors.append('iae_boot_missing_CHAT_GOVERNANCE_KERNEL_ALWAYS_ON_v1')
    valid=json.loads((fixture_dir/'valid_full_promotion.json').read_text())
    gate=iae.evaluate(root, dict(valid, task_class='meta_chat_turn'))
    if gate.get('decision') != 'ALLOW':
        errors.append('iae_evaluate_valid_meta_chat_turn_not_allow:'+json.dumps(gate)[:500])
    deny=json.loads((fixture_dir/'deny_missing_router.json').read_text())
    gate2=iae.evaluate(root, dict(deny, task_class='meta_chat_turn'))
    if gate2.get('decision') != 'DENY':
        errors.append('iae_evaluate_missing_router_not_deny:'+json.dumps(gate2)[:500])
    out={'status':'PASS' if not errors else 'FAIL','fixture_results':results,'invariants_loaded':boot.get('invariants_loaded'), 'errors':errors}
    out_path=root/'runtime/evals/chat_governance/H0B1_BEHAVIOR_TEST_RESULTS.json'
    _mb_atomic_json.write_json_file(out_path, out, operation_id='H0B1_BEHAVIOR_TEST_RESULTS', allowed_roots=[str(root)], indent=2, sort_keys=False)
    print(json.dumps(out, indent=2))
    return 0 if not errors else 1
if __name__=='__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv)>1 else '/mnt/data/Metablooms_OS/Metablooms_OS'))
