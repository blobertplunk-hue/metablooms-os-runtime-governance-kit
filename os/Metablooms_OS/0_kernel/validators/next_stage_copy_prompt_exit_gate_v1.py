#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib, sys, re
from pathlib import Path

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def _sidecar_ok(path: Path):
    side = path.with_name(path.name + '.sha256')
    if not side.exists(): return False, f'missing sidecar: {side}'
    parts = side.read_text(encoding='utf-8').strip().split()
    if not parts: return False, f'empty sidecar: {side}'
    actual = _sha256(path)
    if parts[0] != actual: return False, f'sidecar mismatch for {path.name}: declared {parts[0]} actual {actual}'
    return True, 'ok'

def validate(root: Path, require_existing_authority: bool=False):
    state = root/'runtime/state'
    md = state/'NEXT_STAGE_COPY_PROMPT.md'
    js = state/'NEXT_STAGE_COPY_PROMPT.json'
    errors=[]; warnings=[]; prompt=''; data={}
    if not md.exists(): errors.append('missing runtime/state/NEXT_STAGE_COPY_PROMPT.md')
    if not js.exists(): errors.append('missing runtime/state/NEXT_STAGE_COPY_PROMPT.json')
    if md.exists():
        prompt = md.read_text(encoding='utf-8')
        if len(prompt.strip()) < 200: errors.append('NEXT_STAGE_COPY_PROMPT.md is too short to be operational')
        ok,msg=_sidecar_ok(md)
        if not ok: errors.append(msg)
    if js.exists():
        try: data=json.loads(js.read_text(encoding='utf-8'))
        except Exception as e: errors.append(f'invalid NEXT_STAGE_COPY_PROMPT.json: {e}')
        ok,msg=_sidecar_ok(js)
        if not ok: errors.append(msg)
    if prompt:
        required = ['Boot from /mnt/data using','Verify checksum','extract to /mnt/data/Metablooms_OS','run exactly one bounded governed stage','For any multi-step process, automatically show a tracker preview without the user asking','At stage exit, generate runtime/state/NEXT_STAGE_COPY_PROMPT.md','export a clearly labeled BOOTABLE_FULL_AUTHORITY bundle plus .sha256 sidecar using a short phone-safe filename']
        for phrase in required:
            if phrase not in prompt: errors.append(f'missing required prompt phrase: {phrase}')
        for phrase in ['latest clearly labeled BOOTABLE_FULL_AUTHORITY export','latest clearly labeled export']:
            if phrase in prompt: errors.append(f'generic/stale authority phrase is forbidden: {phrase}')
        m = re.search(r'using\s+([^\s]+\.zip)\s+and its \.sha256 sidecar', prompt)
        if not m: errors.append('prompt must reference an explicit source authority ZIP filename')
        elif require_existing_authority and not (Path('/mnt/data')/m.group(1)).exists():
            errors.append('prompt source authority does not exist in /mnt/data: ' + str(Path('/mnt/data')/m.group(1)))
        if 'next requested MetaBlooms task' in prompt:
            warnings.append('prompt is generic because no concrete next task was supplied; acceptable only for routing-smoke handoffs')
    if data and prompt:
        if data.get('prompt') != prompt: errors.append('NEXT_STAGE_COPY_PROMPT.json prompt field does not exactly match markdown prompt')
        for key in ['previous_stage','source_authority_zip','created_at_utc','prompt']:
            if key not in data: errors.append(f'NEXT_STAGE_COPY_PROMPT.json missing required key: {key}')
    return {'verdict':'PASS' if not errors else 'FAIL','errors':errors,'warnings':warnings}

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/Metablooms_OS')
    res = validate(root, '--require-existing-authority' in sys.argv)
    print(json.dumps(res, indent=2))
    sys.exit(0 if res['verdict']=='PASS' else 1)
