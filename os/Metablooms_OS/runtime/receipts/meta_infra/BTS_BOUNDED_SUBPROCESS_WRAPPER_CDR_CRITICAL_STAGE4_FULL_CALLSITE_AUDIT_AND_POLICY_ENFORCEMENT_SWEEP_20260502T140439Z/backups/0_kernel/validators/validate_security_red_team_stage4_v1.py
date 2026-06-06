#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,sys
from pathlib import Path
def root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/"boot_manifest_v1.json").exists() and (q/"0_kernel").exists(): return q
 return Path.cwd()
def load(p): return json.loads(Path(p).read_text())
def main():
 r=root(); issues=[]; req=["0_kernel/registry/security/SECURITY_RED_TEAM_FIXTURE_SET_v1.json","0_kernel/registry/security/SECURITY_RED_TEAM_POLICY_v1.json","0_kernel/scripts/security_red_team_runner_v1.py","runtime/receipts/security/SECURITY_ARTIFACT_THREAT_MODEL_STAGE4_RECEIPT_LATEST.json","runtime/handoffs/security/SECURITY_ARTIFACT_THREAT_MODEL_STAGE4_HANDOFF_LATEST.json"]
 for x in req:
  if not (r/x).exists(): issues.append({"missing":x})
 if issues:
  print(json.dumps({"verdict":"FAIL","issues":issues},indent=2,sort_keys=True)); return 2
 fx=load(r/"0_kernel/registry/security/SECURITY_RED_TEAM_FIXTURE_SET_v1.json").get("fixtures",[])
 ids=[x.get("fixture_id") for x in fx]
 if len(fx)<16: issues.append({"fixture_count_too_low":len(fx)})
 if len(ids)!=len(set(ids)): issues.append({"duplicate_fixture_ids":True})
 reps=set(x.get("mapped_risk") for x in fx)
 for rid in "MBSEC-001 MBSEC-002 MBSEC-003 MBSEC-004 MBSEC-005 MBSEC-006 MBSEC-007 MBSEC-008 CONTROL".split():
  if rid not in reps: issues.append({"unrepresented_risk":rid})
 for x in fx:
  if x.get("mapped_risk")!="CONTROL" and x.get("expected_decision")=="ALLOW": issues.append({"malicious_allows":x.get("fixture_id")})
 p=subprocess.run([sys.executable,"-S",str(r/"0_kernel/scripts/security_red_team_runner_v1.py"),"--json"],cwd=str(r),text=True,capture_output=True,timeout=30)
 try: result=json.loads(p.stdout)
 except Exception as e: result={}; issues.append({"runner_parse_error":str(e),"stdout_tail":p.stdout[-500:]})
 if p.returncode!=0: issues.append({"runner_returncode":p.returncode,"stderr_tail":p.stderr[-500:]})
 if result.get("promotion_decision")!="PROMOTE": issues.append({"runner_promotion_decision":result.get("promotion_decision")})
 out={"verdict":"PASS" if not issues else "FAIL","fixture_count":len(fx),"runner_verdict":result.get("verdict"),"false_allow_count":result.get("false_allow_count"),"mismatch_count":result.get("mismatch_count"),"issues":issues}
 outp=r/"runtime/evals/security/SECURITY_RED_TEAM_STAGE4_VALIDATION_LATEST.json"; outp.parent.mkdir(parents=True,exist_ok=True); outp.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
 print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not issues else 20
if __name__=="__main__": raise SystemExit(main())
