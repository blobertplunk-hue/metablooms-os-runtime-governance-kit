#!/usr/bin/env python3
import json, pathlib, sys
root=pathlib.Path('/mnt/data/Metablooms_OS')
ROOT=root

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
gate=root/'runtime/governance/legacy_executor_retrofit_gate_v1.py'
allow=root/'tests/fixtures/tool_governance/stage6q_repair_allow_wrapped_executor_v1.json'
deny=root/'tests/fixtures/tool_governance/stage6q_repair_deny_direct_executor_v1.json'
def run(args):
    r=bounded_subprocess.run([sys.executable,'-S',str(gate),'--root',str(root)]+args,text=True,capture_output=True)
    try: data=json.loads(r.stdout)
    except Exception as e: raise SystemExit(f'bad json rc={r.returncode} out={r.stdout} err={r.stderr}')
    return r.returncode,data
rc_inv,d_inv=run(['--inventory'])
rc_a,d_a=run(['--packet',str(allow)])
rc_d,d_d=run(['--packet',str(deny)])
report={'schema':'Stage6QRepairSmokeReport_v1','inventory':d_inv,'allow':d_a,'deny':d_d,'verdict':'PASS' if rc_inv==0 and rc_a==0 and rc_d!=0 and d_d.get('decision')=='DENY' else 'FAIL'}
print(json.dumps(report,indent=2,sort_keys=True))
raise SystemExit(0 if report['verdict']=='PASS' else 30)
