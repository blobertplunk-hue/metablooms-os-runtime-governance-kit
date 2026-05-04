#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import importlib.util, json, time

import importlib.util as _mb_atomic_importlib_util
_ATOMIC_JSON_COMPAT_PATH = Path(__file__).resolve().parents[3] / '0_kernel/lib/io/atomic_json_compat_v1.py'
_ATOMIC_JSON_COMPAT_SPEC = _mb_atomic_importlib_util.spec_from_file_location('atomic_json_compat_v1_stage5', _ATOMIC_JSON_COMPAT_PATH)
_mb_atomic_json = _mb_atomic_importlib_util.module_from_spec(_ATOMIC_JSON_COMPAT_SPEC)
assert _ATOMIC_JSON_COMPAT_SPEC and _ATOMIC_JSON_COMPAT_SPEC.loader
_ATOMIC_JSON_COMPAT_SPEC.loader.exec_module(_mb_atomic_json)

def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod

def main() -> int:
    root = Path(__file__).resolve().parents[3]
    gate = load(root/'runtime/governance/governance_survival_promotion_gate_v1.py','survival_gate')
    fixtures_dir = root/'runtime/evals/governance_survival/fixtures'
    valid = json.loads((fixtures_dir/'valid_full_promotion.json').read_text(encoding='utf-8'))
    cases = {'valid_full_promotion': valid}
    # Convert filesystem fixtures to simulated contexts for fast deterministic testing.
    translations = {
      'deny_missing_chat_kernel': {'simulate_missing_paths':['runtime/governance/chat_governance_kernel_v1.py']},
      'deny_missing_tool_selector': {'simulate_missing_paths':['runtime/governance/tool_selection_evidence_router_v1.py']},
      'deny_missing_sandbox_policy': {'simulate_missing_paths':['0_kernel/sandbox_governance/SANDBOX_TOOL_USE_POLICY_v1.json']},
      'deny_unregistered_governance_file': {'simulate_unregistered_governance_file':'runtime/governance/loose_experimental_gate_v9.py'},
    }
    for name, ctx in translations.items(): cases[name]=ctx
    for name in ['deny_missing_tracker_gate','deny_missing_see_gate_when_required','deny_missing_ce_after_see','deny_missing_receipt_handoff','deny_export_without_fresh_extract_smoke']:
        cases[name]=json.loads((fixtures_dir/(name+'.json')).read_text(encoding='utf-8'))
    results={}; errors=[]
    for name, ctx in cases.items():
        res=gate.validate(root, ctx); results[name]=res['decision']
        expected='ALLOW' if name=='valid_full_promotion' else 'DENY'
        if res['decision'] != expected: errors.append({'fixture':name,'expected':expected,'result':res})
    out={'stage':'H0C2_GOVERNANCE_SURVIVAL_AND_PROMOTION_BLOCKER_AUDIT','tested_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'status':'PASS' if not errors else 'FAIL','fixture_results':results,'errors':errors}
    out_path=root/'runtime/evals/governance_survival/H0C2_BEHAVIOR_TEST_RESULTS.json'
    _mb_atomic_json.write_json_file(out_path, out, operation_id='H0C2_BEHAVIOR_TEST_RESULTS', allowed_roots=[str(root)], indent=2, sort_keys=True)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1
if __name__ == '__main__': raise SystemExit(main())
