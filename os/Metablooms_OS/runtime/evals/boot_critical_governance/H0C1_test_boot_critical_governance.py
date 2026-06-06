#!/usr/bin/env python3
from __future__ import annotations
import importlib.util, json, shutil, tempfile
from pathlib import Path

def _load(path: Path, name: str):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(mod); return mod

def main(root: str) -> dict:
    r=Path(root).resolve()
    loader=_load(r/'runtime/governance/boot_critical_governance_loader_v1.py','loader_under_test')
    scatter=_load(r/'runtime/governance/governance_scatter_prevention_v1.py','scatter_under_test')
    valid=loader.validate_boot_critical_governance(r)
    scatter_valid=scatter.validate_no_scattered_governance(r)
    results={'valid_loader':valid.get('decision'),'valid_scatter':scatter_valid.get('decision')}
    # Negative fixture 1: missing chat kernel must deny.
    with tempfile.TemporaryDirectory() as td:
        t=Path(td)/'Metablooms_OS'
        for rel in ['0_kernel/registry/BOOT_REQUIRED_GATES_v1.json','0_kernel/registry/GOVERNANCE_SCATTER_PREVENTION_POLICY_v1.json','runtime/governance/boot_critical_governance_loader_v1.py','runtime/governance/governance_scatter_prevention_v1.py']:
            (t/rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(r/rel, t/rel)
        deny=loader.validate_boot_critical_governance(t, run_scatter=False)
        results['deny_missing_chat_kernel']='DENY' if deny.get('decision')=='DENY' and any('chat_governance_kernel' in e for e in deny.get('errors',[])) else 'UNEXPECTED'
    # Negative fixture 2: unregistered file in controlled governance dir must deny.
    with tempfile.TemporaryDirectory() as td:
        t=Path(td)/'Metablooms_OS'
        for rel in ['0_kernel/registry/BOOT_REQUIRED_GATES_v1.json','0_kernel/registry/GOVERNANCE_SCATTER_PREVENTION_POLICY_v1.json','runtime/governance/governance_scatter_prevention_v1.py']:
            (t/rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(r/rel, t/rel)
        extra=t/'runtime/governance/UNREGISTERED_LOOSE_GATE_v1.py'
        extra.write_text('# loose gate\n', encoding='utf-8')
        sdeny=scatter.validate_no_scattered_governance(t)
        results['deny_unregistered_scatter']='DENY' if sdeny.get('decision')=='DENY' and sdeny.get('unregistered_count',0)>0 else 'UNEXPECTED'
    status='PASS' if results=={'valid_loader':'ALLOW','valid_scatter':'ALLOW','deny_missing_chat_kernel':'DENY','deny_unregistered_scatter':'DENY'} else 'FAIL'
    return {'status':status,'results':results,'root':str(r)}
if __name__=='__main__':
    import argparse, sys
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ns=ap.parse_args()
    out=main(ns.root); print(json.dumps(out, indent=2)); sys.exit(0 if out['status']=='PASS' else 1)
