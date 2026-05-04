#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
REQUIRED=['CARTRIDGE_MANIFEST.json','PROMPT_ENGINE_CONTRACT_v1.json','PROMPT_PROFILE_REGISTRY_v1.json','PROMPT_FAILURE_TAXONOMY_v1.json','PROMPT_WEAKNESS_LEDGER_TEMPLATE_v1.json','PROMPT_PATCH_WRITEBACK_PROTOCOL_v1.json','PROMPT_OUTPUT_RULES_v1.json','PROMPT_REUSABLE_ASSET_INDEXING_RULES_v1.json','PROMPT_CARTRIDGE_INSTALLATION_METADATA_v1.json']
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def validate(root: str|Path):
    root=Path(root); base=root/'runtime/cartridges/prompt_governance_v1'; errors=[]; checks=[]
    for name in REQUIRED:
        p=base/name; ok=p.exists() and p.is_file(); checks.append({'name':'exists:'+name,'passed':ok})
        if not ok: errors.append('missing:'+name); continue
        try: load(p)
        except Exception as exc: errors.append('invalid_json:'+name+':'+repr(exc))
    if not errors:
        prof=load(base/'PROMPT_PROFILE_REGISTRY_v1.json')
        if len(prof.get('profiles',[])) < 4: errors.append('profile_registry_missing_default_profiles')
        tax=load(base/'PROMPT_FAILURE_TAXONOMY_v1.json')
        if not all('repair' in x for x in tax.get('failure_classes',[])): errors.append('failure_taxonomy_missing_repair_protocol')
        out=load(base/'PROMPT_OUTPUT_RULES_v1.json')
        if not out.get('same_turn_ranked_option_rules'): errors.append('same_turn_option_ordering_rule_missing')
        asset=load(base/'PROMPT_REUSABLE_ASSET_INDEXING_RULES_v1.json')
        if not asset.get('index_path'): errors.append('asset_indexing_rule_missing')
    return {'decision':'DENY' if errors else 'ALLOW','errors':errors,'checks':checks}
if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
    result=validate(root); print(json.dumps(result,indent=2)); raise SystemExit(0 if result['decision']=='ALLOW' else 1)
