#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
try:
 from runtime.governance.safe_walk_v1 import safe_walk
except Exception:
 try: from safe_walk_v1 import safe_walk
 except Exception:
  def safe_walk(root, **kwargs):
   root=Path(root); ignore=set(kwargs.get('ignore_names') or {'__pycache__','legacy_archives','legacy_quarantine','.git'})
   for dp,dns,fns in os.walk(root):
    dns[:] = [d for d in dns if d not in ignore]
    for fn in fns: yield Path(dp)/fn
CONTROLLED_PREFIXES=(
 '0_kernel/boot_contracts/', '0_kernel/cartridges/', '0_kernel/chat_governance/',
 '0_kernel/docs/', '0_kernel/lib/', '0_kernel/mpp_v3/', '0_kernel/pipeline/',
 '0_kernel/registry/', '0_kernel/schemas/', 'runtime/governance/', 'runtime/cartridges/',
)
ROOT_CONTROLLED={'NEW_CHAT_START_HERE.md','CURRENT_FULL_AUTHORITY_POINTER_v1.json','CURRENT_EXPORT_AUTHORITY_v1.json'}
IGNORE_NAMES={'__pycache__','legacy_archives','legacy_quarantine','.git'}
SELF_HASH_ANCHORS={'0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json','0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json.sha256'}
def sha256_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
 return h.hexdigest()
def is_controlled_path(rel):
 return rel in ROOT_CONTROLLED or rel.startswith(CONTROLLED_PREFIXES)
def classify_lifecycle(rel):
 low=rel.lower()
 if rel in SELF_HASH_ANCHORS: return 'self_hash_anchor'
 if rel.endswith('.pyc') or '/__pycache__/' in rel: return 'generated_non_authoritative'
 if '/legacy_archives/' in rel or '/legacy_quarantine/' in rel: return 'historical'
 if 'pre_patch_backups' in low or 'backup' in low or '_bak_' in rel or rel.endswith('.bak'): return 'backup'
 if rel.startswith('runtime/receipts/') or rel.startswith('runtime/handoffs/') or rel.startswith('runtime/stage_bundles/'): return 'receipt'
 if rel in ROOT_CONTROLLED or rel.startswith('0_kernel/boot_contracts/') or rel.startswith('0_kernel/registry/current_authority/'):
  return 'active_authority'
 if rel.startswith(CONTROLLED_PREFIXES): return 'active_supporting'
 return 'generated_non_authoritative'
def candidates(root):
 root=Path(root); out=[]
 for p in safe_walk(root, ignore_names=IGNORE_NAMES, files_only=True, max_files=100000):
  if not p.is_file(): continue
  rel=p.relative_to(root).as_posix()
  if any(x in IGNORE_NAMES for x in rel.split('/')): continue
  if not is_controlled_path(rel): continue
  state=classify_lifecycle(rel)
  if state in {'active_authority','active_supporting'}: out.append(rel)
 return sorted(set(out))
def load_index(root):
 p=Path(root)/'0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json'
 return json.loads(p.read_text()) if p.exists() else {'entries':[]}
def validate_controlled_artifact_index(root, verify_hashes=False):
 root=Path(root); data=load_index(root); entries=data.get('entries',[])
 reg={e.get('path'):e for e in entries if isinstance(e,dict) and e.get('path')}
 cur=set(candidates(root)); errors=[]
 for rel in sorted(cur-set(reg)): errors.append('unregistered_controlled_artifact:'+rel)
 for rel in sorted(set(reg)-cur): errors.append('registered_noncurrent_controlled_artifact:'+rel)
 if verify_hashes:
  for rel,e in sorted(reg.items()):
   p=root/rel
   if p.exists() and e.get('sha256') and sha256_file(p)!=e.get('sha256'):
    errors.append('registered_hash_mismatch:'+rel)
 return {'decision':'DENY' if errors else 'ALLOW','errors':errors[:200],'error_count':len(errors),'current_controlled_count':len(cur),'registered_count':len(reg),'index_status':data.get('status'),'candidate_model':'promotion_authority_lifecycle_v1'}
if __name__=='__main__':
 import sys; r=validate_controlled_artifact_index(sys.argv[1] if len(sys.argv)>1 else Path.cwd(), verify_hashes='--verify-hashes' in sys.argv); print(json.dumps(r,indent=2)); raise SystemExit(0 if r['decision']=='ALLOW' else 1)
