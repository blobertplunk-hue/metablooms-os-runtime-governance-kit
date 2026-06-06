#!/usr/bin/env python3
from __future__ import annotations
import json, argparse
from pathlib import Path

def find_root():
    p = Path(__file__).resolve()
    for q in [p.parent, *p.parents]:
        if (q / 'boot_manifest_v1.json').exists() and (q / '0_kernel').exists():
            return q
    return Path.cwd()

def decide(f):
    blockers, warnings = [], []
    if not f.get('teks_codes'):
        blockers.append('missing_teks')
    if not f.get('official_source_refs'):
        blockers.append('missing_official_source_refs')
    if not f.get('answer_key'):
        blockers.append('missing_answer_or_scoring_rule')
    if f.get('student_visible_feedback') is False:
        blockers.append('student_feedback_not_visible')
    if f.get('eb_support') == 'reveals_answer':
        blockers.append('eb_support_reveals_answer')
    if f.get('deployment') == 'blocked_network_dependency':
        blockers.append('blocked_external_dependency')
    if f.get('tts_plan') == 'needs_repair':
        warnings.append('tts_needs_control_filtering')
    if f.get('cognitive_demand') == 'copy_only':
        warnings.append('cognitive_demand_too_low')
    if f.get('distractor_parity') is False:
        warnings.append('distractor_parity_weak')
    if f.get('telemetry') is False:
        warnings.append('telemetry_missing')
    if blockers:
        return 'BLOCK', blockers + warnings
    if warnings:
        return 'WARN', warnings
    return 'PASS', []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    root = find_root()
    data = json.loads((root / 'runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE1_FIXTURES_v1.json').read_text(encoding='utf-8'))['fixtures']
    results = []
    for item in data:
        pred, reasons = decide(item.get('features', {}))
        results.append({'fixture_id': item['fixture_id'], 'expected': item['expected_decision'], 'predicted': pred, 'reasons': reasons, 'match': pred == item['expected_decision']})
    false_pass = [r for r in results if r['predicted'] == 'PASS' and r['expected'] != 'PASS']
    accuracy = round(sum(1 for r in results if r['match']) / len(results), 4) if results else 0
    promote = (not false_pass) and accuracy >= 0.9
    out = {'verdict': 'EDUCATION_VALIDITY_PASS' if promote else 'EDUCATION_VALIDITY_FAIL', 'promotion_decision': 'PROMOTE' if promote else 'BLOCK', 'accuracy': accuracy, 'fixture_count': len(results), 'false_pass_count': len(false_pass), 'results': results}
    path = root / 'runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE1_RESULTS_LATEST.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    _mb_write_json_file(path, out, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_education_validity_gate_v1_py_L57', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
    print(json.dumps(out, indent=2, sort_keys=True) if args.json else out['verdict'])
    return 0 if promote else 20

if __name__ == '__main__':
    raise SystemExit(main())
