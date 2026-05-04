#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, sys, hashlib
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/mnt/data/Metablooms_OS')
CORPUS_PATH = ROOT/'0_kernel/evals/real_task_eval_harness/REAL_TASK_CORPUS_v2.json'

def _csv_rows(text: str):
    return list(csv.reader(text.splitlines()))

def _eval_html(fx):
    html=fx['input']['html']; low=html.lower()
    checks={
      'doctype':'<!doctype html>' in low,
      'lang':bool(re.search(r'<html[^>]+lang=', html, re.I)),
      'viewport':'name="viewport"' in html or "name='viewport'" in html,
      'tokens':'--mb-' in html,
      'focus_style':'focus' in low and 'outline' in low,
      'reduced_motion':'prefers-reduced-motion' in html,
      'aria_live':'aria-live' in html,
      'tts_hidden_icon':'aria-hidden="true"' in html or "aria-hidden='true'" in html,
      'no_external_cdn':not bool(re.search(r'https?://|cdn\.', html, re.I)),
      'self_contained': '<script' in low or '<style' in low,
      'no_module_import': 'type="module"' not in low and "type='module'" not in low,
    }
    return {k:checks.get(k, False) for k in fx.get('expected_checks', checks.keys())}

def _eval_blooket(fx):
    rows=_csv_rows(fx['input']['csv'])
    header=rows[0] if rows else []
    qrows=[r for r in rows[2:] if any(c.strip() for c in r)] if len(rows)>2 else []
    checks={
      'header_exact': header == ['Question','Answer 1','Answer 2','Answer 3','Answer 4','Correct Answer'],
      'spacer_row': len(rows)>1 and all(not c.strip() for c in rows[1]),
      'four_answers': all(len(r)>=6 and all(r[i].strip() for i in range(1,5)) for r in qrows),
      'correct_answer_present': all(len(r)>5 and r[5].strip() in {'A','B','C','D'} for r in qrows),
      'answer_distribution': len({r[5].strip() for r in qrows if len(r)>5 and r[5].strip()}) > 1 if len(qrows)>2 else True,
      'no_extra_columns': all(len(r)==6 for r in rows if any(c.strip() for c in r) or r is header),
      'question_rows_present': len(qrows)>=2,
    }
    return {k:checks.get(k, False) for k in fx.get('expected_checks', checks.keys())}

def _eval_lesson(fx):
    l=fx['input']['lesson']
    checks={
      'grade': l.get('grade')==3,
      'standard': bool(str(l.get('standard','')).startswith('3.')),
      'objective': bool(l.get('objective')),
      'steps': isinstance(l.get('steps'), list) and len(l.get('steps'))>=3,
      'evidence_requirement': any('evidence' in str(x).lower() for x in list(l.get('checks_for_understanding',[]))+list(l.get('steps',[]))),
      'eb_supports': bool(l.get('eb_supports')),
      'exit_check': bool(l.get('exit_ticket') or l.get('checks_for_understanding')),
      'misconceptions': bool(l.get('misconceptions')),
      'reteach': bool(l.get('reteach')),
      'exit_ticket': bool(l.get('exit_ticket')),
    }
    return {k:checks.get(k, False) for k in fx.get('expected_checks', checks.keys())}

def _eval_research(fx):
    w=fx['input']['workflow']
    checks={
      'requires_web_run': w.get('requires_web_run') is True,
      'requires_citations': w.get('requires_citations') is True,
      'blocks_provisional_percentages': w.get('blocks_provisional_percentages') is True,
      'evidence_binding': w.get('requires_claim_evidence_binding') is True,
      'minimum_sources': int(w.get('minimum_sources',0))>=3,
      'minimum_domains': int(w.get('minimum_domains',0))>=2,
      'official_sources_preferred': w.get('official_sources_preferred') is True,
      'record_search_query': w.get('record_search_query') is True,
    }
    return {k:checks.get(k, False) for k in fx.get('expected_checks', checks.keys())}

def _eval_export(fx):
    e=fx['input']['export']
    name=e.get('filename') or e.get('primary_bundle','')
    checks={
      'primary_bundle': str(e.get('primary_bundle','')).startswith('BOOTABLE_FULL_AUTHORITY_'),
      'sidecar': str(e.get('sidecar','')).endswith('.zip.sha256'),
      'stat': e.get('requires_stat') is True,
      'zip_test': e.get('requires_zip_test') is True,
      'sha256_check': e.get('requires_sha256_check') is True,
      'clean_extract_smoke': e.get('requires_clean_extract_smoke') is True,
      'boot_smoke': e.get('requires_boot_smoke') is True,
      'phone_safe_name': len(name) <= int(e.get('max_name_length',999)) and re.match(r'^[A-Z0-9_]+\.zip$', name or '') is not None,
      'no_forbidden_words': not any(word.lower() in name.lower() for word in e.get('forbidden', [])),
      'download_manifest': e.get('download_manifest') is True,
    }
    return {k:checks.get(k, False) for k in fx.get('expected_checks', checks.keys())}

def _eval_debug(fx):
    d=fx['input']['debug']
    checks={
      'read_before_patch': d.get('requires_read_before_patch') is True,
      'root_cause': d.get('requires_root_cause') is True,
      'minimal_fix': d.get('requires_minimal_fix') is True,
      'regression_test': d.get('requires_regression_test') is True,
      'receipt': d.get('requires_receipt') is True,
      'do_not_assume_missing': d.get('do_not_assume_missing') is True,
      'probe_filesystem': d.get('probe_filesystem') is True,
      'record_failed_methods': d.get('record_failed_methods') is True,
      'fallback_selector': d.get('fallback_selector') is True,
    }
    return {k:checks.get(k, False) for k in fx.get('expected_checks', checks.keys())}

def eval_fixture(fx):
    domain=fx['domain']
    if domain=='educational_html': checks=_eval_html(fx)
    elif domain=='blooket_csv': checks=_eval_blooket(fx)
    elif domain=='lesson_plan': checks=_eval_lesson(fx)
    elif domain=='research_see': checks=_eval_research(fx)
    elif domain=='artifact_export': checks=_eval_export(fx)
    elif domain=='repair_debugging': checks=_eval_debug(fx)
    else: checks={'known_domain':False}
    return checks, all(checks.values())

def run(root: Path=ROOT):
    data=json.loads((root/'0_kernel/evals/real_task_eval_harness/REAL_TASK_CORPUS_v2.json').read_text(encoding='utf-8'))
    results=[]
    for fx in data['fixtures']:
        checks,ok=eval_fixture(fx)
        results.append({'fixture_id':fx['id'],'domain':fx['domain'],'verdict':'PASS' if ok else 'FAIL','checks':checks})
    passed=sum(1 for r in results if r['verdict']=='PASS')
    domains=sorted(set(r['domain'] for r in results))
    return {'schema_version':'v2','verdict':'PASS' if passed==len(results) else 'FAIL','passed':passed,'total':len(results),'pass_rate':passed/len(results) if results else 0,'domains':domains,'results':results}

if __name__=='__main__':
    summary=run(ROOT)
    print(json.dumps(summary, indent=2))
    sys.exit(0 if summary['verdict']=='PASS' else 1)
