#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
try:
 from runtime.governance.safe_walk_v1 import safe_walk
except Exception:
 try: from safe_walk_v1 import safe_walk
 except Exception:
  import os
  def safe_walk(root, **kwargs):
   root=Path(root)
   for dp,dns,fns in os.walk(root):
    dns[:] = [d for d in dns if d not in {'__pycache__','.git','legacy_archives','legacy_quarantine'}]
    for fn in fns: yield Path(dp)/fn
def validate_banned_patterns(root):
 root=Path(root); hits=[]
 for scope_name in ['0_kernel','runtime']:
  scope=root/scope_name
  if not scope.exists(): continue
  for p in safe_walk(scope, files_only=True, max_files=50000):
   if p.suffix!='.py': continue
   rel=p.relative_to(root).as_posix()
   if rel.startswith('0_kernel/vendor/'): continue
   txt=p.read_text(encoding='utf-8',errors='ignore')
   bad='.'+'rglob('; bad2='Path'+bad
   if bad in txt or bad2 in txt: hits.append({'path':rel,'pattern':'dot-rglob-call'})
 return {'decision':'DENY' if hits else 'ALLOW','hit_count':len(hits),'hits':hits[:100],'replacement':'runtime/governance/safe_walk_v1.py::safe_walk'}
if __name__=='__main__':
 r=validate_banned_patterns(sys.argv[1] if len(sys.argv)>1 else Path.cwd()); print(json.dumps(r,indent=2,sort_keys=True)); raise SystemExit(0 if r['decision']=='ALLOW' else 1)
