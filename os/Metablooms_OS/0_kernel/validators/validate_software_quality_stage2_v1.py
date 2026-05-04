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
import json,subprocess,sys
from pathlib import Path
def find_root():
 p=Path(__file__).resolve()
 for parent in [p.parent,*p.parents]:
  if (parent/'boot_manifest_v1.json').exists() and (parent/'0_kernel').exists(): return parent
 return Path.cwd()
def main():
 root=find_root(); required=['0_kernel/security/software_quality_gate_v1.py','0_kernel/registry/software_quality/MB_SOFTWARE_QUALITY_GATE_SPEC_v2.json','runtime/evals/software_quality/SOFTWARE_QUALITY_STAGE2_SCORECARD_LATEST.json','runtime/evals/software_quality/SOFTWARE_QUALITY_REGRESSION_FIXTURES_v2.json']
 missing=[p for p in required if not (root/p).exists()]
 proc=bounded_subprocess_run([sys.executable,'-S',str(root/'0_kernel/security/software_quality_gate_v1.py')],cwd=str(root),text=True,capture_output=True,timeout=10)
 try: gate=json.loads(proc.stdout)
 except Exception: gate={'parse_error':proc.stdout[-500:],'stderr':proc.stderr[-500:]}
 ok=not missing and proc.returncode==0 and gate.get('promotion_decision')=='PROMOTE'
 print(json.dumps({'schema_version':'VALIDATE_SOFTWARE_QUALITY_STAGE2_v1','verdict':'PASS' if ok else 'FAIL','missing':missing,'gate':gate},indent=2,sort_keys=True)); return 0 if ok else 2
if __name__=='__main__': raise SystemExit(main())
