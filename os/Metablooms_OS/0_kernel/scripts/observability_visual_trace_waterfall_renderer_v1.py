#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); args=ap.parse_args()
    root=Path(args.root).resolve()
    required=['runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl','runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json','runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json','runtime/state/operator_surface/VISUAL_TRACE_WATERFALL_LATEST.json','OPEN_OPERATOR_VISUAL_TRACKER.html']
    issues=[p for p in required if not (root/p).is_file()]
    html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8') if (root/'OPEN_OPERATOR_VISUAL_TRACKER.html').exists() else ''
    for marker in ['data-section="visual_trace_waterfall"','data-section="evidence_filters"','data-section="trace_waterfall_rows"']:
        if marker not in html: issues.append('missing_marker:'+marker)
    out={'artifact_type':'MB_VISUAL_TRACE_WATERFALL_RENDERER_SMOKE.v1','verdict':'PASS' if not issues else 'FAIL','issues':issues}
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
