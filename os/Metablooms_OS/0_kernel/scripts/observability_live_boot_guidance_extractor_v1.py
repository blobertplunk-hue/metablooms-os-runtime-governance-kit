#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,hashlib,time
from pathlib import Path
STAGE="OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS"
def write(p,text):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8"); Path(str(p)+".sha256").write_text(hashlib.sha256(text.encode()).hexdigest()+"  "+p.name+"\n",encoding="utf-8")
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--json",action="store_true"); args=ap.parse_args(argv); root=Path(args.root).resolve()
 policy=json.loads((root/"0_kernel/registry/observability/MB_LIVE_BOOT_GUIDANCE_EXTRACTOR_POLICY_v1.json").read_text()); pointer=json.loads((root/"CURRENT_FULL_AUTHORITY_POINTER_v1.json").read_text())
 steps=[
 {"order":1,"action":"Verify authority pointer and external sidecar.","command_or_path":"CURRENT_FULL_AUTHORITY_POINTER_v1.json + external .sha256 sidecar","evidence_path":"CURRENT_FULL_AUTHORITY_POINTER_v1.json","deep_link":"#live-step-1","gate":True},
 {"order":2,"action":"Open the operator tracker before work resumes.","command_or_path":"OPEN_OPERATOR_VISUAL_TRACKER.html","evidence_path":"OPEN_OPERATOR_VISUAL_TRACKER.html","deep_link":"#live-step-2","gate":True},
 {"order":3,"action":"Run boot-critical governance loader.","command_or_path":"python runtime/governance/boot_critical_governance_loader_v1.py","evidence_path":"runtime/governance/boot_critical_governance_loader_v1.py","deep_link":"#live-step-3","gate":True},
 {"order":4,"action":"Run scatter prevention and fresh-chat rehearsal.","command_or_path":"python runtime/governance/governance_scatter_prevention_v1.py && python runtime/governance/fresh_chat_boot_rehearsal_v1.py","evidence_path":"runtime/governance/fresh_chat_boot_rehearsal_v1.py","deep_link":"#live-step-4","gate":True},
 {"order":5,"action":"Validate the new-chat start contract.","command_or_path":"python runtime/governance/new_chat_start_contract_validator_v1.py /mnt/data/Metablooms_OS","evidence_path":"runtime/governance/new_chat_start_contract_validator_v1.py","deep_link":"#live-step-5","gate":True},
 {"order":6,"action":"Run runtime starter smoke through the wrapper only.","command_or_path":policy["required_entrypoint"],"evidence_path":"runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py","deep_link":"#live-step-6","gate":True},
 {"order":7,"action":"Validate historical-callsite quarantine and live boot guidance.","command_or_path":"python 0_kernel/validators/validate_observability_trace_span_ledger_stage8_historical_callsite_quarantine_v1.py --root /mnt/data/Metablooms_OS --json && python 0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py --root /mnt/data/Metablooms_OS --json","evidence_path":"0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py","deep_link":"#live-step-7","gate":True},
 {"order":8,"action":"Execute exactly one bounded governed stage, then write receipt and handoff.","command_or_path":"stage-specific governed command","evidence_path":"runtime/receipts/","deep_link":"#live-step-8","gate":True}]
 links=[{"label":"Operator tracker","path":"OPEN_OPERATOR_VISUAL_TRACKER.html","kind":"html","href":"OPEN_OPERATOR_VISUAL_TRACKER.html"},{"label":"Live boot guidance JSON","path":policy["output_json"],"kind":"json","href":policy["output_json"]},{"label":"Live boot guidance Markdown","path":policy["output_markdown"],"kind":"markdown","href":policy["output_markdown"]},{"label":"New-chat contract","path":"0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md","kind":"markdown","href":"0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md"},{"label":"Historical quarantine index","path":"runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json","kind":"json","href":"runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json"},{"label":"Stage 9 validator","path":"0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py","kind":"python","href":"0_kernel/validators/validate_observability_trace_span_ledger_stage9_live_boot_guidance_v1.py"}]
 issues=[]
 for rel in policy["live_surfaces"]:
  p=root/rel
  if not p.is_file(): issues.append("missing_live_surface:"+rel); continue
  txt=p.read_text(encoding="utf-8",errors="ignore")
  if policy["required_entrypoint"] not in txt and rel!="OPEN_OPERATOR_VISUAL_TRACKER.html": issues.append("live_surface_missing_wrapper:"+rel)
  for frag in policy["forbidden_live_fragments"]:
   if frag in txt: issues.append("forbidden_live_fragment:"+rel+":"+frag)
 artifact={"artifact_type":"MB_LIVE_BOOT_GUIDANCE.v1","stage_id":STAGE,"created_utc":time.strftime("%Y%m%dT%H%M%SZ",time.gmtime()),"verdict":"PASS" if not issues else "FAIL","current_authority":{"stage_id":pointer.get("stage_id"),"authority_zip":pointer.get("authority_zip") or pointer.get("export_zip"),"sidecar":pointer.get("authority_zip_sha256_sidecar") or pointer.get("export_sha256_sidecar"),"canonical_working_root":str(root)},"steps":steps,"deep_links":links,"forbidden_live_fragments":policy["forbidden_live_fragments"],"issues":issues}
 write(root/policy["output_json"], json.dumps(artifact,indent=2,sort_keys=True)+"\n")
 md=["# MetaBlooms Live Boot Guidance","",f"Stage: `{STAGE}`","","## Current live steps only",""]
 for s in steps: md.append(f"{s['order']}. **{s['action']}**  \n   `{s['command_or_path']}`  \n   Evidence: `{s['evidence_path']}`")
 md += ["","## Deep links",""]
 for l in links: md.append(f"- [{l['label']}]({l['href']}) — `{l['path']}`")
 write(root/policy["output_markdown"], "\n".join(md)+"\n")
 print(json.dumps(artifact,indent=2,sort_keys=True)); return 0 if artifact["verdict"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
