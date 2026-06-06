#!/usr/bin/env python3
from __future__ import annotations
import json, importlib.util
from pathlib import Path

def _import(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def validate_prompt_patch_replay_quality_ranker(root):
    root=Path(root)
    required=[
      '0_kernel/registry/PROMPT_PATCH_REPLAY_AND_QUALITY_RANKER_CONTRACT_v1.json',
      'runtime/governance/prompt_patch_replay_engine_v1.py',
      'runtime/governance/prompt_quality_ranker_v1.py',
      'runtime/governance/prompt_auto_improvement_loop_v1.py',
      'runtime/state/PROMPT_PATCH_LEDGER_v1.jsonl'
    ]
    errors=[]
    for rel in required:
        if not (root/rel).exists(): errors.append('missing:'+rel)
    if errors:
        return {'validator':'validate_prompt_patch_replay_quality_ranker_v1','decision':'DENY','errors':errors}
    replay=_import(root/'runtime/governance/prompt_patch_replay_engine_v1.py','prompt_patch_replay_engine_v1')
    report=replay.replay_prompt_patches(root, write_report=True)
    if report.get('decision')!='ALLOW': errors.append('replay_report_denied')
    return {'validator':'validate_prompt_patch_replay_quality_ranker_v1','decision':'ALLOW' if not errors else 'DENY','errors':errors,'report':report}

if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
    r=validate_prompt_patch_replay_quality_ranker(root)
    print(json.dumps(r, indent=2, sort_keys=True))
    raise SystemExit(0 if r.get('decision')=='ALLOW' else 1)
