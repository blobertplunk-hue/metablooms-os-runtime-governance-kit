#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
FORBIDDEN=set("╭╮╰╯│┌┐└┘├┤┬┴┼─")
TOP='TRACKER ▸'
def sha256_file(p: Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()
def rel(root: Path, p: Path)->str:
    return str(p.resolve().relative_to(root.resolve()))
def main(argv=None)->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--state', required=True)
    ap.add_argument('--receipt', required=True)
    ap.add_argument('--handoff', required=True)
    ap.add_argument('--stage', required=True)
    ap.add_argument('--preview', required=True)
    ap.add_argument('--report', required=True)
    args=ap.parse_args(argv)
    root=Path(args.root); state_p=Path(args.state); receipt=Path(args.receipt); handoff=Path(args.handoff); preview_p=Path(args.preview)
    errors=[]
    for label,p,is_dir in [('root',root,True),('state',state_p,False),('receipt',receipt,False),('handoff',handoff,False),('preview',preview_p,False)]:
        if is_dir and not p.is_dir(): errors.append(f'{label}_missing')
        if not is_dir and not p.is_file(): errors.append(f'{label}_missing')
    state={}; preview=''
    if not errors:
        try: state=json.loads(state_p.read_text(encoding='utf-8'))
        except Exception as e: errors.append(f'state_json_invalid:{e}')
        try: preview=preview_p.read_text(encoding='utf-8')
        except Exception as e: errors.append(f'preview_read_failed:{e}')
    if not errors:
        rr=rel(root, receipt); hr=rel(root, handoff); rs=sha256_file(receipt); hs=sha256_file(handoff)
        ev=state.get('evidence',[]); hist=state.get('history',[])
        if state.get('current_stage') != args.stage: errors.append('stale_current_stage')
        if not any(e.get('kind')=='receipt' and e.get('path')==rr and e.get('sha256')==rs for e in ev): errors.append('stale_or_missing_receipt_evidence')
        if not any(e.get('kind')=='handoff' and e.get('path')==hr and e.get('sha256')==hs for e in ev): errors.append('stale_or_missing_handoff_evidence')
        if not any(h.get('stage')==args.stage and h.get('receipt_path')==rr and h.get('handoff_path')==hr for h in hist): errors.append('stale_or_missing_history_binding')
        if not preview.startswith(TOP): errors.append('preview_not_first_tracker_marker')
        if any(ch in FORBIDDEN for ch in preview): errors.append('forbidden_box_or_pipe_layout')
        if '%' in preview: errors.append('fake_percent_or_percent_symbol_present')
        max_width=max((len(line) for line in preview.splitlines()), default=0)
        if max_width>64: errors.append(f'mobile_width_exceeds_64:{max_width}')
    report={'artifact_type':'TRACKER_STALE_STATE_VALIDATION_REPORT','stage':args.stage,'status':'PASS' if not errors else 'FAIL','errors':errors,'checks':{'stale_state_rejected':'PASS' if errors else 'NOT_APPLICABLE_ON_FRESH_STATE','preview_top_marker':'PASS' if preview.startswith(TOP) else 'FAIL','no_forbidden_layout':'PASS' if not any(ch in FORBIDDEN for ch in preview) else 'FAIL','no_percent_symbol':'PASS' if '%' not in preview else 'FAIL'}}
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1
if __name__=='__main__':
    raise SystemExit(main())
