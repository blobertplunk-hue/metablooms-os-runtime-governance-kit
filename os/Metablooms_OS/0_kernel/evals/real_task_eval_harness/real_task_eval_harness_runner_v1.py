#!/usr/bin/env python3
from __future__ import annotations
import json, csv, re, sys, hashlib, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/data/Metablooms_OS')
FIXTURE_PATH = ROOT/'0_kernel/evals/real_task_eval_harness/REAL_TASK_EVAL_FIXTURES_v1.json'

def _has(path: str) -> bool:
    return (ROOT/path).exists()

def eval_html(fx):
    html = fx['input']['html']
    checks = {
        'doctype': '<!doctype html>' in html.lower(),
        'lang': bool(re.search(r'<html[^>]+lang=', html, re.I)),
        'viewport': 'name="viewport"' in html or "name='viewport'" in html,
        'tokens': '--mb-' in html,
        'aria_live': 'aria-live' in html,
        'tts_no_icon_text': 'aria-hidden="true"' in html or "aria-hidden='true'" in html,
        'no_cdn': not bool(re.search(r'https?://', html)),
    }
    return checks, all(checks.values())

def eval_blooket_csv(fx):
    rows = list(csv.reader(fx['input']['csv'].splitlines()))
    checks = {
        'has_spacer_before_first_question': len(rows) > 1 and all(not cell.strip() for cell in rows[1]),
        'question_rows_present': len(rows) >= 3,
        'four_answers': all(len(r) >= 6 for r in rows[2:] if any(c.strip() for c in r)),
        'correct_answer_not_blank': all((len(r) > 5 and r[5].strip()) for r in rows[2:] if any(c.strip() for c in r)),
        'answer_distribution_not_all_A': len({r[5].strip() for r in rows[2:] if len(r)>5 and r[5].strip()}) > 1,
    }
    return checks, all(checks.values())

def eval_artifact_presence(fx):
    checks = {name: _has(path) for name,path in fx['expected_paths'].items()}
    return checks, all(checks.values())

def eval_research_workflow(fx):
    checks = {
        'requires_web_run_for_see': fx['input'].get('see_requires_web_run') is True,
        'requires_citations': fx['input'].get('requires_citations') is True,
        'blocks_provisional_claims': fx['input'].get('blocks_provisional_claims') is True,
    }
    return checks, all(checks.values())

def run(root: Path = ROOT):
    fixtures = json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))['fixtures']
    results=[]
    for fx in fixtures:
        if fx['type']=='educational_html': checks, ok = eval_html(fx)
        elif fx['type']=='blooket_csv': checks, ok = eval_blooket_csv(fx)
        elif fx['type'] in ('lesson_workflow','artifact_export','stage_exit_prompt_gate'): checks, ok = eval_artifact_presence(fx)
        elif fx['type']=='research_workflow': checks, ok = eval_research_workflow(fx)
        else: checks, ok = {'unknown_type': False}, False
        results.append({'fixture_id': fx['id'], 'type': fx['type'], 'verdict':'PASS' if ok else 'FAIL', 'checks':checks})
    passed=sum(1 for r in results if r['verdict']=='PASS')
    summary={'verdict':'PASS' if passed==len(results) else 'FAIL', 'passed':passed, 'total':len(results), 'pass_rate': passed/len(results) if results else 0, 'results':results}
    return summary

if __name__ == '__main__':
    summary=run(ROOT)
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary['verdict']=='PASS' else 1)
