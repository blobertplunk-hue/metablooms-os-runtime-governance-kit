#!/usr/bin/env python3
from pathlib import Path
import importlib.util, sys
ROOT=Path('/mnt/data/Metablooms_OS')
mod_path=ROOT/'0_kernel/evals/real_task_eval_harness/real_task_corpus_runner_v2.py'
spec=importlib.util.spec_from_file_location('runner', mod_path)
runner=importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
res=runner.run(ROOT)
assert res['verdict']=='PASS', res
assert res['total']>=12, res
assert set(['educational_html','blooket_csv','lesson_plan','research_see','artifact_export','repair_debugging']).issubset(set(res['domains'])), res
print('PASS real task corpus runner v2')
