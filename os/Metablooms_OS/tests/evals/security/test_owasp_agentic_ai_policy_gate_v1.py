#!/usr/bin/env python3
import json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[3]

import importlib.util
_BOUNDED_COMPAT_SPEC = importlib.util.spec_from_file_location('bounded_subprocess_compat_v1', ROOT / '0_kernel/lib/execution/bounded_subprocess_compat_v1.py')
bounded_subprocess = importlib.util.module_from_spec(_BOUNDED_COMPAT_SPEC)
assert _BOUNDED_COMPAT_SPEC and _BOUNDED_COMPAT_SPEC.loader
_BOUNDED_COMPAT_SPEC.loader.exec_module(bounded_subprocess)
GATE=ROOT/'runtime/governance/owasp_agentic_ai_policy_gate_v1.py'
ALLOW=ROOT/'tests/fixtures/security/owasp_agentic_policy_allow_v1.json'
DENY=ROOT/'tests/fixtures/security/owasp_agentic_policy_deny_missing_controls_v1.json'
allow=bounded_subprocess.run([sys.executable, str(GATE), str(ALLOW)], text=True, capture_output=True)
deny=bounded_subprocess.run([sys.executable, str(GATE), str(DENY)], text=True, capture_output=True)
assert allow.returncode == 0, allow.stdout + allow.stderr
assert json.loads(allow.stdout)['decision'] == 'ALLOW'
assert deny.returncode == 1, deny.stdout + deny.stderr
obj=json.loads(deny.stdout)
assert obj['decision'] == 'DENY'
assert 'supply_chain_origin' in obj['controls_missing']
print(json.dumps({'schema':'Stage6OPolicyGateSmoke_v1','status':'PASS','allow_decision':'ALLOW','deny_decision':'DENY','deny_missing_count':len(obj['controls_missing'])}, indent=2))
