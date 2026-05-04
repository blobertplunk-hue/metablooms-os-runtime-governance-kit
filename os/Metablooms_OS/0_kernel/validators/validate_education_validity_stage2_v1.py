#!/usr/bin/env python3
from __future__ import annotations

# MetaBlooms Stage4 bounded subprocess enforcement shim.
from pathlib import Path as _MBPath
import sys as _MBSys
_MB_SELF = _MBPath(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_EXEC_LIB = _MB_PARENT / "0_kernel" / "lib" / "execution"
    if (_MB_EXEC_LIB / "bounded_subprocess_compat_v1.py").exists():
        if str(_MB_EXEC_LIB) not in _MBSys.path:
            _MBSys.path.insert(0, str(_MB_EXEC_LIB))
        break
from bounded_subprocess_compat_v1 import run as bounded_subprocess_run
import json, subprocess, sys
from pathlib import Path
def find_root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def main():
 root=find_root(); required=['0_kernel/scripts/education_validity_gate_v2.py','0_kernel/security/education_promotion_gate_v1.py','0_kernel/registry/education_validity/MB_EDUCATION_VALIDITY_GATE_SPEC_v2.json','0_kernel/registry/education_validity/MB_EDUCATION_VALIDITY_PROMOTION_GATE_SPEC_v1.json','runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_FIXTURES_v1.json','runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_PROMOTION_REPORT_LATEST.json','runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_SCORECARD_LATEST.json']; missing=[p for p in required if not (root/p).exists()]; gate=bounded_subprocess_run([sys.executable,'-S',str(root/'0_kernel/scripts/education_validity_gate_v2.py'),'--json'],cwd=str(root),text=True,capture_output=True,timeout=15); promo=bounded_subprocess_run([sys.executable,'-S',str(root/'0_kernel/security/education_promotion_gate_v1.py'),'--json'],cwd=str(root),text=True,capture_output=True,timeout=15); out={'schema_version':'VALIDATE_EDUCATION_VALIDITY_STAGE2_v1','verdict':'PASS' if not missing and gate.returncode==0 and promo.returncode==0 else 'FAIL','missing':missing,'gate_rc':gate.returncode,'promo_rc':promo.returncode}; print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out['verdict']=='PASS' else 20
if __name__=='__main__': raise SystemExit(main())
