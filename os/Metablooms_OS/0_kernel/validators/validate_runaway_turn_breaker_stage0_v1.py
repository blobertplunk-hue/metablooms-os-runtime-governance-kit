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
import json,subprocess,sys,py_compile
from pathlib import Path
def find_root():
 here=Path(__file__).resolve()
 for p in [here.parent,*here.parents]:
  if (p/'boot_manifest_v1.json').exists() and (p/'0_kernel').exists(): return p
 return Path.cwd()
def run(cmd,root):
 p=bounded_subprocess_run(cmd,cwd=str(root),text=True,capture_output=True,timeout=15)
 try: out=json.loads(p.stdout)
 except Exception: out={'stdout_tail':p.stdout[-500:],'stderr_tail':p.stderr[-500:]}
 return p.returncode,out
def main():
 root=find_root(); issues=[]
 req=['0_kernel/registry/runtime_governance/RUNAWAY_TURN_BREAKER_POLICY_v1.json','0_kernel/scripts/runaway_turn_breaker_v1.py','runtime/receipts/runtime_governance/RUNAWAY_TURN_BREAKER_STAGE0_INSTALL_RECEIPT_LATEST.json','runtime/handoffs/runtime_governance/RUNAWAY_TURN_BREAKER_STAGE0_HANDOFF_LATEST.json']
 for r in req:
  if not (root/r).exists(): issues.append({'missing':r})
 for py in ['0_kernel/scripts/runaway_turn_breaker_v1.py','0_kernel/validators/validate_runaway_turn_breaker_stage0_v1.py','bin/mb','0_kernel/scripts/stage_runner_v1.py']:
  try: py_compile.compile(str(root/py),doraise=True)
  except Exception as e: issues.append({'compile_failure':py,'error':repr(e)})
 s=root/'0_kernel/scripts/runaway_turn_breaker_v1.py'; passrc,passout=run([sys.executable,'-S',str(s),'--stage-name','VALIDATOR_PASS','--timeout','30','--command-count','2','--files-touched','5','--has-receipt-plan','--has-handoff-plan','--json'],root); blockrc,blockout=run([sys.executable,'-S',str(s),'--stage-name','VALIDATOR_BLOCK','--timeout','999','--command-count','50','--files-touched','500','--broad-extract','--has-receipt-plan','--has-handoff-plan','--json'],root)
 if passrc!=0 or passout.get('verdict')!='RUNAWAY_BUDGET_PASS': issues.append({'pass_smoke_failed':passout,'rc':passrc})
 if blockrc==0 or blockout.get('verdict')!='RUNAWAY_BUDGET_BLOCK': issues.append({'block_smoke_failed':blockout,'rc':blockrc})
 print(json.dumps({'artifact_type':'RUNAWAY_TURN_BREAKER_STAGE0_VALIDATION_v1','verdict':'PASS' if not issues else 'FAIL','issues':issues,'smoke':{'pass_rc':passrc,'pass_verdict':passout.get('verdict'),'block_rc':blockrc,'block_verdict':blockout.get('verdict')}},indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
