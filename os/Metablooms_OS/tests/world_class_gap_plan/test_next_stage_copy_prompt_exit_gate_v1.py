#!/usr/bin/env python3
from __future__ import annotations
import json, tempfile, importlib.util, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / '0_kernel/validators/next_stage_copy_prompt_exit_gate_v1.py'
spec = importlib.util.spec_from_file_location('gate', MOD)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name + '.sha256').write_text(f'{h}  {path.name}\n', encoding='utf-8')

with tempfile.TemporaryDirectory() as td:
    r = Path(td); s = r / 'runtime/state'; s.mkdir(parents=True)
    prompt = (
        'Boot from /mnt/data using BOOTABLE_FULL_AUTHORITY_WC9.zip and its .sha256 sidecar. Verify checksum, extract to /mnt/data/Metablooms_OS, load BOOT_AUTHORITY_MANIFEST_v1.json and the latest boot/runtime handoff, then run exactly one bounded governed stage for the next requested MetaBlooms task.\n\n'
        'Stage constraints:\n'
        '- Previous completed stage: WC_STAGE9\n'
        '- For any multi-step process, automatically show a tracker preview without the user asking.\n'
        '- Run exactly one bounded governed stage, write receipts/handoff, and stop.\n'
        '- At stage exit, generate runtime/state/NEXT_STAGE_COPY_PROMPT.md with a copy-ready prompt for the following stage.\n'
        '- When successful, export a clearly labeled BOOTABLE_FULL_AUTHORITY bundle plus .sha256 sidecar using a short phone-safe filename.\n'
    )
    write(s/'NEXT_STAGE_COPY_PROMPT.md', prompt)
    write(s/'NEXT_STAGE_COPY_PROMPT.json', json.dumps({'created_at_utc':'x','previous_stage':'WC_STAGE9','source_authority_zip':'BOOTABLE_FULL_AUTHORITY_WC9.zip','prompt':prompt}, indent=2))
    assert gate.validate(r)['verdict'] == 'PASS'

with tempfile.TemporaryDirectory() as td:
    r = Path(td); s = r / 'runtime/state'; s.mkdir(parents=True)
    prompt = 'Boot from /mnt/data using the latest clearly labeled BOOTABLE_FULL_AUTHORITY export and its .sha256 sidecar.'
    write(s/'NEXT_STAGE_COPY_PROMPT.md', prompt)
    write(s/'NEXT_STAGE_COPY_PROMPT.json', json.dumps({'created_at_utc':'x','previous_stage':'x','source_authority_zip':'x','prompt':prompt}, indent=2))
    assert gate.validate(r)['verdict'] == 'FAIL'

print('PASS')
