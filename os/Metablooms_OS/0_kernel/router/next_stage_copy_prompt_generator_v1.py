#!/usr/bin/env python3
from __future__ import annotations
import json, sys, time, hashlib, os
from pathlib import Path

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(text, encoding='utf-8')
    os.replace(tmp, path)
    path.with_name(path.name + '.sha256').write_text(f'{_sha256(path)}  {path.name}\n', encoding='utf-8')

def generate(root: Path, next_stage: str, previous_stage: str, source_authority_zip: str, concrete_task_supplied: bool=False) -> str:
    target = next_stage if concrete_task_supplied else 'for the next requested MetaBlooms task'
    prompt = (
        f'Boot from /mnt/data using {source_authority_zip} and its .sha256 sidecar. Verify checksum, extract to /mnt/data/Metablooms_OS, load BOOT_AUTHORITY_MANIFEST_v1.json and the latest boot/runtime handoff, then run exactly one bounded governed stage {target}.\n\n'
        'Stage constraints:\n'
        f'- Previous completed stage: {previous_stage}\n'
        '- Use the latest measured scorecard, DORA-style metrics baseline, educational HTML design-system cartridge, operator polish authority manifest, lesson promotion queue/fixture factory, general capability resolver framework, automatic multi-step tracker contract, and next-stage copy prompt exit gate as priority authority.\n'
        '- For any multi-step process, automatically show a tracker preview without the user asking.\n'
        '- If no concrete next task is supplied, do not invent domain work; run only a bounded boot/routing smoke and write a clear handoff.\n'
        '- Run exactly one bounded governed stage, write receipts/handoff, and stop.\n'
        '- At stage exit, generate runtime/state/NEXT_STAGE_COPY_PROMPT.md with a copy-ready prompt for the following stage.\n'
        '- Before final response, validate the continuation prompt with 0_kernel/validators/next_stage_copy_prompt_exit_gate_v1.py.\n'
        '- When successful, export a clearly labeled BOOTABLE_FULL_AUTHORITY bundle plus .sha256 sidecar using a short phone-safe filename.\n'
    )
    payload = {
        'schema_version': 'v2',
        'created_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'next_stage': next_stage,
        'previous_stage': previous_stage,
        'source_authority_zip': source_authority_zip,
        'concrete_task_supplied': concrete_task_supplied,
        'prompt': prompt,
    }
    state = root / 'runtime/state'
    _write(state / 'NEXT_STAGE_COPY_PROMPT.md', prompt)
    _write(state / 'NEXT_STAGE_COPY_PROMPT.json', json.dumps(payload, indent=2) + '\n')
    return prompt

if __name__ == '__main__':
    if len(sys.argv) < 5:
        print('usage: next_stage_copy_prompt_generator_v1.py ROOT NEXT_STAGE PREVIOUS_STAGE SOURCE_AUTHORITY_ZIP [--concrete]', file=sys.stderr)
        sys.exit(2)
    print(generate(Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], '--concrete' in sys.argv))
