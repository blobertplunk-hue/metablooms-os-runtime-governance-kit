#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "0_kernel" / "tools" / "mpp_v3"))

from research_planner_packet_writer_v1 import (  # noqa: E402
    ResearchPlannerValidationError,
    build_packet,
    validate_file,
    validate_packet,
)

FIXTURES = ROOT / "0_kernel" / "tests" / "mpp_v3" / "fixtures" / "research_planner"


def main() -> int:
    results = []

    pass_fixture = FIXTURES / "pass_research_planner_packet_v1.json"
    report = validate_file(pass_fixture)
    results.append({"case": "pass_fixture", "status": "PASS", "packet_hash": report["packet_hash"]})

    fail_fixture = FIXTURES / "fail_research_planner_packet_missing_query_id_v1.json"
    try:
        validate_file(fail_fixture)
    except ResearchPlannerValidationError as exc:
        codes = [i.code for i in exc.issues]
        assert "REQUIRED" in codes, codes
        results.append({"case": "fail_fixture_missing_query_id", "status": "PASS", "codes": codes})
    else:
        raise AssertionError("fail fixture unexpectedly passed")

    generated = build_packet(
        request="Create a research planner packet smoke test",
        domain="MPP v3 research planner",
        operator_context="sandbox smoke test",
        stakes="medium",
        seed_queries=["JSON Schema validation smoke test"],
    )
    report2 = validate_packet(generated)
    assert generated["handoff"]["next_stage"] == "SEE"
    assert generated["quality_gates"]["mmd_required"] is True
    assert generated["research_trigger"]["must_use_web_run"] is True
    results.append({"case": "generated_packet", "status": "PASS", "packet_hash": report2["packet_hash"]})

    print(json.dumps({"status": "PASS", "results": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
