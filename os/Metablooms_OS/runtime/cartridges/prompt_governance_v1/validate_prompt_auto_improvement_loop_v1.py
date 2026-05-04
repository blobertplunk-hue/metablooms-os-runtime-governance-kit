#!/usr/bin/env python3
from __future__ import annotations
import json, importlib.util
from pathlib import Path
def _mod(path):
    spec=importlib.util.spec_from_file_location('prompt_auto_improvement_loop_v1', path); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def validate_auto_patch_loop(root):
    root=Path(root); path=root/'runtime/governance/prompt_auto_improvement_loop_v1.py'
    if not path.exists(): return {'decision':'DENY','errors':['missing_prompt_auto_improvement_loop']}
    m=_mod(path); errors=[]; results=[]
    for fx in sorted((root/'runtime/cartridges/prompt_governance_v1/fixtures/auto_patch').glob('auto_patch_*.json')):
        data=json.loads(fx.read_text()); r=m.run_patch_loop(root, data.get('raw_prompt',''), write_packet=False)
        results.append({'fixture':fx.name,'decision':r.get('decision'),'profile':r.get('selected_profile'),'checks':r.get('validation_checks')})
        if r.get('decision')!=data.get('expected_decision','ALLOW'): errors.append('fixture_decision_mismatch:'+fx.name)
        if not r.get('optimized_prompt') or 'Execution contract:' not in r.get('optimized_prompt',''): errors.append('missing_execution_contract:'+fx.name)
    return {'decision':'DENY' if errors else 'ALLOW','errors':errors,'fixture_count':len(results),'results':results}
if __name__=='__main__':
    import sys
    root=sys.argv[1] if len(sys.argv)>1 else Path.cwd(); r=validate_auto_patch_loop(root); print(json.dumps(r, indent=2)); raise SystemExit(0 if r['decision']=='ALLOW' else 1)
