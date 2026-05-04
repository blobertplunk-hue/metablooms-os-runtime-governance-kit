
#!/usr/bin/env python3
"""SEE_v2 — Structured Evidence Establishment Engine.

Standalone runtime for turning a task into a structured evidence artifact.
This file is intentionally self-contained and requires no external packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class EvidenceItem:
    claim: str
    type: str
    source: str
    verification_method: str
    confidence: float
    status: str


@dataclass
class ToolStep:
    step: int
    goal: str
    tool: str
    reason: str
    expected_output: str


@dataclass
class RiskItem:
    risk: str
    cause: str
    impact: str
    mitigation: str


def _stable_id(task: str, context: Dict[str, Any]) -> str:
    seed = json.dumps({"task": task, "context": context}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()]


def _extract_constraints(context: Dict[str, Any], task: str) -> List[str]:
    constraints = _normalize_list(context.get("constraints"))
    lowered = task.lower()
    heuristic_terms = [
        ("must", "Task includes a must-level requirement."),
        ("required", "Task includes a required element."),
        ("without", "Task forbids at least one action or omission."),
        ("only", "Task limits valid scope or method."),
    ]
    for token, message in heuristic_terms:
        if token in lowered and message not in constraints:
            constraints.append(message)
    return constraints


def _extract_success_criteria(context: Dict[str, Any], task: str) -> List[str]:
    success = _normalize_list(context.get("success_criteria"))
    if not success:
        success = [
            "Objective is explicitly satisfied.",
            "Output is structurally usable.",
            "No blocking unknowns remain unresolved."
        ]
    if "download" in task.lower():
        success.append("Output is exportable or downloadable.")
    return list(dict.fromkeys(success))


def _extract_given(task: str, context: Dict[str, Any]) -> List[str]:
    given: List[str] = [f"Task: {task}"]
    for key in ("existing_artifacts", "target", "context", "artifact_reference"):
        if key in context and context[key]:
            given.extend(_normalize_list(context[key]))
    return given


def _extract_assumptions(task: str, context: Dict[str, Any]) -> List[str]:
    assumptions = _normalize_list(context.get("assumptions"))
    if not context.get("existing_artifacts"):
        assumptions.append("Relevant artifacts may need to be discovered or verified.")
    if not context.get("constraints"):
        assumptions.append("Constraints are incomplete unless explicitly supplied.")
    return list(dict.fromkeys(assumptions))


def _extract_unknowns(task: str, context: Dict[str, Any]) -> List[str]:
    unknowns = _normalize_list(context.get("unknowns"))
    if not context.get("existing_artifacts"):
        unknowns.append("Whether required artifacts exist.")
    if re.search(r"\b(latest|best|correct|complete|full)\b", task.lower()):
        unknowns.append("Whether completeness criteria are fully specified.")
    return list(dict.fromkeys(unknowns))


def _build_evidence(task: str, context: Dict[str, Any], constraints: List[str], success: List[str], unknowns: List[str]) -> List[Dict[str, Any]]:
    evidence: List[EvidenceItem] = []

    evidence.append(EvidenceItem(
        claim=task,
        type="requirement",
        source="user_input",
        verification_method="explicit_input",
        confidence=0.98,
        status="supported",
    ))

    for c in constraints:
        evidence.append(EvidenceItem(
            claim=c,
            type="requirement",
            source="derived" if c not in _normalize_list(context.get("constraints")) else "user_input",
            verification_method="logical_check",
            confidence=0.8,
            status="supported",
        ))

    for s in success:
        evidence.append(EvidenceItem(
            claim=s,
            type="fact",
            source="derived",
            verification_method="logical_check",
            confidence=0.7,
            status="supported",
        ))

    for u in unknowns:
        evidence.append(EvidenceItem(
            claim=u,
            type="assumption",
            source="derived",
            verification_method="artifact_check",
            confidence=0.45,
            status="unresolved",
        ))

    return [asdict(e) for e in evidence]


def _tool_plan(task: str, context: Dict[str, Any], unknowns: List[str]) -> List[Dict[str, Any]]:
    steps: List[ToolStep] = []
    lowered = task.lower()

    steps.append(ToolStep(
        step=1,
        goal="Normalize objective and lock constraints.",
        tool="SEE_v2",
        reason="All later stages depend on explicit scope.",
        expected_output="Structured objective, constraints, and success criteria.",
    ))

    if unknowns:
        steps.append(ToolStep(
            step=2,
            goal="Resolve unknown artifacts or missing inputs.",
            tool="artifact_audit" if context.get("existing_artifacts") else "preflight_probe",
            reason="Execution should not proceed with unresolved blockers.",
            expected_output="Verified artifacts or explicit NO_GO blockers.",
        ))

    if any(token in lowered for token in ("export", "bundle", "file", "zip")):
        steps.append(ToolStep(
            step=3,
            goal="Validate artifact path, structure, and completeness before shipping.",
            tool="artifact_auditor",
            reason="File-related tasks require filesystem truth checks.",
            expected_output="Artifact audit report.",
        ))

    steps.append(ToolStep(
        step=len(steps) + 1,
        goal="Validate stage outputs against contracts before execution completes.",
        tool="verification_critic",
        reason="Fail-closed validation prevents premature success claims.",
        expected_output="Validation report with GO or NO_GO.",
    ))

    return [asdict(s) for s in steps]


def _risk_model(task: str, context: Dict[str, Any], unknowns: List[str]) -> List[Dict[str, Any]]:
    risks: List[RiskItem] = []

    if unknowns:
        risks.append(RiskItem(
            risk="Execution based on unresolved unknowns.",
            cause="Insufficient verified context.",
            impact="high",
            mitigation="Resolve unknowns before execution or emit NO_GO.",
        ))

    if any(token in task.lower() for token in ("file", "bundle", "export", "download")):
        risks.append(RiskItem(
            risk="Artifact claim without filesystem verification.",
            cause="Assuming outputs exist or are complete.",
            impact="high",
            mitigation="Run artifact audit before any ship/export claim.",
        ))

    risks.append(RiskItem(
        risk="Overconfident plan with weak validation.",
        cause="Missing explicit pass/fail checks.",
        impact="medium",
        mitigation="Attach validation plan and block completion on failed checks.",
    ))

    return [asdict(r) for r in risks]


def _simulation(tool_plan: List[Dict[str, Any]], unknowns: List[str]) -> Dict[str, List[str]]:
    expected_flow = [f"Step {s['step']}: {s['goal']}" for s in tool_plan]
    failure_points = []
    if unknowns:
        failure_points.append("Unknown artifacts or conditions may block execution readiness.")
    failure_points.append("Validation may fail if artifacts do not match declared contracts.")

    fallbacks = [
        "Halt with NO_GO if a required artifact cannot be verified.",
        "Reduce scope and re-run SEE with narrower constraints.",
    ]

    return {
        "expected_flow": expected_flow,
        "failure_points": failure_points,
        "fallbacks": fallbacks,
    }


def _validation_plan(task: str, unknowns: List[str]) -> List[Dict[str, str]]:
    plan = [
        {
            "check": "Objective is explicit and singular.",
            "method": "logical_validation",
            "pass_condition": "A single normalized objective exists."
        },
        {
            "check": "Evidence items are present for key claims.",
            "method": "schema_validation",
            "pass_condition": "Evidence array is non-empty and structured."
        },
    ]
    if any(token in task.lower() for token in ("file", "bundle", "export", "download")):
        plan.append({
            "check": "Artifacts are verified before shipping claims.",
            "method": "artifact_audit",
            "pass_condition": "Referenced artifact exists and passes completeness checks."
        })
    if unknowns:
        plan.append({
            "check": "Critical unknowns are resolved or explicitly block execution.",
            "method": "logical_validation",
            "pass_condition": "No unresolved critical blockers remain."
        })
    return plan


def _execution_readiness(unknowns: List[str], risks: List[Dict[str, Any]]) -> Dict[str, Any]:
    blockers = list(dict.fromkeys(unknowns))
    status = "NO_GO" if blockers else "GO"
    return {
        "status": status,
        "blocking_issues": blockers,
    }


def _confidence_score(evidence: List[Dict[str, Any]], readiness: Dict[str, Any]) -> float:
    if not evidence:
        return 0.0
    base = sum(item["confidence"] for item in evidence) / len(evidence)
    if readiness["status"] == "NO_GO":
        base *= 0.6
    return round(min(max(base, 0.0), 1.0), 3)


def run_see_v2(task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not task or not str(task).strip():
        raise ValueError("task is required")

    context = context or {}
    task = str(task).strip()

    constraints = _extract_constraints(context, task)
    success = _extract_success_criteria(context, task)
    given = _extract_given(task, context)
    assumptions = _extract_assumptions(task, context)
    unknowns = _extract_unknowns(task, context)

    evidence = _build_evidence(task, context, constraints, success, unknowns)
    tool_plan = _tool_plan(task, context, unknowns)
    risk_model = _risk_model(task, context, unknowns)
    simulation = _simulation(tool_plan, unknowns)
    validation_plan = _validation_plan(task, unknowns)
    execution_readiness = _execution_readiness(unknowns, risk_model)
    confidence_score = _confidence_score(evidence, execution_readiness)

    result = {
        "see_id": _stable_id(task, context),
        "version": "2.0",
        "objective": task,
        "context": {
            "given": given,
            "assumptions": assumptions,
            "unknowns": unknowns,
        },
        "constraints": constraints,
        "success_criteria": success,
        "evidence": evidence,
        "tool_plan": tool_plan,
        "risk_model": risk_model,
        "simulation": simulation,
        "validation_plan": validation_plan,
        "execution_readiness": execution_readiness,
        "confidence_score": confidence_score,
    }
    return result


def _cli() -> int:
    parser = argparse.ArgumentParser(description="SEE_v2 standalone engine")
    parser.add_argument("--task", required=True, help="Task to analyze")
    parser.add_argument("--context-json", default=None, help="Optional JSON string for context")
    parser.add_argument("--out", default=None, help="Optional path to save JSON output")
    args = parser.parse_args()

    context: Dict[str, Any] = {}
    if args.context_json:
        context = json.loads(args.context_json)

    result = run_see_v2(args.task, context)

    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(rendered)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
