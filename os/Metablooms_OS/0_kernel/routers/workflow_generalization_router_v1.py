#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

HARD_FLAGS = {
    "pc_only_blocks_sandbox_primary",
    "evidence_tier_overclaim",
    "removes_existing_gate",
    "no_fixture_for_recurring_claim",
    "unsafe_or_policy_invalid",
}

TASK_RULES = [
    (re.compile(r"\b(html|visual|tracker|dashboard|landing page|student activity|teacher tool)\b", re.I), ["VISUAL_PRESENTATION_QUALITY_GATE", "BROWSER_RENDER_CAPABILITY_RESOLVER"]),
    (re.compile(r"\b(screenshot|render|browser|mobile smoke|google sites|weasyprint|chromium|playwright)\b", re.I), ["BROWSER_RENDER_CAPABILITY_RESOLVER"]),
    (re.compile(r"\b(repair|fix|failed|failure|blocked|stuck|regression|false positive)\b", re.I), ["WORKFLOW_GENERALIZATION_ENGINE"]),
    (re.compile(r"\b(old transcript|transcript|chat log|previous chat|conversation export)\b", re.I), ["TRANSCRIPT_LESSON_IMPORT_GATE", "WORKFLOW_GENERALIZATION_ENGINE"]),
]

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def score_total(score_map):
    if not isinstance(score_map, dict):
        return 0.0
    total = 0.0
    for value in score_map.values():
        try:
            total += float(value)
        except Exception:
            pass
    return total

def evaluate_candidate(candidate):
    comp = candidate.get("baseline_comparison", {})
    flags = set(comp.get("regression_flags", []) or [])
    current = score_total(comp.get("score_current", {}))
    proposed = score_total(comp.get("score_candidate", {}))
    missing_evidence = not candidate.get("evidence", {}).get("summary")
    if flags & HARD_FLAGS:
        return {"decision": "reject", "reason": "hard_regression_flags_present", "current_total": current, "candidate_total": proposed, "flags": sorted(flags)}
    if missing_evidence:
        return {"decision": "defer_for_more_evidence", "reason": "missing_evidence_summary", "current_total": current, "candidate_total": proposed, "flags": sorted(flags)}
    if proposed > current:
        return {"decision": "adopt", "reason": "candidate_scores_higher_than_current_and_no_hard_regression", "current_total": current, "candidate_total": proposed, "flags": sorted(flags)}
    return {"decision": "reject", "reason": "not_better_than_current", "current_total": current, "candidate_total": proposed, "flags": sorted(flags)}

def route_task(task_text, candidate_lessons=None):
    includes = []
    reasons = []
    for regex, modules in TASK_RULES:
        if regex.search(task_text or ""):
            for module in modules:
                if module not in includes:
                    includes.append(module)
            reasons.append({"match": regex.pattern, "include": modules})
    adopted, rejected, deferred, decisions = [], [], [], []
    for candidate in candidate_lessons or []:
        evaluation = evaluate_candidate(candidate)
        record = {"lesson_id": candidate.get("lesson_id", "UNKNOWN"), **evaluation}
        decisions.append((candidate, evaluation))
        if evaluation["decision"] == "adopt":
            adopted.append(record)
        elif evaluation["decision"] == "defer_for_more_evidence":
            deferred.append(record)
        else:
            rejected.append(record)
    for candidate, evaluation in decisions:
        if evaluation["decision"] == "adopt":
            for module in candidate.get("auto_include", []) or []:
                if module not in includes:
                    includes.append(module)
    return {
        "task_text": task_text,
        "auto_include": includes,
        "routing_reasons": reasons,
        "candidate_adoptions": adopted,
        "candidate_rejections": rejected,
        "candidate_deferrals": deferred,
        "honesty": "candidate transcript lessons only affect routing when better_than_current passes",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default="")
    parser.add_argument("--candidate-json")
    parser.add_argument("--out")
    args = parser.parse_args()
    candidates = []
    if args.candidate_json:
        data = load_json(Path(args.candidate_json))
        candidates = data if isinstance(data, list) else data.get("candidates", [data])
    result = route_task(args.task, candidates)
    output = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)

if __name__ == "__main__":
    main()
