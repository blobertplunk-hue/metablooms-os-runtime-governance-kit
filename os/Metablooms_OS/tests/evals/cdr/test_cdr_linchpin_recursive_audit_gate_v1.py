#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
GATE=ROOT/'runtime/governance/cdr_linchpin_recursive_audit_gate_v1.py'
VALID=ROOT/'tests/fixtures/cdr/valid_cdr_linchpin_recursive_audit_packet_v1.json'
INVALID=ROOT/'tests/fixtures/cdr/invalid_cdr_linchpin_recursive_audit_missing_cycles_v1.json'
def run(p):
    cp=bounded_subprocess.run([sys.executable, str(GATE), str(p)], text=True, capture_output=True)
    data=json.loads(cp.stdout)
    return cp.returncode, data
rv,dv=run(VALID)
ri,di=run(INVALID)
assert rv==0 and dv['decision']=='ALLOW', dv
assert ri!=0 and di['decision']=='DENY', di
assert any(r.startswith('missing_cycle:') for r in di['reasons']), di
print(json.dumps({'verdict':'PASS','valid':dv['decision'],'invalid':di['decision']}, indent=2))
