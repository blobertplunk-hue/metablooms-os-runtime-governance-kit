#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
GATE = ROOT/'runtime/governance/mpp_cdr_binding_gate_v1.py'
CASES = [
 ('tests/fixtures/mpp_v3/valid_mpp_code_work_with_cdr_pass_v1.json','ALLOW'),
 ('tests/fixtures/mpp_v3/invalid_mpp_code_work_missing_cdr_v1.json','DENY'),
 ('tests/fixtures/mpp_v3/valid_mpp_non_code_no_cdr_required_v1.json','ALLOW'),
]
for rel, expected in CASES:
    p = ROOT/rel
    proc = bounded_subprocess.run([sys.executable, str(GATE), str(p)], text=True, capture_output=True)
    out = json.loads(proc.stdout)
    assert out['verdict'] == expected, (rel, expected, out)
print('MPP_CDR_BINDING_GATE_TEST_PASS')
