#!/usr/bin/env python3
from __future__ import annotations
import ast, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "0_kernel/registry/tool_governance/ATOMIC_APPEND_LOG_WRITER_CALLSITE_POLICY_STAGE3_v1.json"
EXCLUDE_PARTS = ("runtime/receipts/", "runtime/stage_bundles/", "__pycache__", ".stage3_append_bak_", ".stage4_bak_")
DEFERRED = {
    "0_kernel/scripts/runtime_pulse_logger_v1.py": "hash_chain_preservation_required",
    "runtime/governance/bts_v4/BTS.py": "bts_hash_chain_preservation_required",
    "runtime/governance/legacy_archives/claude_memory_sync_writer_v1.py": "legacy_archive_exempt",
}

def scan():
    rows=[]
    files=list((ROOT/'0_kernel').rglob('*.py'))+list((ROOT/'runtime').rglob('*.py'))+list((ROOT/'tests').rglob('*.py'))
    for p in files:
        rel=str(p.relative_to(ROOT))
        if any(x in rel for x in EXCLUDE_PARTS):
            continue
        try:
            tree=ast.parse(p.read_text(encoding='utf-8'))
        except Exception as exc:
            rows.append({'file':rel,'line':0,'classification':'parse_error','detail':str(exc)})
            continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            func=n.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
            if name != 'open':
                continue
            append=False
            if len(n.args)>=2 and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value,str) and 'a' in n.args[1].value:
                append=True
            for kw in n.keywords:
                if kw.arg=='mode' and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value,str) and 'a' in kw.value.value:
                    append=True
            if append:
                rows.append({'file':rel,'line':n.lineno,'classification':DEFERRED.get(rel,'blocking_live_direct_append_open'), 'detail':'direct append-open call'})
    return rows

def main():
    policy=json.loads(POLICY.read_text(encoding='utf-8')) if POLICY.exists() else {}
    rows=scan()
    blocking=[r for r in rows if str(r.get('classification','')).startswith('blocking') or r.get('classification')=='parse_error']
    out={
        'artifact_type':'AtomicAppendLogWriterCallsitePolicyStage3Result.v1',
        'created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'policy_path':str(POLICY.relative_to(ROOT)) if POLICY.exists() else None,
        'canonical_writer':policy.get('canonical_writer'),
        'compat_adapter':policy.get('compat_adapter'),
        'remaining_direct_append_open_count':len(rows),
        'blocking_count':len(blocking),
        'warning_count':len(rows)-len(blocking),
        'remaining':rows,
        'verdict':'PASS' if not blocking else 'FAIL'
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['verdict']=='PASS' else 2
if __name__ == '__main__':
    raise SystemExit(main())
