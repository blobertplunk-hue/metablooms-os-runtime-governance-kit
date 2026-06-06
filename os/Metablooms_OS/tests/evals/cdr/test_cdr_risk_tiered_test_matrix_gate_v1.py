#!/usr/bin/env python3
import json, pathlib, importlib.util
ROOT=pathlib.Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('cdr_risk_tiered_test_matrix_gate_v1', ROOT/'runtime/governance/cdr_risk_tiered_test_matrix_gate_v1.py')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
valid=json.load(open(ROOT/'tests/fixtures/cdr/valid_cdr_risk_tiered_test_matrix_packet_v1.json'))
invalid=json.load(open(ROOT/'tests/fixtures/cdr/invalid_cdr_risk_tiered_test_matrix_undertiered_v1.json'))
a=m.evaluate(valid); b=m.evaluate(invalid)
assert a['verdict']=='ALLOW', a
assert b['verdict']=='DENY', b
print('test_cdr_risk_tiered_test_matrix_gate_v1.py: PASS')
