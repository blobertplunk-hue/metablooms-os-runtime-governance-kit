#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE13_EVIDENCE_QUERY_UI_INTERACTIONS_AND_RESULT_PINNING'
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); a=ap.parse_args(); root=Path(a.root)
 required=[root/'runtime/state/operator_surface/EVIDENCE_QUERY_UI_INTERACTIONS_LATEST.json',root/'runtime/state/operator_surface/EVIDENCE_RESULT_PINNING_MODEL_LATEST.json',root/'OPEN_OPERATOR_VISUAL_TRACKER.html']
 issues=[str(p) for p in required if not p.is_file() or p.stat().st_size==0]
 verdict='PASS' if not issues else 'FAIL'
 print(json.dumps({'artifact_type':'MB_EVIDENCE_QUERY_UI_RENDERER_SMOKE.v1','stage_id':STAGE,'verdict':verdict,'issues':issues},indent=2,sort_keys=True))
 return 0 if verdict=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
