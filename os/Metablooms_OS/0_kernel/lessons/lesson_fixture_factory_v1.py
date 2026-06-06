#!/usr/bin/env python3
"""MetaBlooms lesson promotion fixture factory v1.
Generates regression fixtures from accepted lesson queue items and validates gate coverage.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

REQUIRED_LESSON_FIELDS = {
    "lesson_id", "problem_class", "evidence_paths", "adopt_decision",
    "acceptance_gate", "prevents_regression", "priority"
}

def load_queue(root: Path) -> dict:
    path = root / "0_kernel/lessons/LESSON_PROMOTION_QUEUE_v1.json"
    return json.loads(path.read_text(encoding="utf-8"))

def build_fixture(lesson: dict) -> dict:
    return {
        "schema_version": "v1",
        "fixture_type": "lesson_promotion_regression",
        "lesson_id": lesson["lesson_id"],
        "problem_class": lesson["problem_class"],
        "gate_under_test": lesson["acceptance_gate"],
        "must_block_if": [
            "evidence_paths_empty",
            "fixture_missing",
            "stage_exit_prompt_missing",
            "successful_stage_without_bootable_full_authority_when_possible"
        ],
        "must_require": {
            "artifact_evidence_paths": lesson["evidence_paths"],
            "prevention_claim": lesson["prevents_regression"]
        },
        "expected_decision": "pass_when_gate_artifacts_present_else_fail"
    }

def run(root: Path) -> dict:
    queue = load_queue(root)
    out_dir = root / "tests/fixtures/world_class_lessons"
    out_dir.mkdir(parents=True, exist_ok=True)
    fixtures=[]
    errors=[]
    for lesson in queue.get("lessons", []):
        missing=sorted(REQUIRED_LESSON_FIELDS - set(lesson))
        if missing:
            errors.append({"lesson_id": lesson.get("lesson_id"), "missing_fields": missing})
            continue
        if lesson.get("adopt_decision") != "accept":
            continue
        if not lesson.get("evidence_paths"):
            errors.append({"lesson_id": lesson.get("lesson_id"), "error": "empty evidence_paths"})
            continue
        fixture=build_fixture(lesson)
        path=out_dir / f"{lesson['lesson_id']}_fixture.json"
        path.write_text(json.dumps(fixture, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        lesson["fixture_path"] = str(path.relative_to(root))
        fixtures.append(str(path.relative_to(root)))
    qpath=root / "0_kernel/lessons/LESSON_PROMOTION_QUEUE_v1.json"
    qpath.write_text(json.dumps(queue, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    report={
        "verdict": "PASS" if not errors else "FAIL",
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "errors": errors
    }
    (root / "runtime/state/LESSON_FIXTURE_FACTORY_RESULT_v1.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return report

if __name__ == "__main__":
    root=Path(sys.argv[1]) if len(sys.argv)>1 else Path("/mnt/data/Metablooms_OS")
    result=run(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["verdict"] == "PASS" else 1)
