#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import importlib.util,json,sys

import importlib.util as _mb_atomic_importlib_util
_ATOMIC_JSON_COMPAT_PATH = Path(__file__).resolve().parents[3] / '0_kernel/lib/io/atomic_json_compat_v1.py'
_ATOMIC_JSON_COMPAT_SPEC = _mb_atomic_importlib_util.spec_from_file_location('atomic_json_compat_v1_stage5', _ATOMIC_JSON_COMPAT_PATH)
_mb_atomic_json = _mb_atomic_importlib_util.module_from_spec(_ATOMIC_JSON_COMPAT_SPEC)
assert _ATOMIC_JSON_COMPAT_SPEC and _ATOMIC_JSON_COMPAT_SPEC.loader
_ATOMIC_JSON_COMPAT_SPEC.loader.exec_module(_mb_atomic_json)
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def main(root_arg):
 root=Path(root_arg); errors=[]
 required=['0_kernel/sandbox_governance/SANDBOX_TOOL_USE_POLICY_v1.json','runtime/governance/sandbox_tool_governance_v1.py','runtime/governance/chat_governance_kernel_v1.py','runtime/plans/H0B2_CODING_PLAN_v1.json','research/SEE/H0B2_SANDBOX_BOOTSTRAP_LAYOUT_REPAIR_SEE_v1.json','research/CE/H0B2_SANDBOX_BOOTSTRAP_LAYOUT_REPAIR_CE_v1.json']
 for rel in required:
  if not (root/rel).exists(): errors.append('missing:'+rel)
 sandbox=load(root/'runtime/governance/sandbox_tool_governance_v1.py','sandbox_test'); boot=sandbox.load_policy(root)
 if boot.get('decision')!='ALLOW': errors.append('sandbox_load_policy_not_allow')
 manifest=json.loads((root/'runtime/evals/sandbox_governance/H0B2_FIXTURES_MANIFEST_v1.json').read_text()); results={}
 for name,expected in manifest['expected'].items():
  pkt=json.loads((root/'runtime/evals/sandbox_governance/fixtures'/(name+'.json')).read_text()); res=sandbox.validate_sandbox_plan(root,pkt); results[name]=res.get('decision')
  if res.get('decision')!=expected: errors.append(f'fixture:{name}:expected:{expected}:got:{res.get("decision")}:errors:{res.get("errors")}')
 out={'status':'PASS' if not errors else 'FAIL','sandbox_policy_load':boot.get('decision'),'fixture_results':results,'errors':errors}
 p=root/'runtime/evals/sandbox_governance/H0B2_BEHAVIOR_TEST_RESULTS.json'; _mb_atomic_json.write_json_file(p, out, operation_id='H0B2_BEHAVIOR_TEST_RESULTS', allowed_roots=[str(root)], indent=2, sort_keys=False); print(json.dumps(out,indent=2)); return 0 if not errors else 1
if __name__=='__main__': sys.exit(main(sys.argv[1]))
