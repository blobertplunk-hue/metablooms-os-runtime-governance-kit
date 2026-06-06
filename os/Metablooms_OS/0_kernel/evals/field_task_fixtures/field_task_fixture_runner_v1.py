#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time, hashlib
from pathlib import Path
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/Metablooms_OS')
BASE=ROOT/'0_kernel/evals/field_task_fixtures'

def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding='utf-8')
    path.with_name(path.name+'.sha256').write_text(f'{sha256(path)}  {path.name}\n', encoding='utf-8')

def run(root=ROOT):
    cfg=BASE/'FIELD_TASK_FIXTURES_v1.json'
    errors=[]; results=[]
    if not cfg.exists():
        errors.append('missing FIELD_TASK_FIXTURES_v1.json')
        fixtures=[]
    else:
        fixtures=json.loads(cfg.read_text(encoding='utf-8')).get('fixtures',[])
    for fx in fixtures:
        rel=fx.get('artifact')
        p=BASE/rel
        item={'id':fx.get('id'),'domain':fx.get('domain'),'artifact':str(p),'verdict':'PASS','errors':[]}
        if not p.exists():
            item['verdict']='FAIL'; item['errors'].append('missing artifact')
        else:
            text=p.read_text(encoding='utf-8')
            for s in fx.get('must_contain',[]):
                if s not in text:
                    item['verdict']='FAIL'; item['errors'].append('missing required text: '+s)
            if 'json_requires' in fx or 'json_requires_key' in fx:
                try: data=json.loads(text)
                except Exception as e:
                    item['verdict']='FAIL'; item['errors'].append('invalid json: '+str(e)); data={}
                for k,v in fx.get('json_requires',{}).items():
                    if data.get(k)!=v:
                        item['verdict']='FAIL'; item['errors'].append(f'json key {k} expected {v!r} got {data.get(k)!r}')
                if fx.get('json_requires_key') and fx['json_requires_key'] not in data:
                    item['verdict']='FAIL'; item['errors'].append('missing json key: '+fx['json_requires_key'])
        if item['verdict']!='PASS': errors.append(item['id'])
        results.append(item)
    out={'schema_version':'v1','checked_at_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),'verdict':'PASS' if not errors else 'FAIL','passed':sum(1 for r in results if r['verdict']=='PASS'),'total':len(results),'results':results,'errors':errors}
    write_json(root/'runtime/state/FIELD_TASK_FIXTURE_RESULTS_v1.json', out)
    return out
if __name__=='__main__':
    res=run(ROOT); print(json.dumps(res, indent=2)); sys.exit(0 if res['verdict']=='PASS' else 1)
