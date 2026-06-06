#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
def find_root():
 p=Path(__file__).resolve()
 for q in [p.parent,*p.parents]:
  if (q/'boot_manifest_v1.json').exists() and (q/'0_kernel').exists(): return q
 return Path.cwd()
def decide(f):
 b=[]; w=[]
 if not f.get('teks_codes'): b.append('missing_teks')
 if not f.get('official_source_refs'): b.append('missing_official_source_refs')
 if not f.get('answer_key') or not f.get('scoring_rule'): b.append('missing_answer_or_scoring_rule')
 if f.get('student_visible_feedback') is False: b.append('student_feedback_not_visible')
 if f.get('eb_support')=='reveals_answer': b.append('eb_support_reveals_answer')
 if f.get('deployment')=='blocked_network_dependency': b.append('blocked_external_dependency')
 if f.get('contains_unvetted_external_script'): b.append('unvetted_external_script')
 if f.get('assessment_fidelity') not in ('staar_like','evidence_based_rla','simulation_with_reasoning'): w.append('weak_assessment_fidelity')
 if f.get('cognitive_demand') in ('copy_only','recall_only'): w.append('cognitive_demand_too_low')
 if f.get('misconception_model') is not True: w.append('misconception_model_missing')
 if f.get('distractor_parity') is False: w.append('distractor_parity_weak')
 if f.get('tts_plan')=='needs_repair': w.append('tts_needs_control_filtering')
 if len(f.get('udl_options') or [])<2: w.append('udl_options_incomplete')
 if len(f.get('accessibility') or [])<2: w.append('accessibility_incomplete')
 if not f.get('eb_support') or f.get('eb_support')=='none': w.append('eb_support_missing')
 if f.get('telemetry') is not True: w.append('telemetry_missing')
 return ('BLOCK',b+w) if b else (('WARN',w) if w else ('PASS',[]))
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); ap.add_argument('--promotion-gate',action='store_true'); args=ap.parse_args(); root=find_root()
 fixtures=json.loads((root/'runtime/evals/education_validity/EDUCATION_VALIDITY_STAGE2_FIXTURES_v1.json').read_text())['fixtures']; results=[]
 for item in fixtures:
  p,r=decide(item['features']); results.append({'fixture_id':item['fixture_id'],'expected':item['expected_decision'],'predicted':p,'reasons':r,'match':p==item['expected_decision']})
 labels=sorted({r['expected'] for r in results}|{r['predicted'] for r in results}); fp=[r for r in results if r['predicted']=='PASS' and r['expected']!='PASS']; acc=round(sum(r['match'] for r in results)/len(results),4); promote=(not fp and acc>=0.95 and {'PASS','WARN','BLOCK'}.issubset(set(labels)))
 out={'schema_version':'EDUCATION_VALIDITY_GATE_v2','verdict':'EDUCATION_VALIDITY_PROMOTION_PASS' if promote else 'EDUCATION_VALIDITY_PROMOTION_FAIL','promotion_decision':'PROMOTE' if promote else 'BLOCK','fixture_count':len(results),'accuracy':acc,'false_pass_count':len(fp),'decisions_covered':labels,'results':results}
 outdir=root/'runtime/evals/education_validity'; outdir.mkdir(parents=True,exist_ok=True); _mb_write_json_file(outdir / 'EDUCATION_VALIDITY_STAGE2_PROMOTION_REPORT_LATEST.json', out, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_education_validity_gate_v2_py_L36', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000); print(json.dumps(out,indent=2,sort_keys=True) if args.json else out['verdict']); return 0 if promote else 20
if __name__=='__main__': raise SystemExit(main())
