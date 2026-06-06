#!/usr/bin/env python3
from __future__ import annotations
import json, pathlib, subprocess, sys, importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[3]

def load_mod(rel):
    p=ROOT/rel
    spec=importlib.util.spec_from_file_location(p.stem, p)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def validate(root: pathlib.Path = ROOT) -> dict:
    enforcer=load_mod('runtime/governance/prompt_route_preexecution_enforcer_v1.py')
    hook=load_mod('runtime/governance/task_start_hook_v1.py')
    fdir=root/'runtime/cartridges/prompt_governance_v1/fixtures/preexecution_enforcer'
    required=[root/'0_kernel/registry/PROMPT_ROUTE_PREEXECUTION_ENFORCER_CONTRACT_v1.json', root/'runtime/governance/prompt_route_preexecution_enforcer_v1.py', root/'runtime/governance/task_start_hook_v1.py', root/'runtime/state/PROMPT_TASK_START_LEDGER_v1.jsonl']
    missing=[str(p.relative_to(root)) for p in required if not p.exists()]
    results=[]
    for fp in sorted(fdir.glob('*.json')):
        fixture=json.loads(fp.read_text())
        d=enforcer.enforce_prompt_route(fixture['prompt'], root=root)
        ok=d.get('decision')=='ALLOW' and d.get('improved_prompt') and d.get('contract_hash') and d.get('required_gates')
        if fixture.get('expect_task_type'): ok = ok and d.get('task_type')==fixture['expect_task_type']
        if fixture.get('expect_profile'): ok = ok and d.get('selected_profile')==fixture['expect_profile']
        if fixture.get('expect_required_phrase'): ok = ok and fixture['expect_required_phrase'] in d.get('improved_prompt','')
        ranks=d.get('ranking_explanation',[])
        ok = ok and bool(ranks) and [r.get('rank') for r in ranks] == sorted(r.get('rank') for r in ranks)
        results.append({'fixture':fp.name,'ok':bool(ok),'task_type':d.get('task_type'),'profile':d.get('selected_profile')})
    before=(root/'runtime/state/PROMPT_TASK_START_LEDGER_v1.jsonl').read_text() if (root/'runtime/state/PROMPT_TASK_START_LEDGER_v1.jsonl').exists() else ''
    hook_decision=hook.start_task('execute a governed implementation stage with export validation', root=root)
    after=(root/'runtime/state/PROMPT_TASK_START_LEDGER_v1.jsonl').read_text()
    ledger_ok=len(after)>len(before) and hook_decision.get('decision')=='ALLOW'
    passed=sum(1 for r in results if r['ok'])
    decision='ALLOW' if not missing and passed==len(results) and ledger_ok else 'DENY'
    return {'validator':'validate_prompt_route_preexecution_enforcer_v1','decision':decision,'missing':missing,'fixture_count':len(results),'passed':passed,'failed':len(results)-passed,'ledger_write_ok':ledger_ok,'results':results}
if __name__=='__main__':
    print(json.dumps(validate(), indent=2, sort_keys=True))
