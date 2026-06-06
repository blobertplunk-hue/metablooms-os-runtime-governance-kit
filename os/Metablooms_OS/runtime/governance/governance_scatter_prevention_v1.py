#!/usr/bin/env python3
from __future__ import annotations
import json, importlib.util
from pathlib import Path
def _import(root):
 p=Path(root)/'runtime/governance/controlled_artifact_registry_v1.py'
 if not p.exists(): return None
 spec=importlib.util.spec_from_file_location('controlled_artifact_registry_v1',p); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
def validate_governance_scatter(root, max_unregistered=0):
 m=_import(root)
 if m is None: return {'decision':'DENY','errors':['missing_controlled_artifact_registry_v1']}
 r=m.validate_controlled_artifact_index(root, verify_hashes=False); r['mode']='controlled_artifact_index'; return r
if __name__=='__main__':
 import sys; r=validate_governance_scatter(sys.argv[1] if len(sys.argv)>1 else Path.cwd()); print(json.dumps(r,indent=2)); raise SystemExit(0 if r['decision']=='ALLOW' else 1)
