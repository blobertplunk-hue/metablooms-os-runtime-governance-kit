#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, zipfile, os
from pathlib import Path
GUARD_ID='OS_BUNDLE_DELIVERY_MUST_BE_FULL_BOOTABLE_AUTHORITY_v1'
REQUIRED=[
 'Metablooms_OS/portable_full_os_boot_verify.py',
 'Metablooms_OS/0_kernel/scripts/boot_runtime_executor_v1.py',
 'Metablooms_OS/runtime/governance/runtime_starter_smoke_v1.py',
 'Metablooms_OS/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
 'Metablooms_OS/0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
 'Metablooms_OS/runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json',
 'Metablooms_OS/governance/invariants/OS_BUNDLE_DELIVERY_MUST_BE_FULL_BOOTABLE_AUTHORITY_v1.json',
 'Metablooms_OS/runtime/governance/os_bundle_delivery_guard_v1.py'
]
def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def validate(zip_path, sidecar=None, min_bytes=5_000_000):
    zp=Path(zip_path)
    errors=[]; warnings=[]
    if not zp.exists():
        return {'guard_id':GUARD_ID,'decision':'DENY','errors':['zip_missing'],'zip':str(zp)}
    if zp.stat().st_size < min_bytes:
        errors.append('zip_below_min_full_os_size')
    if sidecar:
        sp=Path(sidecar)
        if not sp.exists(): errors.append('sidecar_missing')
        else:
            expected=sp.read_text(encoding='utf-8', errors='replace').split()[0].strip()
            actual=file_sha(zp)
            if expected!=actual: errors.append('sidecar_sha_mismatch')
    if not zipfile.is_zipfile(zp):
        errors.append('not_zip')
        return {'guard_id':GUARD_ID,'decision':'DENY','errors':errors,'zip':str(zp)}
    with zipfile.ZipFile(zp) as z:
        names=[i.filename.replace('\\','/') for i in z.infolist()]
        files=[i for i in z.infolist() if not i.is_dir()]
        dirs=[i for i in z.infolist() if i.is_dir()]
        seen=set(); dups=[]
        for n in names:
            if n in seen: dups.append(n)
            seen.add(n)
        unsafe=[n for n in names if n.startswith('/') or '/../' in ('/'+n) or n.startswith('../')]
        roots=sorted({n.split('/')[0] for n in names if n})
        if roots != ['Metablooms_OS']:
            errors.append('not_single_Metablooms_OS_root')
        if dups: errors.append('duplicate_zip_entries')
        if unsafe: errors.append('unsafe_zip_paths')
        missing=[p for p in REQUIRED if p not in names]
        if missing: errors.append('missing_required_os_authority_paths')
        has_receipt=any(n.startswith('Metablooms_OS/runtime/receipts/') and n.endswith('.json') for n in names)
        has_handoff=any(n.startswith('Metablooms_OS/runtime/handoffs/') and n.endswith('.json') for n in names)
        has_tracker=any('TRACKER' in n.upper() for n in names)
        if not has_receipt: errors.append('missing_runtime_receipt')
        if not has_handoff: errors.append('missing_runtime_handoff')
        if not has_tracker: warnings.append('tracker_not_detected_by_name')
        bad_crc=z.testzip()
        if bad_crc: errors.append('zip_crc_failure:'+bad_crc)
    return {'guard_id':GUARD_ID,'decision':'ALLOW' if not errors else 'DENY','errors':errors,'warnings':warnings,'zip':str(zp),'bytes':zp.stat().st_size,'required_count':len(REQUIRED),'roots':roots,'file_count':len(files),'dir_count':len(dirs),'duplicate_count':len(dups),'unsafe_count':len(unsafe),'missing_required':missing if 'missing' in locals() else []}
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('zip')
    ap.add_argument('--sidecar')
    ap.add_argument('--min-bytes',type=int,default=5_000_000)
    args=ap.parse_args()
    r=validate(args.zip,args.sidecar,args.min_bytes)
    print(json.dumps(r,indent=2))
    raise SystemExit(0 if r['decision']=='ALLOW' else 1)
