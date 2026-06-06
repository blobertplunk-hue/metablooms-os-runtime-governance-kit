#!/usr/bin/env python3
import json, sys, tempfile
from pathlib import Path
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/mnt/data/Metablooms_OS')

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
GATE=ROOT/'runtime/governance/durable_checkpoint_replay_gate_v1.py'
thread='stage6p.demo'; ck='ckpt_interrupt'
cmd=[sys.executable,'-S',str(GATE),'write','--root',str(ROOT),'--stage-id','STAGE6P_DURABLE_CHECKPOINT_REPLAY_MINIMUM','--thread-id',thread,'--checkpoint-id',ck,'--status','INTERRUPTED','--state-json','{"step":"before_handoff","completed":["boot","see","ce"]}','--interrupt-json','{"reason":"bounded_stage_pause","resume_options":["approve","reject"]}','--next','await_human_or_next_turn']
write=bounded_subprocess.run(cmd,capture_output=True,text=True)
allow=ROOT/'tests/fixtures/state_checkpoint/stage6p_resume_allow_v1.json'
resume=bounded_subprocess.run([sys.executable,'-S',str(GATE),'resume','--root',str(ROOT),'--resume-packet',str(allow)],capture_output=True,text=True)
deny=ROOT/'tests/fixtures/state_checkpoint/stage6p_resume_deny_payload_v1.json'
deny_run=bounded_subprocess.run([sys.executable,'-S',str(GATE),'resume','--root',str(ROOT),'--resume-packet',str(deny)],capture_output=True,text=True)
result={'schema':'Stage6PDurableCheckpointSmokeResult_v1','write_returncode':write.returncode,'write_stdout':json.loads(write.stdout) if write.stdout.strip().startswith('{') else write.stdout,'resume_returncode':resume.returncode,'resume_stdout':json.loads(resume.stdout) if resume.stdout.strip().startswith('{') else resume.stdout,'deny_returncode':deny_run.returncode,'deny_stdout':json.loads(deny_run.stdout) if deny_run.stdout.strip().startswith('{') else deny_run.stdout}
result['verdict']='PASS' if write.returncode==0 and resume.returncode==0 and deny_run.returncode!=0 else 'FAIL'
print(json.dumps(result, indent=2, sort_keys=True))
sys.exit(0 if result['verdict']=='PASS' else 1)
