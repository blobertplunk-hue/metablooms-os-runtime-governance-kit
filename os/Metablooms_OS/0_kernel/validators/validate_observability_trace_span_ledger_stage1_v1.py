#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
REQUIRED=['0_kernel/registry/observability/MB_TRACE_SPAN_LEDGER_SPEC_v2.json','0_kernel/registry/operator_surface/MB_CLI_COMMAND_SPEC_v5.json','0_kernel/validators/validate_observability_trace_span_ledger_stage1_v1.py','docs/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE1.md','runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl','runtime/traces/observability/TRACE_SUMMARY_LATEST.json','runtime/receipts/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE1_RECEIPT_LATEST.json','runtime/handoffs/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE1_HANDOFF_LATEST.json','bin/mb']
FIELDS=['schema_version','trace_id','span_id','parent_span_id','name','stage_name','event','status','timestamp_utc','attributes']; VALID_STATUS={'OK','WARN','ERROR','BLOCKED'}
def find_root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument('--root'); ap.add_argument('--json',action='store_true'); a=ap.parse_args(argv); root=Path(a.root) if a.root else find_root(); checks={rel:(root/rel).exists() for rel in REQUIRED}; issues=[]
 for rel,ok in checks.items():
  if not ok: issues.append({'missing':rel})
 ledger=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl'; rows=[]; parse_errors=[]
 if ledger.exists():
  for idx,line in enumerate(ledger.read_text(encoding='utf-8').splitlines(),start=1):
   if not line.strip(): continue
   try: rec=json.loads(line)
   except Exception as e: parse_errors.append({'line':idx,'error':str(e)}); continue
   rows.append(rec); missing=[f for f in FIELDS if f not in rec]
   if missing: issues.append({'line':idx,'missing_fields':missing})
   if rec.get('status') not in VALID_STATUS: issues.append({'line':idx,'invalid_status':rec.get('status')})
   if rec.get('status') in {'ERROR','BLOCKED'} and not any(k in rec.get('attributes',{}) for k in ['error','blocker','reason']): issues.append({'line':idx,'missing_error_or_blocker_attributes':True})
 if not rows: issues.append({'empty_or_missing_ledger':str(ledger)})
 if parse_errors: issues.append({'parse_errors':parse_errors[:10]})
 verdict='PASS' if not issues else 'FAIL'; out={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE1_VALIDATION_v1','verdict':verdict,'root':str(root),'checks':checks,'span_count':len(rows),'issues':issues}; print(json.dumps(out,indent=2,sort_keys=True)); return 0 if verdict=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
