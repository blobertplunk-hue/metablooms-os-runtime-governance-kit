#!/usr/bin/env python3
from __future__ import annotations
import json, os, py_compile, importlib.util
from pathlib import Path
REQ=['0_kernel/scripts/checkpoint_manager_v1.py','0_kernel/registry/state_checkpoint/MB_STATE_CHECKPOINT_RESUME_INTERRUPT_SPEC_v1.json','0_kernel/registry/state_checkpoint/MB_INTERRUPT_DECISION_POLICY_v1.json','docs/state_checkpoint/STATE_CHECKPOINT_RESUME_INTERRUPT_STAGE1.md','runtime/receipts/state_checkpoint/STATE_CHECKPOINT_RESUME_INTERRUPT_STAGE1_RECEIPT_LATEST.json','runtime/handoffs/state_checkpoint/STATE_CHECKPOINT_RESUME_INTERRUPT_STAGE1_HANDOFF_LATEST.json']
def find_root():
    env=os.environ.get('METABLOOMS_ROOT')
    if env: return Path(env)
    here=Path(__file__).resolve()
    for p in [here.parent,*here.parents]:
        if (p/'boot_manifest_v1.json').exists() and (p/'0_kernel').exists(): return p
    return Path.cwd()
def load_module(path):
    spec=importlib.util.spec_from_file_location('checkpoint_manager_v1', path)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
def main():
    root=find_root(); issues=[]; smoke={}
    for r in REQ:
        if not (root/r).exists(): issues.append({'missing':r})
    try: py_compile.compile(str(root/'0_kernel/scripts/checkpoint_manager_v1.py'),doraise=True)
    except Exception as e: issues.append({'compile_failure':'checkpoint_manager_v1.py','error':str(e)})
    if not issues:
        try:
            cm=load_module(root/'0_kernel/scripts/checkpoint_manager_v1.py')
            rec=cm.create_checkpoint(root,'STATE_STAGE1_VALIDATOR_SMOKE',{},interrupt_payload={'question':'approve?'})
            smoke['interrupt_status']=rec.get('status'); smoke['thread_id']=rec.get('thread_id')
            rec2=cm.resume_checkpoint(root,rec['thread_id'],{'decision':'approve'})
            smoke['resume_status']=rec2.get('status')
            if rec.get('status')!='INTERRUPTED' or rec2.get('status')!='RESUMED': issues.append({'smoke':'unexpected_status','smoke_payload':smoke})
        except Exception as e: issues.append({'smoke_exception':str(e)})
    payload={'artifact_type':'STATE_CHECKPOINT_RESUME_INTERRUPT_STAGE1_VALIDATION','verdict':'PASS' if not issues else 'FAIL','issues':issues,'smoke':smoke}
    print(json.dumps(payload,indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
