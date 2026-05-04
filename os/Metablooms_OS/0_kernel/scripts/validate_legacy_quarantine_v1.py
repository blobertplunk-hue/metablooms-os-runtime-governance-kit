#!/usr/bin/env python3
from __future__ import annotations
import json, sys, hashlib, datetime, os
from pathlib import Path
ROOT=Path('/mnt/data/Metablooms_OS')

def sha(p: Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''):
            h.update(c)
    return h.hexdigest()

def main():
    if 'site' in sys.modules:
        print(json.dumps({'result':'deny','blocks':['site module loaded; use python3 -S lane']}))
        return 2
    contract=ROOT/'runtime/governance/contracts/legacy_quarantine_redirects_contract_v1.json'
    data=json.loads(contract.read_text())
    blocks=[]; warnings=[]; checked=[]
    if data.get('authoritative_root')!='/mnt/data/Metablooms_OS':
        blocks.append('bad authoritative_root')
    for e in data.get('entries',[]):
        art=e.get('legacy_artifact','<unknown>')
        arch=e.get('archive_path')
        if arch:
            ap=ROOT/arch
            if not ap.exists(): blocks.append(f'{art}: archive missing {arch}')
            elif e.get('archive_sha256') and sha(ap)!=e.get('archive_sha256'):
                blocks.append(f'{art}: archive sha mismatch')
        live=e.get('live_location')
        red=e.get('redirect')
        if live:
            lp=ROOT/live
            if not lp.exists():
                blocks.append(f'{art}: live tombstone/stub missing {live}')
            else:
                text=lp.read_text(errors='replace')[:4096]
                allowed=('tombstone' in text.lower()) or ('retired' in text.lower()) or ('archive_only' in text.lower()) or ('SystemExit(64)' in text)
                if not allowed:
                    blocks.append(f'{art}: live location does not look tombstoned/retired')
        if red:
            rp=ROOT/red
            if not rp.exists(): blocks.append(f'{art}: redirect metadata missing {red}')
            else:
                r=json.loads(rp.read_text())
                if r.get('machine_use_status') not in ('forbidden_as_runtime_authority','archive_only_after_r3','archive_only_after_r3_confirmed_after_r11'):
                    # Some older redirect statuses are accepted if status itself is explicit.
                    status=str(r.get('status','')).lower()
                    if 'archive' not in status and 'retired' not in status and 'quarantine' not in status:
                        blocks.append(f'{art}: redirect status not archive/retired/quarantined')
        for s in e.get('successor_contracts') or e.get('successor_expected') or []:
            sp=ROOT/s
            if not sp.exists(): blocks.append(f'{art}: successor missing {s}')
        checked.append(art)
    result='deny' if blocks else 'allow'
    report={'decision_id':'R11-LEGACY-QUARANTINE-'+datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ'), 'result':result, 'checked_count':len(checked), 'checked':checked, 'blocks':blocks, 'warnings':warnings, 'contract_path':str(contract)}
    print(json.dumps(report,indent=2))
    return 1 if blocks else 0
if __name__=='__main__':
    raise SystemExit(main())
