#!/usr/bin/env python3
from __future__ import annotations
import json, time, importlib.util
from pathlib import Path

def _import(path:Path,name:str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def _fixture_files(root:Path):
    base=root/'runtime/cartridges/prompt_governance_v1/fixtures/patch_replay_quality_ranker'
    if not base.exists(): return []
    return sorted([p for p in base.iterdir() if p.is_file() and p.suffix=='.json' and not p.name.endswith('.sha256')])

def replay_prompt_patches(root, fixtures=None, write_report=True):
    root=Path(root)
    auto=_import(root/'runtime/governance/prompt_auto_improvement_loop_v1.py','prompt_auto_improvement_loop_v1')
    ranker=_import(root/'runtime/governance/prompt_quality_ranker_v1.py','prompt_quality_ranker_v1')
    fixture_paths=[Path(p) for p in fixtures] if fixtures else _fixture_files(root)
    results=[]
    for fp in fixture_paths:
        fx=json.loads(fp.read_text(encoding='utf-8'))
        raw=fx.get('raw_prompt','')
        candidates=[]
        primary=auto.optimize_prompt(raw, root, fx.get('task_hint'))
        primary['candidate_id']=fx.get('fixture_id','fixture')+':auto_primary'
        primary['raw_prompt']=raw
        candidates.append(primary)
        for c in fx.get('additional_candidates',[]):
            c=dict(c); c.setdefault('raw_prompt', raw); candidates.append(c)
        ranking=ranker.rank_candidates(candidates, fx)
        expected=fx.get('expected_decision','ALLOW')
        pass_flag=(ranking.get('decision')==expected and ranking.get('top_candidate') and ranking['top_candidate']['score']>=fx.get('min_top_score',0.80))
        results.append({'fixture_id':fx.get('fixture_id',fp.stem),'path':str(fp.relative_to(root)),'expected_decision':expected,'ranking':ranking,'pass':bool(pass_flag)})
    report={'packet_type':'PROMPT_PATCH_REPLAY_REPORT_v1','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'fixture_count':len(results),'passed':sum(1 for r in results if r['pass']),'failed':sum(1 for r in results if not r['pass']),'results':results}
    report['decision']='ALLOW' if results and report['failed']==0 else 'DENY'
    if write_report:
        out=root/'runtime/state/PROMPT_PATCH_REPLAY_REPORT_v1.json'
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
        ledger=root/'runtime/state/PROMPT_PATCH_LEDGER_v1.jsonl'
        with ledger.open('a',encoding='utf-8') as f:
            f.write(json.dumps({'event_type':'prompt_patch_replay','stage':'PROMPT_GOVERNANCE_CARTRIDGE_INSTALL_9_PROMPT_PATCH_REPLAY_AND_QUALITY_RANKER','decision':report['decision'],'fixture_count':report['fixture_count'],'created_utc':report['created_utc']}, sort_keys=True)+'\n')
    return report

if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
    r=replay_prompt_patches(root)
    print(json.dumps(r, indent=2, sort_keys=True))
    raise SystemExit(0 if r.get('decision')=='ALLOW' else 1)
