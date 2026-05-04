#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

def root():
    p=Path(__file__).resolve()
    for q in [p.parent,*p.parents]:
        if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
    return Path.cwd()
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    r=root(); required=[
      r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_STAGE_GRAPH_SPEC_v1.json',
      r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_ROLE_POLICY_v1.json',
      r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_WORKPACKET_SCHEMA_v1.json',
      r/'0_kernel/scripts/agent_harness_planner_v1.py',
      r/'docs/agent_harness/AGENT_HARNESS_STAGE1.md'
    ]
    missing=[str(p) for p in required if not p.exists()]
    issues=[]
    if not missing:
      spec=load(required[0]); roles=load(required[1]); schema=load(required[2])
      nodes=spec.get('stage_graph',{}).get('nodes',[]); edges=spec.get('stage_graph',{}).get('edges',[])
      role_names={x.get('role') for x in roles.get('roles',[])}
      node_roles={x.get('role') for x in nodes}
      if len(nodes)<7: issues.append('node_count_below_7')
      if not node_roles.issubset(role_names): issues.append('node_roles_not_in_role_policy')
      if not edges: issues.append('missing_edges')
      if 'workpacket_id' not in schema.get('required_fields',[]): issues.append('workpacket_schema_missing_workpacket_id')
    planner=r/'0_kernel/scripts/agent_harness_planner_v1.py'
    smoke=None
    if planner.exists():
      cp=subprocess.run(['python3','-S',str(planner),'--stage','AGENT_HARNESS_STAGE1_VALIDATOR_SMOKE','--write-plan','--json'],cwd=str(r),text=True,capture_output=True,timeout=30)
      smoke={'rc':cp.returncode,'stdout_tail':cp.stdout[-1200:],'stderr_tail':cp.stderr[-500:]}
      if cp.returncode!=0: issues.append('planner_smoke_failed')
    verdict='PASS' if not missing and not issues else 'FAIL'
    out={'artifact_type':'AGENT_HARNESS_STAGE1_VALIDATION_v1','verdict':verdict,'missing':missing,'issues':issues,'smoke':smoke}
    (r/'runtime/evals/agent_harness').mkdir(parents=True,exist_ok=True)
    (r/'runtime/evals/agent_harness/AGENT_HARNESS_STAGE1_VALIDATION_LATEST.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2,sort_keys=True))
    return 0 if verdict=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
