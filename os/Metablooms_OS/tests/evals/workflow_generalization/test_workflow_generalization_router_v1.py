#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ROUTER = ROOT / "0_kernel/routers/workflow_generalization_router_v1.py"
FIX = Path(__file__).parent / "fixtures"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/workflow_generalization_eval_report.json")

def run_fixture(path: Path):
    fixture = json.loads(path.read_text(encoding="utf-8"))
    candidate_file = None
    args = [sys.executable, str(ROUTER), "--task", fixture["task"]]
    if "candidates" in fixture:
        candidate_file = path.with_suffix(".candidates.tmp.json")
        candidate_file.write_text(json.dumps({"candidates": fixture["candidates"]}), encoding="utf-8")
        args += ["--candidate-json", str(candidate_file)]
    completed = subprocess.run(args, text=True, capture_output=True, timeout=20)
    if candidate_file and candidate_file.exists():
        candidate_file.unlink()
    if completed.returncode != 0:
        return {"fixture": path.name, "pass": False, "stderr": completed.stderr, "stdout": completed.stdout}
    result = json.loads(completed.stdout)
    failures = []
    for module in fixture.get("expect_include", []):
        if module not in result.get("auto_include", []):
            failures.append(f"missing include {module}")
    for module in fixture.get("expect_absent", []):
        if module in result.get("auto_include", []):
            failures.append(f"unexpected include {module}")
    adopted = {item["lesson_id"] for item in result.get("candidate_adoptions", [])}
    rejected = {item["lesson_id"] for item in result.get("candidate_rejections", [])}
    deferred = {item["lesson_id"] for item in result.get("candidate_deferrals", [])}
    for lesson_id in fixture.get("expect_adopt", []):
        if lesson_id not in adopted:
            failures.append(f"expected adopt {lesson_id}")
    for lesson_id in fixture.get("expect_reject", []):
        if lesson_id not in rejected:
            failures.append(f"expected reject {lesson_id}")
    for lesson_id in fixture.get("expect_defer", []):
        if lesson_id not in deferred:
            failures.append(f"expected defer {lesson_id}")
    return {"fixture": path.name, "pass": not failures, "failures": failures, "result": result}

report = {"harness": "test_workflow_generalization_router_v1", "results": [run_fixture(path) for path in sorted(FIX.glob("*.json"))]}
report["overall"] = "PASS" if all(item["pass"] for item in report["results"]) else "FAIL"
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
sys.exit(0 if report["overall"] == "PASS" else 1)
