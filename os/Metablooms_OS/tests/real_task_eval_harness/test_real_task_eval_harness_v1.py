#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path
root=Path('/mnt/data/Metablooms_OS')
runner=root/'0_kernel/evals/real_task_eval_harness/real_task_eval_harness_runner_v1.py'
out=subprocess.check_output([sys.executable, str(runner), str(root)], text=True)
res=json.loads(out)
assert res['verdict']=='PASS', out
assert res['passed']==res['total']==6, out
print(out)
