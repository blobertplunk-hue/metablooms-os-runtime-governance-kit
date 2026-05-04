#!/usr/bin/env python3
from __future__ import annotations

# MetaBlooms Stage4 bounded subprocess enforcement shim.
from pathlib import Path as _MBPath
import sys as _MBSys
_MB_SELF = _MBPath(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_EXEC_LIB = _MB_PARENT / "0_kernel" / "lib" / "execution"
    if (_MB_EXEC_LIB / "bounded_subprocess_compat_v1.py").exists():
        if str(_MB_EXEC_LIB) not in _MBSys.path:
            _MBSys.path.insert(0, str(_MB_EXEC_LIB))
        break
from bounded_subprocess_compat_v1 import run as bounded_subprocess_run
import json, subprocess, hashlib, time, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MB = ROOT / 'bin/mb'
TS = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
OUT_DIR = ROOT / 'runtime/evals/operator_surface'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run(args, timeout=60):
    p = bounded_subprocess_run(args, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
    parsed = None
    try:
        parsed = json.loads(p.stdout)
    except Exception:
        pass
    return {'args': args, 'rc': p.returncode, 'stdout_tail': p.stdout[-2000:], 'stderr_tail': p.stderr[-2000:], 'json': parsed}

required_paths = [
    'bin/mb',
    '0_kernel/registry/operator_surface/MB_CLI_COMMAND_SPEC_v1.json',
    'runtime/fixtures/operator_surface/MB_CLI_FIXTURE_CASES_v1.json',
    'docs/operator_surface/MB_OPERATOR_QUICKSTART_v1.md',
]
checks = {rel: (ROOT/rel).exists() for rel in required_paths}
results = {
    'artifact_type': 'MB_OPERATOR_SURFACE_VALIDATION_v1',
    'created_utc': TS,
    'root': str(ROOT),
    'path_checks': checks,
    'commands': {}
}
for name, cmd in {
    'status_json': ['python3','-S',str(MB), '--json', 'status'],
    'verify_json': ['python3','-S',str(MB), '--json', 'verify'],
    'replay_json': ['python3','-S',str(MB), '--json', 'replay'],
}.items():
    results['commands'][name] = run(cmd)

pass_conditions = [all(checks.values())]
pass_conditions.append(results['commands']['status_json']['rc'] == 0 and results['commands']['status_json']['json'] is not None)
pass_conditions.append(results['commands']['verify_json']['rc'] == 0 and results['commands']['verify_json']['json'] is not None and results['commands']['verify_json']['json'].get('verdict') == 'VERIFY_PASS')
pass_conditions.append(results['commands']['replay_json']['rc'] == 0 and results['commands']['replay_json']['json'] is not None)
results['verdict'] = 'PASS' if all(pass_conditions) else 'FAIL'
results['pass_conditions'] = pass_conditions
p = OUT_DIR / 'MB_OPERATOR_SURFACE_VALIDATION_LATEST.json'
_mb_write_json_file(p, results, operation_id='STAGE4_ATOMIC_JSON_0_kernel_validators_validate_operator_surface_v1_py_L61', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
sha = hashlib.sha256(p.read_bytes()).hexdigest()
(p.with_suffix('.json.sha256')).write_text(f'{sha}  {p.name}\n', encoding='utf-8')
print(json.dumps({'verdict': results['verdict'], 'validation_path': str(p), 'sha256': sha}, indent=2))
raise SystemExit(0 if results['verdict'] == 'PASS' else 2)
