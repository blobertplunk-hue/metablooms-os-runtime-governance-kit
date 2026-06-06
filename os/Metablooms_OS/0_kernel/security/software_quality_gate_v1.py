#!/usr/bin/env python3
from __future__ import annotations
import json,time
from pathlib import Path
def find_root():
 p=Path(__file__).resolve()
 for parent in [p.parent,*p.parents]:
  if (parent/'boot_manifest_v1.json').exists() and (parent/'0_kernel').exists(): return parent
 return Path.cwd()
def main():
 root=find_root(); sc=json.loads((root/'runtime/evals/software_quality/SOFTWARE_QUALITY_STAGE2_SCORECARD_LATEST.json').read_text()); fx=json.loads((root/'runtime/evals/software_quality/SOFTWARE_QUALITY_REGRESSION_FIXTURES_v2.json').read_text())
 promote=float(sc.get('overall_score',0))>=0.90 and int(sc.get('false_pass_count',1))==0 and float(sc.get('gate_pass_ratio',0))>=1.0 and len(fx.get('fixtures',[]))>=8
 print(json.dumps({'schema_version':'MB_SOFTWARE_QUALITY_PROMOTION_GATE_v1','verdict':'SOFTWARE_QUALITY_PROMOTION_GATE_PASS' if promote else 'SOFTWARE_QUALITY_PROMOTION_GATE_BLOCK','promotion_decision':'PROMOTE' if promote else 'BLOCK','overall_score':sc.get('overall_score'),'false_pass_count':sc.get('false_pass_count'),'gate_pass_ratio':sc.get('gate_pass_ratio'),'fixture_count':len(fx.get('fixtures',[])),'checked_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())},indent=2,sort_keys=True))
 return 0 if promote else 20
if __name__=='__main__': raise SystemExit(main())
