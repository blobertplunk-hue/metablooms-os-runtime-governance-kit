#!/usr/bin/env python3
from __future__ import annotations
import json, tempfile, os, sys
from pathlib import Path

import importlib.util as _mb_atomic_importlib_util
_ATOMIC_JSON_COMPAT_PATH = Path(__file__).resolve().parents[3] / '0_kernel/lib/io/atomic_json_compat_v1.py'
_ATOMIC_JSON_COMPAT_SPEC = _mb_atomic_importlib_util.spec_from_file_location('atomic_json_compat_v1_stage5', _ATOMIC_JSON_COMPAT_PATH)
_mb_atomic_json = _mb_atomic_importlib_util.module_from_spec(_ATOMIC_JSON_COMPAT_SPEC)
assert _ATOMIC_JSON_COMPAT_SPEC and _ATOMIC_JSON_COMPAT_SPEC.loader
_ATOMIC_JSON_COMPAT_SPEC.loader.exec_module(_mb_atomic_json)
ROOT=Path('/mnt/data/Metablooms_OS')

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
VALIDATOR=ROOT/'runtime/governance/post_tool_result_validation_v1.py'
def run(env):
    with tempfile.TemporaryDirectory() as td:
        ep=Path(td)/'env.json'; op=Path(td)/'out.json'
        _mb_atomic_json.write_json_file(ep, env, operation_id='post_tool_result_validation_fixture_env', indent=None, sort_keys=False)
        r=bounded_subprocess.run(['python3','-S',str(VALIDATOR),str(ep),'--out',str(op)],capture_output=True,text=True)
        return r.returncode, json.loads(op.read_text()) if op.exists() else {'stdout':r.stdout,'stderr':r.stderr}
def main():
    tmp=ROOT/'runtime/tmp/stage6l_fixture_target.txt'; tmp.parent.mkdir(parents=True, exist_ok=True); tmp.write_text('ok', encoding='utf-8')
    base={'schema_version':'PostToolResultValidationEnvelope_v1','validation_id':'fixture','stage_id':'STAGE6L','tool_id':'bts_wrapped_filesystem_write','action_type':'filesystem_write','intent':'fixture write','expected':{'min_bytes':1},'actual':{'implementation_reality_verdict':'PASS'},'artifacts':{'primary_path':str(tmp)},'created_at_utc':'2026-05-02T03:26:00Z'}
    rc,out=run(base); assert rc==0 and out['decision']=='ALLOW_SUCCESS_COMMIT', out
    bad=dict(base); bad['artifacts']={'primary_path':str(tmp)+'.missing'}
    rc,out=run(bad); assert rc!=0 and out['decision']=='DENY_SUCCESS_COMMIT', out
    bad2=json.loads(json.dumps(base)); bad2['actual']['implementation_reality_verdict']='FAIL'
    rc,out=run(bad2); assert rc!=0 and out['reason_code']=='IMPLEMENTATION_REALITY_FAILED', out
    print(json.dumps({'verdict':'PASS','fixtures':['allow_valid_filesystem','deny_missing_artifact','deny_failed_implementation_reality']}, indent=2))
if __name__=='__main__': main()
