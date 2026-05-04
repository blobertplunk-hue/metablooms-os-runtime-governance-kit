#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def find_root():
    here=Path(__file__).resolve()
    for parent in [here.parent,*here.parents]:
        if (parent/'boot_manifest_v1.json').exists() and (parent/'0_kernel').exists():
            return parent
    return Path.cwd()

def run(cmd,cwd,expect=(0,),timeout=30):
    p=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=timeout)
    try:
        parsed=json.loads(p.stdout)
    except Exception:
        parsed=None
    return {'cmd':cmd,'ok':p.returncode in expect,'returncode':p.returncode,'stdout_tail':p.stdout[-2000:],'stderr_tail':p.stderr[-1000:],'json':parsed}

def main():
    root=find_root()
    mb=[sys.executable,'-S',str(root/'bin/mb')]
    req=['bin/mb','0_kernel/registry/operator_surface/MB_CLI_COMMAND_SPEC_v3.json','0_kernel/registry/operator_surface/MB_STAGE_RUNNER_CONTRACT_v1.json','0_kernel/registry/operator_surface/MB_TRACKER_PREVIEW_SPEC_v1.json','0_kernel/validators/validate_operator_surface_stage3_v1.py','0_kernel/scripts/stage_runner_v1.py','docs/operator_surface/MB_OPERATOR_QUICKSTART_v3.md','runtime/state/TRACKER_STATE_v1.json']
    checks={rel:(root/rel).exists() for rel in req}
    tests=[
        run(mb+['verify','--json'],root),
        run(mb+['tracker','--json'],root),
        run(mb+['run-stage','STAGE3_FIXTURE','--dry-run','--json','--no-write'],root),
        run(mb+['run-stage','STAGE3_FIXTURE','--execute','--json'],root,expect=(3,))
    ]
    failed=[k for k,v in checks.items() if not v]
    failed_tests=[t for t in tests if not t['ok']]
    verdict='PASS' if not failed and not failed_tests else 'FAIL'
    print(json.dumps({'artifact_type':'MB_OPERATOR_SURFACE_STAGE3_VALIDATION_v1','root':str(root),'verdict':verdict,'required_checks':checks,'failed_required':failed,'tests':tests,'failed_test_count':len(failed_tests)},indent=2,sort_keys=True))
    return 0 if verdict=='PASS' else 2
if __name__=='__main__':
    raise SystemExit(main())
