#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, sys, hashlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = ROOT/'0_kernel'/'validators'/'validate_visual_presentation_quality_gate_v1.py'
FIXTURE_DIR = ROOT/'tests'/'fixtures'/'visual_presentation_quality'
SCHEMA = ROOT/'0_kernel'/'registry'/'visual_presentation_quality'/'visual_presentation_quality_declaration_schema_v1.json'
CASES = [
    ('valid_html_activity', FIXTURE_DIR/'valid_visual_presentation_quality_html_activity_v1.json', 'ALLOW'),
    ('invalid_default_browser_styles', FIXTURE_DIR/'invalid_visual_presentation_quality_default_browser_styles_v1.json', 'DENY'),
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def run() -> dict:
    results = []
    for name, path, expected in CASES:
        proc = subprocess.run([sys.executable, str(VALIDATOR), '--validate', str(path), '--schema', str(SCHEMA), '--expect', expected], text=True, capture_output=True)
        try:
            payload = json.loads(proc.stdout)
        except Exception:
            payload = {'parse_error': True, 'stdout': proc.stdout, 'stderr': proc.stderr}
        actual = payload.get('decision')
        passed = proc.returncode == 0 and actual == expected
        results.append({
            'case': name,
            'fixture_path': str(path),
            'fixture_sha256': sha(path),
            'expected': expected,
            'actual': actual,
            'returncode': proc.returncode,
            'pass': passed,
            'violations': payload.get('violations', []),
            'warnings': payload.get('warnings', []),
            'stderr': proc.stderr.strip(),
            'decision': payload,
        })
    return {
        'schema_version': 'visual_presentation_quality_fixture_results.v1',
        'created_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'validator_path': str(VALIDATOR),
        'validator_sha256': sha(VALIDATOR),
        'schema_path': str(SCHEMA),
        'schema_sha256': sha(SCHEMA),
        'passed': all(r['pass'] for r in results),
        'results': results,
    }

if __name__ == '__main__':
    result = run()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result['passed'] else 1)
