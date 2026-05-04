#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
validator = ROOT / 'runtime/governance/formal_hitl_approval_token_gate_v1.py'
valid = ROOT / 'tests/fixtures/governance/hitl_approval_token_valid_v1.json'
invalid = ROOT / 'tests/fixtures/governance/hitl_approval_token_invalid_missing_scope_v1.json'

def run(packet):
    result = bounded_subprocess.run([sys.executable, '-S', str(validator), str(packet)], capture_output=True, text=True, cwd=str(ROOT))
    if not result.stdout.strip():
        raise AssertionError({'returncode': result.returncode, 'stderr': result.stderr})
    return result.returncode, json.loads(result.stdout)

def main():
    rc, out = run(valid)
    assert rc == 0 and out['decision'] == 'ALLOW', out
    rc, out = run(invalid)
    assert rc != 0 and out['decision'] == 'DENY', out
    print(json.dumps({'schema':'FormalHITLApprovalTokenGateSmokeResult_v1','verdict':'PASS','fixtures_checked':2}, indent=2))

if __name__ == '__main__':
    main()
