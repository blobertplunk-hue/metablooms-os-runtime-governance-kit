#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / 'runtime' / 'state' / 'GENERAL_CAPABILITY_RELIABILITY_LEDGER_v1.jsonl'

METHODS = {
    'filesystem_archive_export': [
        {'method_id':'shell_zip', 'probe':['zip','-v'], 'rank':1},
        {'method_id':'python3_S_zipfile', 'probe':['python3','-S','-c','import zipfile; print("zipfile-ok")'], 'rank':2},
        {'method_id':'tar_gzip_if_zip_unavailable', 'probe':['tar','--version'], 'rank':9},
    ],
    'browser_render': [
        {'method_id':'playwright_managed_browser', 'probe':['python3','-S','-c','import importlib.util; raise SystemExit(0 if importlib.util.find_spec("playwright") else 1)'], 'rank':1, 'fallback_label':'true_browser_preferred'},
        {'method_id':'system_chromium_headless', 'probe':['bash','-lc','command -v chromium || command -v chromium-browser || command -v google-chrome'], 'rank':2, 'fallback_label':'true_browser_preferred'},
        {'method_id':'weasyprint_proxy', 'probe':['bash','-lc','command -v weasyprint'], 'rank':6, 'fallback_label':'render_proxy_with_limitation'},
        {'method_id':'static_dom_validator', 'probe':['python3','-S','-c','print("static-ok")'], 'rank':7, 'fallback_label':'static_only_with_limitation'},
    ],
    'python_execution': [
        {'method_id':'python3_S_stdlib', 'probe':['python3','-S','-c','print("ok")'], 'rank':1},
        {'method_id':'shell_coreutils', 'probe':['bash','-lc','command -v bash && command -v sha256sum'], 'rank':2},
    ],
    'download_link_exposure': [
        {'method_id':'short_phone_safe_sandbox_link', 'probe':['python3','-S','-c','from pathlib import Path; print("link-precheck-ok")'], 'rank':1},
    ],
    'web_research_see': [
        {'method_id':'web_run_external', 'probe':['python3','-S','-c','print("requires-web.run-outside-subprocess")'], 'rank':1},
    ]
}

def run_probe(cmd, timeout=5):
    try:
        cp=subprocess.run(cmd, cwd=str(ROOT), text=True, capture_output=True, timeout=timeout)
        return {'exit_code':cp.returncode, 'stdout':cp.stdout[:500], 'stderr':cp.stderr[:500]}
    except Exception as e:
        return {'exit_code':999, 'stdout':'', 'stderr':repr(e)}

def resolve(capability_need:str, task_id:str='ad_hoc'):
    candidates=METHODS.get(capability_need, [])
    decisions=[]
    selected=None
    for m in sorted(candidates, key=lambda x:x.get('rank',99)):
        probe=run_probe(m['probe'])
        record={'method_id':m['method_id'], 'rank':m.get('rank'), 'probe':probe}
        decisions.append(record)
        if probe['exit_code']==0 and selected is None:
            selected={**m, 'probe':probe}
            break
    if selected:
        primary = selected.get('rank',99) <= 2
        decision = 'ALLOW_PRIMARY' if primary else 'ALLOW_FALLBACK_WITH_LIMITATION'
        limitation = None if primary else selected.get('fallback_label','fallback_with_limitation')
        selected_method=selected['method_id']
    else:
        decision='DENY_BLOCKED'; limitation='no_candidate_method_probe_passed'; selected_method=None
    out={
        'timestamp_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'task_id':task_id,
        'capability_need':capability_need,
        'candidate_methods':[d['method_id'] for d in decisions],
        'selected_method':selected_method,
        'decision':decision,
        'limitation_label':limitation,
        'probe_records':decisions,
        'evidence_paths':[],
    }
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open('a', encoding='utf-8') as f:
        f.write(json.dumps(out, sort_keys=True)+'\n')
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--capability', required=True)
    ap.add_argument('--task-id', default='ad_hoc')
    ap.add_argument('--out')
    args=ap.parse_args()
    result=resolve(args.capability, args.task_id)
    data=json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        p=Path(args.out); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(data+'\n', encoding='utf-8')
    else:
        print(data)
    raise SystemExit(0 if result['decision']!='DENY_BLOCKED' else 2)

if __name__=='__main__':
    main()
