#!/usr/bin/env python3
"""MetaBlooms runtime starter smoke gate v1.
Validates a targeted set of boot-critical runtime artifacts without requiring full archive materialization.
"""
import argparse, json, hashlib, sys, zipfile, pathlib, os

REQUIRED = [
  'CURRENT_FULL_AUTHORITY_POINTER_v1.json',
  '0_kernel/registry/BOOT_REQUIRED_GATES_v1.json',
  '0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json',
  '0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md',
  'runtime/governance/boot_critical_governance_loader_v1.py',
  'runtime/governance/governance_scatter_prevention_v1.py',
  'runtime/governance/task_start_hook_v1.py',
  'runtime/governance/prompt_route_preexecution_enforcer_v1.py',
  'runtime/governance/runtime_starter_smoke_v1.py',
  'runtime/cartridges/prompt_governance_v1/CARTRIDGE_MANIFEST.json'
]
JSON_REQUIRED = [
  'CURRENT_FULL_AUTHORITY_POINTER_v1.json',
  '0_kernel/registry/BOOT_REQUIRED_GATES_v1.json',
  '0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json',
  'runtime/cartridges/prompt_governance_v1/CARTRIDGE_MANIFEST.json'
]

def _strip_prefix(names):
    if any(n.startswith('Metablooms_OS/') for n in names):
        return 'Metablooms_OS/'
    return ''

def validate_zip(path):
    result={'mode':'zip','path':str(path),'decision':'DENY','missing':[],'invalid_json':[],'read_errors':[]}
    with zipfile.ZipFile(path) as z:
        names=set(z.namelist())
        prefix=_strip_prefix(names)
        for rel in REQUIRED:
            name=prefix+rel
            if name not in names:
                result['missing'].append(rel)
                continue
            try:
                data=z.read(name)
                if rel in JSON_REQUIRED:
                    json.loads(data.decode('utf-8'))
            except Exception as e:
                result['read_errors'].append({'path':rel,'error':repr(e)})
        if not result['missing'] and not result['invalid_json'] and not result['read_errors']:
            result['decision']='ALLOW'
    return result

def validate_root(root):
    root=pathlib.Path(root)
    result={'mode':'root','path':str(root),'decision':'DENY','missing':[],'invalid_json':[],'read_errors':[]}
    for rel in REQUIRED:
        p=root/rel
        if not p.exists():
            result['missing'].append(rel); continue
        try:
            data=p.read_bytes()
            if rel in JSON_REQUIRED:
                json.loads(data.decode('utf-8'))
        except Exception as e:
            result['read_errors'].append({'path':rel,'error':repr(e)})
    if not result['missing'] and not result['invalid_json'] and not result['read_errors']:
        result['decision']='ALLOW'
    return result

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--zip')
    ap.add_argument('--root')
    ap.add_argument('--json', action='store_true')
    args=ap.parse_args(argv)
    if args.zip:
        res=validate_zip(args.zip)
    elif args.root:
        res=validate_root(args.root)
    else:
        res={'decision':'DENY','error':'--zip or --root required'}
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res.get('decision')=='ALLOW' else 2
if __name__=='__main__':
    raise SystemExit(main())
