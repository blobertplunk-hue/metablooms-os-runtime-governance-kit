#!/usr/bin/env python3
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path

import importlib.util as _mb_atomic_importlib_util
_ATOMIC_JSON_COMPAT_PATH = Path(__file__).resolve().parents[3] / '0_kernel/lib/io/atomic_json_compat_v1.py'
_ATOMIC_JSON_COMPAT_SPEC = _mb_atomic_importlib_util.spec_from_file_location('atomic_json_compat_v1_stage5', _ATOMIC_JSON_COMPAT_PATH)
_mb_atomic_json = _mb_atomic_importlib_util.module_from_spec(_ATOMIC_JSON_COMPAT_SPEC)
assert _ATOMIC_JSON_COMPAT_SPEC and _ATOMIC_JSON_COMPAT_SPEC.loader
_ATOMIC_JSON_COMPAT_SPEC.loader.exec_module(_mb_atomic_json)
ROOT=Path('/mnt/data/Metablooms_OS')

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
RES=ROOT/'runtime/governance/tool_universe_resolver_v1.py'
OUT=Path('/mnt/data/stage6h_tool_universe_fixture_outputs')
OUT.mkdir(exist_ok=True)
TASKS={
 'zip_export':'Create a full OS authority ZIP export with CRC proof and sidecar',
 'zip_crc_proof':'Run streamed CRC replay proof on a ZIP archive',
 'html_validation':'Validate an interactive HTML with TTS and accessibility DOM checks',
 'filesystem_repair':'Patch a runtime source file and write implementation reality receipt',
 'see_web_research':'Research current 2026 state of the art with citations and SEE evidence',
 'external_install_profile':'Install an external npm package profile for document extraction',
 'spreadsheet_generation':'Create a styled XLSX workbook artifact',
}
results=[]
for name, task in TASKS.items():
    out=OUT/f'{name}_candidate_set.json'
    p=bounded_subprocess.run([sys.executable,'-S',str(RES),'resolve','--task',task,'--stage-id','STAGE6H_FIXTURE','--out',str(out)],capture_output=True,text=True)
    data=json.loads(out.read_text()) if out.exists() else {}
    ok=bool(p.returncode==0 and data.get('sufficiency',{}).get('verdict')=='PASS' and data.get('candidates'))
    results.append({'fixture':name,'returncode':p.returncode,'ok':ok,'classified_job_type':data.get('classified_job_type'),'top_allowed_tool_id':data.get('top_allowed_tool_id'),'candidate_count':len(data.get('candidates',[])),'stderr':p.stderr[-300:]})
# validate why-not-better gate fail/pass on zip_export
cs=OUT/'zip_export_candidate_set.json'
cset=json.loads(cs.read_text())
top=cset['top_allowed_tool_id']
bad={'selected_tool_id':'python_zipfile_compatibility_fallback','candidates':[{'tool_id':'python_zipfile_compatibility_fallback','verdict':'SELECTED'}]}
badp=OUT/'bad_eval.json'; _mb_atomic_json.write_json_file(badp, bad, operation_id='stage6h_bad_eval_fixture', indent=None, sort_keys=False)
badres=OUT/'bad_eval_result.json'
p=bounded_subprocess.run([sys.executable,'-S',str(RES),'validate-evaluation','--candidate-set',str(cs),'--evaluation',str(badp),'--out',str(badres)],capture_output=True,text=True)
results.append({'fixture':'why_not_better_missing_justification_denied','returncode':p.returncode,'ok':p.returncode!=0 and json.loads(badres.read_text()).get('verdict')=='FAIL'})
good={'selected_tool_id':top,'candidates':[{'tool_id':c['tool_id'],'verdict':'SELECTED' if c['tool_id']==top else 'REJECTED','reason':'resolver-ranked candidate'} for c in cset['candidates'][:5]]}
goodp=OUT/'good_eval.json'; _mb_atomic_json.write_json_file(goodp, good, operation_id='stage6h_good_eval_fixture', indent=None, sort_keys=False)
goodres=OUT/'good_eval_result.json'
p=bounded_subprocess.run([sys.executable,'-S',str(RES),'validate-evaluation','--candidate-set',str(cs),'--evaluation',str(goodp),'--out',str(goodres)],capture_output=True,text=True)
results.append({'fixture':'resolver_candidate_coverage_pass','returncode':p.returncode,'ok':p.returncode==0 and json.loads(goodres.read_text()).get('verdict')=='PASS'})
summary={'schema':'STAGE6H_TOOL_UNIVERSE_FIXTURE_RESULTS_v1','results':results,'verdict':'PASS' if all(r['ok'] for r in results) else 'FAIL'}
print(json.dumps(summary,indent=2,sort_keys=True))
_mb_atomic_json.write_json_file(Path('/mnt/data/METABLOOMS_STAGE6H_TOOL_UNIVERSE_RESOLVER_FIXTURE_RESULTS_20260502T021800Z.json'), summary, operation_id='STAGE6H_TOOL_UNIVERSE_FIXTURE_RESULTS', indent=2, sort_keys=True)
sys.exit(0 if summary['verdict']=='PASS' else 1)
