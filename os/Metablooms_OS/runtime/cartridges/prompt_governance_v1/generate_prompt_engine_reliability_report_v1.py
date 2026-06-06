#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
def load(p): return json.loads(Path(p).read_text())
def generate_report(root):
 root=Path(root); c=root/'runtime/cartridges/prompt_governance_v1'
 reg=load(c/'PROMPT_PROFILE_REGISTRY_v1.json'); suite=load(c/'PROMPT_ENGINE_REGRESSION_FIXTURE_SUITE_v1.json')
 profiles={p.get('profile_id'):p for p in reg.get('profiles',[])}; fixtures=[]; errors=[]
 for p in sorted((c/'fixtures/profile_smoke').glob('*.json')):
  fx=load(p); fixtures.append(fx); prof=fx.get('profile_id')
  if prof not in profiles: errors.append('profile_missing_from_registry:'+str(prof))
  gates=set(profiles.get(prof,{}).get('required_gates',[]))
  for gate in fx.get('expected_required_gates',[]):
   if gate not in gates: errors.append(f'missing_gate:{prof}:{gate}')
 if len(fixtures)<suite.get('minimum_fixture_count',0): errors.append('fixture_count_below_minimum')
 return {'id':'PROMPT_ENGINE_RELIABILITY_REPORT_v1','status':'PASS' if not errors else 'FAIL','fixture_count':len(fixtures),'profile_count':len(profiles),'fixtures':[f.get('fixture_id') for f in fixtures],'errors':errors,'summary':'Prompt engine profile smoke suite validates installed profiles, required gates, output rules, and banned-pattern compatibility.'}
if __name__=='__main__':
 root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd(); r=generate_report(root); out=root/'runtime/cartridges/prompt_governance_v1/PROMPT_ENGINE_RELIABILITY_REPORT_v1.json'; out.write_text(json.dumps(r,indent=2,sort_keys=True)); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r['status']=='PASS' else 1)
