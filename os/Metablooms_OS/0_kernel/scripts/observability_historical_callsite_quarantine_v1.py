#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, time
from pathlib import Path

DIRECT_PATTERNS=[
 'Run runtime/governance/runtime_starter_smoke_v1.py',
 'Run `runtime/governance/runtime_starter_smoke_v1.py`',
 'python runtime/governance/runtime_starter_smoke_v1.py',
 'python3 runtime/governance/runtime_starter_smoke_v1.py',
 'runtime_starter_smoke_v1.py'
]
TEXT_SUFFIXES={'.json','.md','.py','.html','.txt','.csv','.yaml','.yml'}

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha_text(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
 return h.hexdigest()
def starts(rel, prefixes): return any(rel.startswith(x) for x in prefixes)

def classify(rel, policy):
 if rel in policy.get('live_operator_surfaces',[]): return 'live_operator_surface'
 if rel in policy.get('implementation_exempt_files',[]): return 'implementation_dependency'
 if starts(rel, policy.get('historical_evidence_prefixes',[])): return 'historical_evidence'
 if starts(rel, policy.get('non_operator_inventory_prefixes',[])): return 'non_operator_state_or_inventory'
 if rel.endswith('.sha256'): return 'checksum_sidecar'
 return 'unclassified'

def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true'); args=ap.parse_args(argv)
 root=Path(args.root).resolve()
 policy_path=root/'0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json'
 policy=load(policy_path)
 hits=[]; issues=[]
 for p in sorted(root.rglob('*')):
  if not p.is_file(): continue
  if p.suffix not in TEXT_SUFFIXES: continue
  if p.name.endswith('.sha256'): continue
  try: txt=p.read_text(encoding='utf-8', errors='ignore')
  except Exception: continue
  matched=[pat for pat in DIRECT_PATTERNS if pat in txt]
  if not matched: continue
  rel=str(p.relative_to(root))
  cls=classify(rel, policy)
  live_forbidden=[]
  if cls=='live_operator_surface':
   for frag in policy.get('forbidden_live_operator_command_fragments',[]):
    if frag in txt: live_forbidden.append(frag)
  if cls=='unclassified': issues.append('unclassified_direct_reference:'+rel)
  if live_forbidden: issues.append('live_operator_direct_command:'+rel)
  hits.append({'path':rel,'class':cls,'matched_patterns':matched,'live_forbidden_fragments':live_forbidden,'sha256':sha_file(p),'size_bytes':p.stat().st_size})
 counts={}
 for h in hits: counts[h['class']]=counts.get(h['class'],0)+1
 index={
  'artifact_type':'MB_HISTORICAL_CALLSITE_QUARANTINE_INDEX.v1',
  'created_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
  'policy':'0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json',
  'underlying_gate':policy.get('underlying_gate'),
  'required_operator_entrypoint':policy.get('required_operator_entrypoint'),
  'verdict':'PASS' if not issues else 'FAIL',
  'summary':{'hit_count':len(hits),'counts_by_class':counts,'issue_count':len(issues)},
  'issues':issues,
  'hits':hits
 }
 out=root/'runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json'
 out.parent.mkdir(parents=True, exist_ok=True)
 text=json.dumps(index,indent=2,sort_keys=True)+'\n'; out.write_text(text,encoding='utf-8')
 (Path(str(out)+'.sha256')).write_text(sha_text(text)+'  '+out.name+'\n',encoding='utf-8')
 print(json.dumps(index,indent=2,sort_keys=True))
 return 0 if index['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
