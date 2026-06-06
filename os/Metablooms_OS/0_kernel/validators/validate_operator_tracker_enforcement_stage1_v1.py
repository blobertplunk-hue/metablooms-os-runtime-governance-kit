#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, sys
from pathlib import Path

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def main(argv=None) -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--report', required=True)
    args=ap.parse_args(argv)
    root=Path(args.root)
    report=Path(args.report)
    preview=root/'runtime/handoffs/operator_tracker/CURRENT_OPERATOR_TRACKER_PREVIEW_LATEST.md'
    policy=root/'0_kernel/registry/operator_surface/OPERATOR_TRACKER_ENFORCEMENT_POLICY_v1.json'
    errors=[]
    checks={}
    def check(name, cond, msg):
        checks[name]='PASS' if cond else 'FAIL'
        if not cond: errors.append(msg)
    check('root_exists', root.is_dir(), f'root missing: {root}')
    check('preview_exists', preview.is_file(), f'preview missing: {preview}')
    check('policy_exists', policy.is_file(), f'policy missing: {policy}')
    text=preview.read_text(encoding='utf-8') if preview.is_file() else ''
    for required in ['Latest bootable full OS','Workstream map','Next pointer','Atomic append-log writer','optional']:
        check('preview_contains_'+required.lower().replace(' ','_'), required in text, f'preview missing required text: {required}')
    if policy.is_file():
        obj=json.loads(policy.read_text(encoding='utf-8'))
        check('policy_active', obj.get('status')=='ACTIVE', 'policy not ACTIVE')
        boot=Path(obj.get('latest_bootable_authority',''))
        check('latest_bootable_exists', boot.is_file(), f'latest bootable missing: {boot}')
        if boot.is_file() and obj.get('latest_bootable_authority_sha256'):
            check('latest_bootable_sha_matches', sha256_file(boot)==obj['latest_bootable_authority_sha256'], 'latest bootable sha mismatch')
    out={'validator':'validate_operator_tracker_enforcement_stage1_v1','status':'PASS' if not errors else 'FAIL','errors':errors,'checks':checks,'preview_path':str(preview),'policy_path':str(policy)}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(out, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1
if __name__=='__main__':
    raise SystemExit(main())
