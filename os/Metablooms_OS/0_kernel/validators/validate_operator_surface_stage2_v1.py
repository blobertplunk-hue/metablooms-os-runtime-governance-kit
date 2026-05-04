#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, tempfile, zipfile, shutil
from pathlib import Path

REQUIRED = [
  'Metablooms_OS/bin/mb',
  'Metablooms_OS/0_kernel/registry/operator_surface/MB_CLI_COMMAND_SPEC_v2.json',
  'Metablooms_OS/0_kernel/validators/validate_operator_surface_stage2_v1.py',
  'Metablooms_OS/docs/operator_surface/MB_OPERATOR_QUICKSTART_v2.md',
  'Metablooms_OS/runtime/receipts/external_review/UX_OPERATOR_SURFACE_STAGE_2_RECEIPT_LATEST.json',
  'Metablooms_OS/runtime/handoffs/external_review/UX_OPERATOR_SURFACE_STAGE_2_HANDOFF_LATEST.json',
]

def validate_zip(zip_path: str) -> dict:
    zpath = Path(zip_path)
    out = {'artifact_type': 'OPERATOR_SURFACE_STAGE2_VALIDATION_v1', 'zip_path': str(zpath), 'checks': {}, 'verdict': 'FAIL'}
    with zipfile.ZipFile(zpath) as z:
        names = set(z.namelist())
        out['checks']['zipfile_testzip_bad_member'] = z.testzip()
        out['checks']['contains_required'] = {p: p in names for p in REQUIRED}
        mb = z.read('Metablooms_OS/bin/mb').decode('utf-8')
        out['checks']['mb_contains_run_stage'] = 'command_run_stage' in mb and "run-stage" in mb
        out['checks']['mb_contains_doctor'] = 'command_doctor' in mb and "doctor" in mb
    ok = out['checks']['zipfile_testzip_bad_member'] is None and all(out['checks']['contains_required'].values()) and out['checks']['mb_contains_run_stage'] and out['checks']['mb_contains_doctor']
    out['verdict'] = 'PASS' if ok else 'FAIL'
    return out

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: validate_operator_surface_stage2_v1.py <zip>', file=sys.stderr)
        raise SystemExit(2)
    print(json.dumps(validate_zip(sys.argv[1]), indent=2, sort_keys=True))
