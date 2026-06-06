#!/usr/bin/env python3
from __future__ import annotations
import json, time, zipfile
from pathlib import Path

def collect(root: Path, data_dir: Path=Path('/mnt/data')):
    receipts=list((root/'runtime').rglob('*RECEIPT*.json')) if (root/'runtime').exists() else []
    handoffs=list((root/'runtime').rglob('*HANDOFF*.json')) if (root/'runtime').exists() else []
    zips=list(data_dir.glob('*.zip'))
    success=fail=unknown=0
    for p in receipts+handoffs:
        try:
            obj=json.loads(p.read_text(encoding='utf-8'))
            v=str(obj.get('verdict') or obj.get('status') or obj.get('decision') or '').upper()
            if 'FAIL' in v or 'BLOCK' in v: fail+=1
            elif 'PASS' in v or 'READY' in v or 'ALLOW' in v: success+=1
            else: unknown+=1
        except Exception: unknown+=1
    known=success+fail
    baseline={'schema_version':'v1','honesty_label':'artifact-delivery proxy metrics for sandbox OS; not production SaaS DORA metrics','events_modeled':len(receipts)+len(handoffs)+len(zips),'receipt_json_files':len(receipts),'handoff_json_files':len(handoffs),'authority_or_delta_zips_in_mnt_data':len(zips),'change_failure_block_rate_proxy':(fail/known if known else None),'success_count':success,'failure_or_block_count':fail,'unknown_count':unknown,'created_at':time.time()}
    out=root/'runtime/state/DORA_STYLE_OS_METRICS_BASELINE_v1.json'; out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(baseline, indent=2), encoding='utf-8')
    return baseline

if __name__=='__main__':
    print(json.dumps(collect(Path('/mnt/data/Metablooms_OS')), indent=2))
