#!/usr/bin/env python3
import json, sys
from pathlib import Path
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path.cwd()
required=['NEW_CHAT_START_HERE.md','BOOT_AUTHORITY_MANIFEST_v1.json','EXPORT_MANIFEST_v1.json','EXPORT_PROVENANCE_v1.json','CURRENT_FULL_AUTHORITY_POINTER_v1.json','CURRENT_EXPORT_AUTHORITY_v1.json','BOOT_HANDOFF_WC13.md']
forbidden=['PAC7 full authority export lock','BOOTABLE_FULL_AUTHORITY_WC12.zip','BOOTABLE_FULL_AUTHORITY_WC10.zip','STAGE6S_FULL_AUTHORITY_EXPORT_AFTER_STAGE6N_TO_6R','STAGE28_STAGING_ONLY']
errors=[]
for rel in required:
    p=root/rel
    if not p.exists():
        errors.append(f'missing:{rel}')
        continue
    txt=p.read_text(encoding='utf-8', errors='replace')
    if 'WC13' not in txt:
        errors.append(f'no_WC13_identity:{rel}')
    for token in forbidden:
        if token in txt:
            errors.append(f'forbidden_token:{rel}:{token}')
for p in root.iterdir():
    if p.name.startswith('.write_probe_'):
        errors.append(f'root_write_probe_present:{p.name}')
status='PASS' if not errors else 'FAIL'
print(json.dumps({'validator':'validate_current_authority_identity_v1','status':status,'errors':errors,'root':str(root)}, indent=2))
sys.exit(0 if status=='PASS' else 1)
