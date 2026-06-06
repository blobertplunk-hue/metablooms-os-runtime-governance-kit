#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def validate_boot_critical_governance(root: str | Path):
    root = Path(root)
    errors=[]; warnings=[]; checks=[]
    manifest_path = root/'0_kernel/registry/BOOT_REQUIRED_GATES_v1.json'
    if not manifest_path.exists():
        return {'decision':'DENY','errors':['missing_boot_required_gates_manifest'],'warnings':warnings,'checks':checks}
    try:
        manifest=_load_json(manifest_path)
        checks.append({'name':'boot_required_gates_parseable','passed':True,'path':str(manifest_path)})
    except Exception as exc:
        return {'decision':'DENY','errors':['boot_required_gates_not_parseable:'+repr(exc)],'warnings':warnings,'checks':checks}
    for rel in manifest.get('required_files',[]):
        p=root/rel
        ok=p.exists() and p.is_file()
        checks.append({'name':'required_file:'+rel,'passed':ok,'path':str(p)})
        if not ok: errors.append('missing_required_file:'+rel)
        elif p.suffix=='.json':
            try: _load_json(p)
            except Exception as exc: errors.append('invalid_json_contract:'+rel+':'+repr(exc))
    scatter_path=root/'runtime/governance/governance_scatter_prevention_v1.py'
    if scatter_path.exists():
        # lightweight import-free contract check; actual scatter enforcement is separate and may be expensive.
        txt=scatter_path.read_text(encoding='utf-8')
        if 'validate_governance_scatter' not in txt:
            errors.append('scatter_validator_missing_validate_function')
    decision='DENY' if errors else 'ALLOW'
    return {'decision':decision,'errors':errors,'warnings':warnings,'checks':checks,'manifest_id':manifest.get('id')}
