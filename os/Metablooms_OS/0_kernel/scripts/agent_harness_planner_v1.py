#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time, hashlib
from pathlib import Path

def now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def h(s): return hashlib.sha256(s.encode()).hexdigest()[:16]
def root():
    p=Path(__file__).resolve()
    for q in [p.parent,*p.parents]:
        if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
    return Path.cwd()
def wj(p,o): p.parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(p, o, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_agent_harness_planner_v1_py_L13', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000); return str(p)
def aj(p,o): p.parent.mkdir(parents=True,exist_ok=True); p.open('a',encoding='utf-8').write(json.dumps(o,sort_keys=True)+'\n'); return str(p)
def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))

def make_workpackets(spec, stage_name):
    packets=[]; thread='stage::'+stage_name; cid=h(stage_name+'|agent_harness')
    for node in spec['stage_graph']['nodes']:
        packets.append({
          'workpacket_id':'WP-'+node['id'].upper()+'-'+h(stage_name+node['id']),
          'stage_name':stage_name,
          'role':node['role'],
          'thread_id':thread,
          'checkpoint_id':cid,
          'input_artifacts':[],
          'output_artifacts':node.get('writes',[]),
          'write_scope':node.get('writes',[]),
          'gates':node.get('required_gates',[]),
          'decision':'READY'
        })
    return packets

def main(argv=None):
    pa=argparse.ArgumentParser(); pa.add_argument('--stage',default='IMPLEMENT_AGENT_HARNESS_STAGE_1'); pa.add_argument('--write-plan',action='store_true'); pa.add_argument('--json',action='store_true'); a=pa.parse_args(argv)
    r=root(); spec_path=r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_STAGE_GRAPH_SPEC_v1.json'; role_path=r/'0_kernel/registry/agent_harness/MB_AGENT_HARNESS_ROLE_POLICY_v1.json'
    if not spec_path.exists() or not role_path.exists():
        out={'verdict':'AGENT_HARNESS_MISSING_SPEC','missing':[str(p) for p in [spec_path,role_path] if not p.exists()]}; print(json.dumps(out,indent=2,sort_keys=True)); return 2
    spec=load_json(spec_path); role=load_json(role_path); packets=make_workpackets(spec,a.stage)
    plan={'artifact_type':'AGENT_HARNESS_STAGE1_PLAN_v1','created_utc':now(),'verdict':'AGENT_HARNESS_READY','stage_name':a.stage,'node_count':len(spec['stage_graph']['nodes']),'edge_count':len(spec['stage_graph']['edges']),'roles':[x['role'] for x in role['roles']],'workpackets':packets,'stage1_limit':spec.get('stage1_limit')}
    plan_path=r/'runtime/agent_harness/AGENT_HARNESS_STAGE1_PLAN_LATEST.json'
    if a.write_plan: wj(plan_path,plan)
    aj(r/'runtime/traces/agent_harness/TRACE_SPAN_LEDGER_AGENT_HARNESS_STAGE1.jsonl',{'schema_version':'MB_TRACE_SPAN_LEDGER_SPEC_v2','trace_id':h(a.stage),'span_id':h(a.stage+'planner'+now()),'parent_span_id':None,'name':'agent_harness.stage1.plan','stage_name':a.stage,'event':'end','status':'OK','timestamp_utc':now(),'attributes':{'node_count':plan['node_count'],'workpacket_count':len(packets),'plan_path':str(plan_path) if a.write_plan else None}})
    if a.json: print(json.dumps(plan,indent=2,sort_keys=True))
    else: print('AGENT_HARNESS_READY nodes=%s workpackets=%s'%(plan['node_count'],len(packets)))
    return 0
if __name__=='__main__': raise SystemExit(main())
