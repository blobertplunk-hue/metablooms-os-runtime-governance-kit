#!/usr/bin/env python3
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
GATE=ROOT/'runtime/governance/mpp_stage_contract_code_bearing_declaration_gate_v1.py'
FIX=ROOT/'tests/fixtures/mpp_v3'

def run(name):
    r=bounded_subprocess.run([sys.executable, str(GATE), str(FIX/name)], text=True, capture_output=True)
    try: out=json.loads(r.stdout)
    except Exception: out={'verdict':'BAD_JSON','stdout':r.stdout,'stderr':r.stderr}
    return r.returncode,out

def main():
    cases={
      'valid_mpp_stage_contract_code_bearing_declared_v1.json':'ALLOW',
      'invalid_mpp_stage_contract_missing_code_flag_v1.json':'DENY',
      'invalid_mpp_stage_contract_code_class_flag_false_v1.json':'DENY',
      'valid_mpp_stage_contract_non_code_declared_v1.json':'ALLOW'
    }
    results={}
    ok=True
    for name,expected in cases.items():
        rc,out=run(name); results[name]=out
        if out.get('verdict') != expected: ok=False
    print(json.dumps({'verdict':'PASS' if ok else 'FAIL','results':results}, indent=2, sort_keys=True))
    return 0 if ok else 1
if __name__=='__main__': raise SystemExit(main())
