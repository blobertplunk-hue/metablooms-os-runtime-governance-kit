#!/usr/bin/env python3
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "runtime" / "governance" / "cdr_adaptability_interface_contract_gate_v1.py"
spec = importlib.util.spec_from_file_location("gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

def test_valid_allows():
    packet = gate.load(ROOT / "tests" / "fixtures" / "cdr" / "valid_cdr_adaptability_interface_contract_packet_v1.json")
    result = gate.evaluate(packet)
    assert result["verdict"] == "ALLOW", result

def test_missing_compatibility_denies():
    packet = gate.load(ROOT / "tests" / "fixtures" / "cdr" / "invalid_cdr_adaptability_missing_compatibility_packet_v1.json")
    result = gate.evaluate(packet)
    assert result["verdict"] == "DENY", result
    assert any("compatibility" in reason for reason in result["reasons"]), result

if __name__ == "__main__":
    test_valid_allows(); test_missing_compatibility_denies(); print("PASS")
