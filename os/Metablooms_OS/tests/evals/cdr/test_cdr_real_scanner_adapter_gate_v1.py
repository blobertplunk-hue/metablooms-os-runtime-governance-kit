#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
GATE=ROOT/'runtime/governance/cdr_real_scanner_adapter_gate_v1.py'
VALID=ROOT/'tests/fixtures/cdr/valid_cdr_real_scanner_adapter_packet_v1.json'
INVALID=ROOT/'tests/fixtures/cdr/invalid_cdr_real_scanner_adapter_missing_fallback_v1.json'

def run(p):
    r=bounded_subprocess.run([sys.executable,'-S',str(GATE),str(p)],cwd=str(ROOT),text=True,capture_output=True)
    try: out=json.loads(r.stdout)
    except Exception as e: raise AssertionError((r.returncode,r.stdout,r.stderr,e))
    return r.returncode,out
rv,ov=run(VALID)
assert rv==0 and ov['verdict']=='ALLOW', ov
ri,oi=run(INVALID)
assert ri!=0 and oi['verdict']=='DENY', oi
assert 'FALLBACK_MISSING' in oi['reasons'], oi
print('PASS CDR real scanner adapter gate')
