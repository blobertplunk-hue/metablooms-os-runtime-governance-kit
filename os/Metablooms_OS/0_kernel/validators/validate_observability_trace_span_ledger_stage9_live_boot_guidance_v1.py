#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys,time,hashlib
from pathlib import Path
STAGE="OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_EXTRACTOR_AND_TRACKER_DEEP_LINKS"
def sha_file(p):
 h=hashlib.sha256();
 with Path(p).open("rb") as f:
  [h.update(c) for c in iter(lambda:f.read(1024*1024), b"")]
 return h.hexdigest()
def load(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def run(cmd,cwd):
 cp=subprocess.run(cmd,cwd=str(cwd),text=True,capture_output=True,timeout=120)
 try: out=json.loads(cp.stdout)
 except Exception: out={"raw_stdout":cp.stdout,"stderr":cp.stderr}
 return {"cmd":cmd,"returncode":cp.returncode,"stdout":out,"stderr":cp.stderr}
def write(p,obj):
 text=json.dumps(obj,indent=2,sort_keys=True)+"\n"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8"); Path(str(p)+".sha256").write_text(hashlib.sha256(text.encode()).hexdigest()+"  "+p.name+"\n",encoding="utf-8")
def main(argv=None):
 ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--json",action="store_true"); args=ap.parse_args(argv); root=Path(args.root).resolve(); issues=[]; checks=[]
 required=["0_kernel/registry/observability/MB_LIVE_BOOT_GUIDANCE_SCHEMA_v1.json","0_kernel/registry/observability/MB_LIVE_BOOT_GUIDANCE_EXTRACTOR_POLICY_v1.json","0_kernel/scripts/observability_live_boot_guidance_extractor_v1.py","runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json","runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.md","OPEN_OPERATOR_VISUAL_TRACKER.html","NEW_CHAT_START_HERE.md","0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md"]
 for rel in required:
  p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({"path":rel,"exists_nonempty":ok,"sha256":sha_file(p) if ok else None})
  if not ok: issues.append("missing_or_empty:"+rel)
 if not issues:
  policy=load(root/"0_kernel/registry/observability/MB_LIVE_BOOT_GUIDANCE_EXTRACTOR_POLICY_v1.json"); guidance=load(root/"runtime/state/operator_surface/LIVE_BOOT_GUIDANCE_LATEST.json")
  if guidance.get("artifact_type")!="MB_LIVE_BOOT_GUIDANCE.v1": issues.append("bad_guidance_artifact_type")
  if guidance.get("verdict")!="PASS": issues.append("guidance_not_pass")
  if len(guidance.get("steps",[]))<8: issues.append("too_few_live_steps")
  if not any(policy["required_entrypoint"] in s.get("command_or_path","") for s in guidance.get("steps",[])): issues.append("guidance_missing_wrapper_step")
  for link in guidance.get("deep_links",[]):
   if not (root/link.get("path","")).exists(): issues.append("deep_link_target_missing:"+link.get("path",""))
  html=(root/"OPEN_OPERATOR_VISUAL_TRACKER.html").read_text(encoding="utf-8")
  for marker in ["data-section=\"live_boot_guidance_deep_links\"","LIVE_BOOT_GUIDANCE_LATEST.json","Current live boot steps"]:
   if marker not in html: issues.append("tracker_missing_marker:"+marker)
  for rel in ["NEW_CHAT_START_HERE.md","0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md","OPEN_OPERATOR_VISUAL_TRACKER.html"]:
   txt=(root/rel).read_text(encoding="utf-8",errors="ignore")
   if policy["required_entrypoint"] not in txt: issues.append("live_surface_missing_wrapper:"+rel)
   for frag in policy["forbidden_live_fragments"]:
    if frag in txt: issues.append("forbidden_live_fragment:"+rel)
  ptrs=[load(root/r) for r in ["CURRENT_FULL_AUTHORITY_POINTER_v1.json","runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json","0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json"]]
  if ptrs[0]!=ptrs[1] or ptrs[0]!=ptrs[2]: issues.append("authority_pointer_copies_not_identical")
  if ptrs[0].get("stage_id")!=STAGE or ptrs[0].get("last_stage")!=STAGE: issues.append("pointer_not_stage9")
  for k in ["live_boot_guidance","live_boot_guidance_markdown","live_boot_guidance_validation","live_boot_guidance_extractor"]:
   if k not in ptrs[0]: issues.append("pointer_missing:"+k)
 extractor=run([sys.executable,str(root/"0_kernel/scripts/observability_live_boot_guidance_extractor_v1.py"),"--root",str(root),"--json"],root)
 newchat=run([sys.executable,str(root/"runtime/governance/new_chat_start_contract_validator_v1.py"),str(root)],root)
 scanner=run([sys.executable,str(root/"0_kernel/scripts/observability_historical_callsite_quarantine_v1.py"),"--root",str(root),"--json"],root)
 smoke=[{"name":"extractor_passes","pass":extractor["returncode"]==0 and extractor["stdout"].get("verdict")=="PASS","result":extractor},{"name":"new_chat_validator_allows","pass":newchat["returncode"]==0 and newchat["stdout"].get("decision")=="ALLOW","result":newchat},{"name":"historical_callsite_scanner_passes","pass":scanner["returncode"]==0 and scanner["stdout"].get("verdict")=="PASS","result":scanner}]
 for s in smoke:
  if not s["pass"]: issues.append("smoke_failed:"+s["name"])
 report={"artifact_type":"OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_VALIDATION.v1","stage_id":STAGE,"created_utc":time.strftime("%Y%m%dT%H%M%SZ",time.gmtime()),"verdict":"PASS" if not issues else "FAIL","checks":checks,"smoke_checks":smoke,"issues":issues}
 out=root/"runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE9_LIVE_BOOT_GUIDANCE_VALIDATION_LATEST.json"; write(out,report); print(json.dumps(report,indent=2,sort_keys=True)); return 0 if report["verdict"]=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
