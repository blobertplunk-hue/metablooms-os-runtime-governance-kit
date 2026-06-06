#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys
ROOT=Path(__file__).resolve().parents[2]
engine=ROOT/'0_kernel/capability_resolver/general_capability_resolver_v1.py'
fixture=json.loads((ROOT/'tests/capability_resolver/general_capability_resolver_fixture_v1.json').read_text())
results=[]
for cap in fixture['capabilities']:
    out=ROOT/'runtime/state'/f'capability_probe_{cap}.json'
    cp=subprocess.run(['python3','-S',str(engine),'--capability',cap,'--task-id','wc6_fixture','--out',str(out)], text=True, capture_output=True)
    record={'capability':cap,'exit_code':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'out_exists':out.exists()}
    if out.exists():
        data=json.loads(out.read_text())
        record['decision']=data.get('decision')
        record['selected_method']=data.get('selected_method')
    results.append(record)
fail=[]
for cap in fixture['expected_nonblocked']:
    r=next(x for x in results if x['capability']==cap)
    if r.get('decision')=='DENY_BLOCKED' or not r.get('out_exists'):
        fail.append(r)
report={'results':results,'verdict':'PASS' if not fail else 'FAIL','failures':fail}
path=ROOT/'runtime/state/GENERAL_CAPABILITY_RESOLVER_TEST_REPORT_v1.json'
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if not fail else 1)
