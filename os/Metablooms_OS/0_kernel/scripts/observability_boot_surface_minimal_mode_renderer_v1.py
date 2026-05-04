#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, time
from pathlib import Path

def write(p:Path,obj):
    s=json.dumps(obj,indent=2,sort_keys=True)+"\n"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(s,encoding='utf-8'); Path(str(p)+'.sha256').write_text(hashlib.sha256(s.encode()).hexdigest()+"  "+p.name+"\n",encoding='utf-8')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--json',action='store_true'); args=ap.parse_args()
    root=Path(args.root).resolve(); state=root/'runtime/state/operator_surface'; obs=root/'runtime/traces/observability'
    guidance=json.loads((state/'LIVE_BOOT_GUIDANCE_LATEST.json').read_text(encoding='utf-8'))
    html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
    result={'artifact_type':'BOOT_SURFACE_MINIMAL_MODE_RENDER_SMOKE.v1','created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'verdict':'PASS' if ('data-section=\'boot_surface_minimal_mode\'' in html or 'data-section="boot_surface_minimal_mode"' in html) and len(guidance.get('steps',[]))>=8 else 'FAIL','guidance_steps':len(guidance.get('steps',[])),'tracker_bytes':len(html.encode())}
    write(obs/'BOOT_SURFACE_MINIMAL_MODE_RENDER_SMOKE_LATEST.json', result)
    print(json.dumps(result,indent=2,sort_keys=True)); return 0 if result['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
