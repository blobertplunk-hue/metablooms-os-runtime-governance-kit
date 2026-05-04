#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
def validate(root):
 root=Path(root); c=root/'runtime/cartridges/prompt_governance_v1'; errors=[]
 suite=json.loads((c/'PROMPT_ENGINE_REGRESSION_FIXTURE_SUITE_v1.json').read_text()); reg=json.loads((c/'PROMPT_PROFILE_REGISTRY_v1.json').read_text())
 profiles={p.get('profile_id'):p for p in reg.get('profiles',[])}; fixtures=[]
 for fp in sorted((c/'fixtures/profile_smoke').glob('*.json')):
  fx=json.loads(fp.read_text()); fixtures.append(fx)
  for field in suite['required_fixture_fields']:
   if field not in fx: errors.append(f'missing_field:{fp.name}:{field}')
  prof=fx.get('profile_id')
  if prof not in profiles: errors.append(f'profile_missing:{prof}')
  gates=set(profiles.get(prof,{}).get('required_gates',[]))
  for gate in fx.get('expected_required_gates',[]):
   if gate not in gates: errors.append(f'gate_missing:{prof}:{gate}')
 if len(fixtures)<suite.get('minimum_fixture_count',0): errors.append('fixture_count_below_minimum')
 rp=c/'PROMPT_ENGINE_RELIABILITY_REPORT_v1.json'
 if not rp.exists(): errors.append('missing_reliability_report')
 elif json.loads(rp.read_text()).get('status')!='PASS': errors.append('reliability_report_not_pass')
 return {'decision':'DENY' if errors else 'ALLOW','errors':errors,'fixture_count':len(fixtures),'profile_count':len(profiles)}
if __name__=='__main__':
 r=validate(sys.argv[1] if len(sys.argv)>1 else Path.cwd()); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r['decision']=='ALLOW' else 1)
