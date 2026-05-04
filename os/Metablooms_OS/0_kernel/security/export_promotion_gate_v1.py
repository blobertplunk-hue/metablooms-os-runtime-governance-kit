#!/usr/bin/env python3
from __future__ import annotations
import argparse,collections,json,re,zipfile
from pathlib import Path
REQUIRED=['Metablooms_OS/0_kernel/lib/archive_extraction_route_v1.py', 'Metablooms_OS/0_kernel/registry/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_POLICY_v2.json', 'Metablooms_OS/runtime/receipts/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_STAGE2_RECEIPT_LATEST.json', 'Metablooms_OS/runtime/handoffs/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_STAGE2_HANDOFF_LATEST.json', 'Metablooms_OS/runtime/export_promotion/EXPORT_FILESYSTEM_SAFETY_PROOF_LATEST.json', 'Metablooms_OS/bin/mb', 'Metablooms_OS/0_kernel/scripts/stage_runner_v1.py', 'Metablooms_OS/0_kernel/scripts/cartridge_executor_v1.py', 'Metablooms_OS/0_kernel/security/security_gate_enforcer_v1.py', 'Metablooms_OS/0_kernel/security/export_promotion_gate_v1.py', 'Metablooms_OS/0_kernel/registry/security/SECURITY_ARTIFACT_ENFORCEMENT_GATES_v1.json', 'Metablooms_OS/0_kernel/registry/security/SECURITY_PROMPT_INJECTION_FIXTURE_SET_v1.json', 'Metablooms_OS/runtime/receipts/security/SECURITY_ARTIFACT_THREAT_MODEL_STAGE3_RECEIPT_LATEST.json', 'Metablooms_OS/runtime/handoffs/security/SECURITY_ARTIFACT_THREAT_MODEL_STAGE3_HANDOFF_LATEST.json', 'Metablooms_OS/0_kernel/lib/filesystem_safety_v1.py', 'Metablooms_OS/0_kernel/lib/trace_diff_logger_v1.py', 'Metablooms_OS/0_kernel/registry/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_POLICY_v1.json', 'Metablooms_OS/0_kernel/validators/validate_filesystem_handling_safety_stage1_v1.py', 'Metablooms_OS/0_kernel/scripts/education_validity_gate_v2.py', 'Metablooms_OS/0_kernel/security/education_promotion_gate_v1.py', 'Metablooms_OS/0_kernel/validators/validate_education_validity_stage2_v1.py', 'Metablooms_OS/0_kernel/registry/education_validity/MB_EDUCATION_VALIDITY_PROMOTION_GATE_SPEC_v1.json', 'Metablooms_OS/0_kernel/registry/education_validity/MB_EDUCATION_VALIDITY_GATE_SPEC_v2.json', 'Metablooms_OS/runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_FIXTURES_v1.json', 'Metablooms_OS/runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_SCORECARD_LATEST.json', 'Metablooms_OS/runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_PROMOTION_REPORT_LATEST.json', 'Metablooms_OS/runtime/receipts/education_validity/EDUCATION_VALIDITY_STAGE2_RECEIPT_LATEST.json', 'Metablooms_OS/runtime/handoffs/education_validity/EDUCATION_VALIDITY_STAGE2_HANDOFF_LATEST.json', 'Metablooms_OS/docs/education_validity/EDUCATION_VALIDITY_STAGE2_HARDWIRED_PROMOTION_GATE.md']
def unsafe(n): return n.startswith('/') or '/../' in ('/'+n) or n.endswith('/..') or '\x00' in n or re.match(r'^[A-Za-z]:',n) is not None
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--archive',required=True); ap.add_argument('--json',action='store_true'); ap.add_argument('--deep-test',action='store_true'); args=ap.parse_args(); issues=[]; info={'archive':args.archive}
 try:
  with zipfile.ZipFile(args.archive) as z:
   names=z.namelist(); nset=set(names); c=collections.Counter(names); info['entries']=len(names); d=[n for n,x in c.items() if x>1]
   if d: issues.append({'reason':'duplicate_entries','count':len(d)})
   u=[n for n in names if unsafe(n)]
   if u: issues.append({'reason':'unsafe_members','sample':u[:10]})
   m=[p for p in REQUIRED if p not in nset]
   if m: issues.append({'reason':'required_members_missing','count':len(m),'sample':m[:20]})
   rep='Metablooms_OS/runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_PROMOTION_REPORT_LATEST.json'
   if rep not in nset: issues.append({'reason':'education_promotion_report_missing'})
   else:
    data=json.loads(z.read(rep).decode()); info['education_accuracy']=data.get('accuracy'); info['education_false_pass_count']=data.get('false_pass_count'); info['education_promotion_decision']=data.get('promotion_decision')
    if data.get('promotion_decision')!='PROMOTE' or data.get('false_pass_count')!=0 or float(data.get('accuracy',0))<0.95: issues.append({'reason':'education_promotion_report_not_passing'})
   if args.deep_test:
    bad=z.testzip(); info['zipfile_testzip_bad_member']=bad
    if bad: issues.append({'reason':'bad_crc','member':bad})
 except Exception as e: issues.append({'reason':'zip_exception','error':str(e)})
 out={'schema_version':'EXPORT_PROMOTION_GATE_v4_EDUCATION_HARDWIRED','verdict':'EXPORT_PROMOTION_PASS' if not issues else 'EXPORT_PROMOTION_FAIL','promotion_decision':'PROMOTE' if not issues else 'BLOCK','issues':issues,'info':info}; print(json.dumps(out,indent=2,sort_keys=True) if args.json else out['verdict']); return 0 if not issues else 20
if __name__=='__main__': raise SystemExit(main())
