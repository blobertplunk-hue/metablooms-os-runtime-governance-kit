#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path

def _load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def run_fresh_chat_rehearsal(root: str|Path):
    root=Path(root); errors=[]; checks=[]
    required=[
      '0_kernel/registry/BOOT_REQUIRED_GATES_v1.json',
      '0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json',
      'runtime/governance/boot_critical_governance_loader_v1.py',
      'runtime/governance/governance_scatter_prevention_v1.py',
      'runtime/governance/controlled_artifact_registry_v1.py',
      'runtime/governance/fresh_chat_boot_rehearsal_v1.py',
      'runtime/cartridges/prompt_governance_v1/CARTRIDGE_MANIFEST.json',
      'runtime/cartridges/prompt_governance_v1/validate_prompt_governance_cartridge_v1.py',
      '0_kernel/registry/PROMPT_GOVERNANCE_CARTRIDGE_INSTALL_2_FRESH_CHAT_REHEARSAL_AND_SCATTER_CLEANUP/FRESH_CHAT_BOOT_PROMPT_LOCK_v1.md'
    ]
    for rel in required:
        ok=(root/rel).is_file(); checks.append({'name':'exists:'+rel,'passed':ok})
        if not ok: errors.append('missing:'+rel)
    if not errors:
        boot=_load_json(root/'0_kernel/registry/BOOT_REQUIRED_GATES_v1.json')
        boot_reqs=set(boot.get('required_files',[]))
        for rel in required[:8]:
            if rel not in boot_reqs and rel != '0_kernel/registry/PROMPT_GOVERNANCE_CARTRIDGE_INSTALL_2_FRESH_CHAT_REHEARSAL_AND_SCATTER_CLEANUP/FRESH_CHAT_BOOT_PROMPT_LOCK_v1.md':
                errors.append('not_boot_required:'+rel)
        manifest=_load_json(root/'runtime/cartridges/prompt_governance_v1/CARTRIDGE_MANIFEST.json')
        if manifest.get('stage2_status')!='installed_and_fresh_chat_rehearsal_bound': errors.append('prompt_manifest_not_stage2_bound')
        idx=_load_json(root/'0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json')
        indexed={e.get('path') for e in idx.get('entries',[]) if e.get('path')}
        self_index_anchor='0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json'
        for rel in required:
            if rel == self_index_anchor:
                continue
            if rel not in indexed: errors.append('fresh_chat_required_file_not_indexed:'+rel)
    return {'decision':'DENY' if errors else 'ALLOW','errors':errors,'checks':checks}

if __name__=='__main__':
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
    result=run_fresh_chat_rehearsal(root)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['decision']=='ALLOW' else 1)
