#!/usr/bin/env python3
import json, os, sys
root=os.environ.get('METABLOOMS_ROOT','/mnt/data/Metablooms_OS')
for rel in ['0_kernel/registry/sandbox_capability_router/SANDBOX_CAPABILITY_ROUTER_CARTRIDGE_LATEST.json','0_kernel/registry/sandbox_capability_router/SANDBOX_ROUTER_ENFORCEMENT_WIRING_LATEST.json']:
    p=os.path.join(root,rel)
    if os.path.exists(p):
        j=json.load(open(p,encoding='utf-8'))
        print(json.dumps({'status':'PASS','router_path':p,'routes':sorted(j.get('routes',{}).keys()),'denylist_count':len(j.get('global_denylist',[]))},indent=2)); sys.exit(0)
print(json.dumps({'status':'FAIL','reason':'router_not_found'},indent=2)); sys.exit(1)
