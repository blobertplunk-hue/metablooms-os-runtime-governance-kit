#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TOOL_PATH = ROOT / "0_kernel/tools/mpp_v3/see_packet_adapter_recursive_gate_v1.py"
FIXTURES = ROOT / "0_kernel/tests/mpp_v3/fixtures"

spec = importlib.util.spec_from_file_location("see_packet_adapter_recursive_gate_v1", TOOL_PATH)
assert spec is not None and spec.loader is not None
adapter = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = adapter
spec.loader.exec_module(adapter)


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def main() -> int:
    research = load("research_planner_valid_for_see_adapter.json")
    valid_evidence = load("web_evidence_valid_for_see_adapter.json")
    see_packet = adapter.build_see_packet(research, valid_evidence)
    gate = adapter.recursive_search_gate(research, see_packet, ROOT)
    assert gate["verdict"] == "PASS", gate
    assert gate["existing_see_validator_verdict"] == "PASS", gate
    assert gate["observed_source_count"] >= 3, gate
    assert gate["observed_domain_diversity"] >= 2, gate
    assert gate["next_stage"] == "NORMALIZE_EVIDENCE", gate

    invalid_evidence = load("web_evidence_invalid_missing_web_run.json")
    bad_packet = adapter.build_see_packet(research, invalid_evidence)
    bad_gate = adapter.recursive_search_gate(research, bad_packet, ROOT)
    assert bad_gate["verdict"] == "FAIL", bad_gate
    codes = {i["code"] for i in bad_gate["issues"]}
    assert "WEBRUN_REQUIRED" in codes or "OS_SEE_VALIDATOR" in codes, bad_gate
    assert "MIN_SOURCE_COUNT" in codes, bad_gate

    out_dir = ROOT / "0_kernel/registry/mpp_v3/see_adapter_test_outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    adapter.write_json(see_packet, out_dir / "SEE_PACKET_ADAPTER_VALID_OUTPUT_v1.json")
    adapter.write_json(gate, out_dir / "SEE_RECURSIVE_GATE_VALID_REPORT_v1.json")
    adapter.write_json(bad_gate, out_dir / "SEE_RECURSIVE_GATE_INVALID_REPORT_v1.json")
    print(json.dumps({"status": "PASS", "valid_gate": gate["verdict"], "invalid_gate": bad_gate["verdict"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
