#!/usr/bin/env python3
import importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
mod_path=ROOT/'runtime/governance/cdr_lint_security_scanner_gate_v1.py'
spec=importlib.util.spec_from_file_location('gate', mod_path)
gate=importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
valid=json.loads((ROOT/'tests/fixtures/cdr/valid_cdr_lint_security_scanner_packet_v1.json').read_text())
invalid=json.loads((ROOT/'tests/fixtures/cdr/invalid_cdr_lint_security_scanner_dynamic_exec_v1.json').read_text())
vr=gate.evaluate(valid); ir=gate.evaluate(invalid)
assert vr['decision']=='ALLOW', vr
assert ir['decision']=='DENY', ir
assert any(r.startswith('zero_tolerance_finding:dynamic_exec') for r in ir['reasons']), ir
print(json.dumps({'verdict':'PASS','valid':vr,'invalid':ir}, indent=2, sort_keys=True))
