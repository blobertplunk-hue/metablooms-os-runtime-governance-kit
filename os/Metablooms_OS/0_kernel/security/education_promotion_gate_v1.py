#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
def find_root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); args=ap.parse_args(); root=find_root(); report=root/'runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_PROMOTION_REPORT_LATEST.json'; issues=[]
 if not report.exists(): issues.append('promotion_report_missing')
 else:
  data=json.loads(report.read_text());
  if data.get('promotion_decision')!='PROMOTE': issues.append('promotion_decision_not_promote')
  if data.get('false_pass_count')!=0: issues.append('false_passes_present')
  if float(data.get('accuracy',0))<0.95: issues.append('accuracy_below_threshold')
 out={'schema_version':'EDUCATION_PROMOTION_GATE_v1','verdict':'EDUCATION_PROMOTION_GATE_PASS' if not issues else 'EDUCATION_PROMOTION_GATE_FAIL','issues':issues,'report_path':str(report)}; print(json.dumps(out,indent=2,sort_keys=True) if args.json else out['verdict']); return 0 if not issues else 20
if __name__=='__main__': raise SystemExit(main())
