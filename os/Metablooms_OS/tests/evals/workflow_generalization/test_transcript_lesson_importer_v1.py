#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/data/Metablooms_OS')
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'runtime/tmp/transcript_importer_eval'
OUT.mkdir(parents=True, exist_ok=True)
IMPORTER = ROOT / '0_kernel/importers/transcript_lesson_importer_v1.py'
ROUTER = ROOT / '0_kernel/routers/workflow_generalization_router_v1.py'
FIX = ROOT / 'tests/evals/workflow_generalization/fixtures'
LEDGER = OUT / 'import_ledger.json'

def run_case(name, expected):
    transcript = FIX / name
    candidate_json = OUT / (name + '.candidate.json')
    route_json = OUT / (name + '.route.json')
    subprocess.run([sys.executable, str(IMPORTER), str(transcript), '--out', str(candidate_json), '--ledger', str(LEDGER)], check=True)
    subprocess.run([sys.executable, str(ROUTER), '--task', 'Import old transcript and improve workflow only if better than current', '--candidate-json', str(candidate_json), '--out', str(route_json)], check=True)
    route = json.loads(route_json.read_text())
    if expected == 'adopt' and not route['candidate_adoptions']:
        raise AssertionError(f'{name} expected adopt, got {route}')
    if expected == 'reject' and not route['candidate_rejections']:
        raise AssertionError(f'{name} expected reject, got {route}')
    if expected == 'defer_or_reject' and (route['candidate_adoptions']):
        raise AssertionError(f'{name} expected no adopt, got {route}')
    return {'fixture': name, 'expected': expected, 'route': route}

results = [
    run_case('transcript_better_sandbox_visual.txt', 'adopt'),
    run_case('transcript_pc_only_regression.txt', 'reject'),
    run_case('transcript_vague.txt', 'defer_or_reject'),
]
report = {'status': 'PASS', 'results': results}
(OUT / 'TRANSCRIPT_IMPORTER_EVAL_REPORT.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
