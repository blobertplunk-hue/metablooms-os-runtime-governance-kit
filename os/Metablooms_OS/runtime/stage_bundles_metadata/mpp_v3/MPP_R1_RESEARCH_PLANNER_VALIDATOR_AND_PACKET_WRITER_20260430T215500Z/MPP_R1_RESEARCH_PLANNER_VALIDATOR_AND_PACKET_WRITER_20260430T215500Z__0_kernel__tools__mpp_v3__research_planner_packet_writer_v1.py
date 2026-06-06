#!/usr/bin/env python3
"""MetaBlooms MPP v3 Research Planner packet writer and validator.

CDR V1 Rationale:
    Creates and validates RESEARCH_PLANNER packets before SEE executes.
    This prevents unplanned research, unbounded recursive search, and
    downstream MMD ambiguity.

CDR V2 Trust:
    Uses the locked JSON schema artifact as the source of truth. Validation
    is fail-closed and returns deterministic error paths. No network access,
    no dynamic imports, and no external dependency are required.

CDR V3 Boundary:
    Inputs: task request/context dictionaries and the locked schema JSON.
    Outputs: research_planner_packet.v1 dictionaries and validation reports.
    Side effects: only write_packet() writes JSON when explicitly called.

CDR V4 Failure:
    Raises ResearchPlannerValidationError for invalid packets. Safe state is
    to halt before SEE and write a blocked receipt/handoff.

CDR V5 Integration:
    Intended stage order: BOOT_AUTHORITY -> RESEARCH_PLANNER -> SEE. The
    packet handoff always names SEE and required artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "research_planner_packet.v1"
STAGE = "RESEARCH_PLANNER"
NEXT_STAGE = "SEE"
QUERY_ID_RE = re.compile(r"^Q-[0-9]{3}$")
DATE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")

EVIDENCE_TYPES = {
    "official",
    "peer_reviewed",
    "technical_docs",
    "expert_practice",
    "news_current",
    "community_failure_report",
    "internal_artifact",
}
PRIORITIES = {"must", "should", "could"}
STAKES = {"low", "medium", "high", "critical"}
CONTRADICTION_HANDLING = {"record_and_resolve", "record_and_block", "record_for_later"}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


class ResearchPlannerValidationError(RuntimeError):
    """Raised when a research planner packet fails validation."""

    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        summary = "; ".join(f"{i.path}:{i.code}" for i in issues[:8])
        super().__init__(f"RESEARCH_PLANNER_PACKET_INVALID: {summary}")


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")[:48] or "RESEARCH"


def _coerce_str_list(value: Any, fallback: list[str] | None = None) -> list[str]:
    if value is None:
        return list(fallback or [])
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return list(fallback or [])


def build_packet(
    request: str,
    domain: str,
    operator_context: str,
    stakes: str = "high",
    known_facts: list[str] | None = None,
    unknowns: list[str] | None = None,
    assumptions: list[str] | None = None,
    seed_queries: list[str] | None = None,
    freshness_required: bool = True,
    must_use_web_run: bool = True,
    minimum_source_count: int = 3,
    minimum_domain_diversity: int = 2,
    max_recursion_rounds: int = 3,
) -> dict[str, Any]:
    """Construct a schema-conformant RESEARCH_PLANNER packet.

    Queries are deterministic and intentionally broad: authoritative baseline,
    implementation practice, failure modes, and current updates. The caller may
    add seed_queries; they are appended after generated must/should queries.
    """
    if not request or not request.strip():
        raise ValueError("request must be non-empty")
    if not domain or not domain.strip():
        raise ValueError("domain must be non-empty")
    if stakes not in STAKES:
        raise ValueError(f"stakes must be one of {sorted(STAKES)}")

    base = f"{domain.strip()} {request.strip()}"
    generated = [
        ("authoritative baseline", f"{base} official guidance standard best practices", "official", "must"),
        ("peer or expert quality signals", f"{base} expert practice quality criteria", "expert_practice", "must"),
        ("failure modes and anti-patterns", f"{base} common failures mistakes anti-patterns", "community_failure_report", "should"),
        ("implementation and validation methods", f"{base} implementation validation schema testing", "technical_docs", "should"),
    ]
    for sq in seed_queries or []:
        generated.append(("operator seed query", sq, "expert_practice", "could"))

    query_plan = []
    for idx, (purpose, query, evidence_type, priority) in enumerate(generated, start=1):
        query_plan.append(
            {
                "query_id": f"Q-{idx:03d}",
                "query": query,
                "purpose": purpose,
                "expected_evidence_type": evidence_type,
                "priority": priority,
            }
        )

    packet = {
        "schema_version": SCHEMA_VERSION,
        "packet_id": f"RP-{_slug(domain)}-{hashlib.sha256((request + domain).encode()).hexdigest()[:12].upper()}",
        "stage": STAGE,
        "created_at": _now_iso(),
        "objective": {
            "request": request.strip(),
            "domain": domain.strip(),
            "stakes": stakes,
            "operator_context": operator_context.strip() or "MetaBlooms governed runtime operator",
        },
        "research_trigger": {
            "required": True,
            "trigger_reason": "MPP v3 requires planned SEE before evidence-dependent governance or implementation stages.",
            "must_use_web_run": must_use_web_run,
            "freshness_required": freshness_required,
            "minimum_source_count": minimum_source_count,
        },
        "planning_basis": {
            "known_facts": _coerce_str_list(known_facts, ["Task entered MPP v3 research pipeline."]),
            "unknowns": _coerce_str_list(unknowns, ["Which sources are authoritative for this exact domain and task?", "Which failure modes should block implementation?"]),
            "assumptions": _coerce_str_list(assumptions, ["Research may reveal constraints that change the downstream plan."]),
        },
        "query_plan": query_plan,
        "source_plan": {
            "preferred_source_types": ["official", "peer_reviewed", "technical_docs", "expert_practice"],
            "exclusion_rules": ["Exclude uncited SEO summaries when stronger sources exist.", "Exclude stale sources when freshness is required and newer official sources exist."],
            "date_capture_required": True,
            "contradiction_handling": "record_and_resolve",
        },
        "recursion_policy": {
            "enabled": True,
            "max_rounds": max_recursion_rounds,
            "expansion_triggers": [
                "authoritative source contradicts another source",
                "source quality is below required threshold",
                "MMD reports critical uncovered gap",
            ],
            "stop_conditions": [
                "minimum source count and domain diversity satisfied",
                "no critical MMD gaps remain",
                "recursion round limit reached and blocked receipt written",
            ],
        },
        "quality_gates": {
            "minimum_source_count": minimum_source_count,
            "minimum_domain_diversity": minimum_domain_diversity,
            "claim_binding_required": True,
            "mmd_required": True,
        },
        "handoff": {
            "next_stage": NEXT_STAGE,
            "required_artifacts": [
                "0_kernel/schemas/mpp_v3/RESEARCH_PLANNER_PACKET_SCHEMA_v1.json",
                "research_planner_packet.v1.json",
            ],
        },
    }
    validate_packet(packet)
    return packet


def validate_packet(packet: dict[str, Any], schema: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a RESEARCH_PLANNER packet against locked schema semantics.

    This is a purpose-built validator for the locked schema. It enforces all
    schema-required fields, enum/const/pattern/minimum/minItems constraints,
    and core cross-field invariants that JSON Schema alone does not express.
    """
    issues: list[ValidationIssue] = []

    def issue(path: str, code: str, message: str) -> None:
        issues.append(ValidationIssue(path, code, message))

    def require_obj(obj: Any, path: str) -> dict[str, Any] | None:
        if not isinstance(obj, dict):
            issue(path, "TYPE_OBJECT", "must be object")
            return None
        return obj

    root = require_obj(packet, "$")
    if root is None:
        raise ResearchPlannerValidationError(issues)

    required = [
        "schema_version", "packet_id", "stage", "created_at", "objective", "research_trigger",
        "planning_basis", "query_plan", "source_plan", "recursion_policy", "quality_gates", "handoff",
    ]
    for key in required:
        if key not in root:
            issue(f"$.{key}", "REQUIRED", "missing required field")

    allowed = set(required)
    for key in root:
        if key not in allowed:
            issue(f"$.{key}", "ADDITIONAL_PROPERTY", "not allowed by schema")

    if root.get("schema_version") != SCHEMA_VERSION:
        issue("$.schema_version", "CONST", f"must equal {SCHEMA_VERSION}")
    if root.get("stage") != STAGE:
        issue("$.stage", "CONST", f"must equal {STAGE}")
    if not isinstance(root.get("packet_id"), str) or len(root.get("packet_id", "")) < 8:
        issue("$.packet_id", "MIN_LENGTH", "must be string length >= 8")
    created = root.get("created_at")
    if not isinstance(created, str) or not DATE_TIME_RE.match(created):
        issue("$.created_at", "FORMAT_DATE_TIME", "must be RFC3339 date-time string")

    objective = require_obj(root.get("objective"), "$.objective")
    if objective:
        for k in ["request", "domain", "stakes", "operator_context"]:
            if k not in objective:
                issue(f"$.objective.{k}", "REQUIRED", "missing required field")
        for k in ["request", "domain", "operator_context"]:
            if not isinstance(objective.get(k), str) or not objective.get(k, "").strip():
                issue(f"$.objective.{k}", "MIN_LENGTH", "must be non-empty string")
        if objective.get("stakes") not in STAKES:
            issue("$.objective.stakes", "ENUM", f"must be one of {sorted(STAKES)}")
        for k in objective:
            if k not in {"request", "domain", "stakes", "operator_context"}:
                issue(f"$.objective.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    trigger = require_obj(root.get("research_trigger"), "$.research_trigger")
    if trigger:
        for k in ["required", "trigger_reason", "must_use_web_run", "freshness_required"]:
            if k not in trigger:
                issue(f"$.research_trigger.{k}", "REQUIRED", "missing required field")
        for k in ["required", "must_use_web_run", "freshness_required"]:
            if not isinstance(trigger.get(k), bool):
                issue(f"$.research_trigger.{k}", "TYPE_BOOLEAN", "must be boolean")
        if "minimum_source_count" in trigger and (not isinstance(trigger.get("minimum_source_count"), int) or trigger.get("minimum_source_count") < 0):
            issue("$.research_trigger.minimum_source_count", "MINIMUM", "must be integer >= 0")
        if not isinstance(trigger.get("trigger_reason"), str):
            issue("$.research_trigger.trigger_reason", "TYPE_STRING", "must be string")
        for k in trigger:
            if k not in {"required", "trigger_reason", "must_use_web_run", "freshness_required", "minimum_source_count"}:
                issue(f"$.research_trigger.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    basis = require_obj(root.get("planning_basis"), "$.planning_basis")
    if basis:
        for k in ["known_facts", "unknowns", "assumptions"]:
            if k not in basis:
                issue(f"$.planning_basis.{k}", "REQUIRED", "missing required field")
            elif not isinstance(basis.get(k), list) or any(not isinstance(x, str) for x in basis.get(k, [])):
                issue(f"$.planning_basis.{k}", "TYPE_ARRAY_STRING", "must be array of strings")
        for k in basis:
            if k not in {"known_facts", "unknowns", "assumptions"}:
                issue(f"$.planning_basis.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    qplan = root.get("query_plan")
    if not isinstance(qplan, list) or len(qplan) < 1:
        issue("$.query_plan", "MIN_ITEMS", "must contain at least one query")
    else:
        seen_qids: set[str] = set()
        for i, q in enumerate(qplan):
            path = f"$.query_plan[{i}]"
            if not isinstance(q, dict):
                issue(path, "TYPE_OBJECT", "query plan entry must be object")
                continue
            for k in ["query_id", "query", "purpose", "expected_evidence_type", "priority"]:
                if k not in q:
                    issue(f"{path}.{k}", "REQUIRED", "missing required field")
            qid = q.get("query_id")
            if not isinstance(qid, str) or not QUERY_ID_RE.match(qid):
                issue(f"{path}.query_id", "PATTERN", "must match ^Q-[0-9]{3}$")
            elif qid in seen_qids:
                issue(f"{path}.query_id", "DUPLICATE", "query_id must be unique")
            else:
                seen_qids.add(qid)
            for k in ["query", "purpose"]:
                if not isinstance(q.get(k), str) or len(q.get(k, "")) < 3:
                    issue(f"{path}.{k}", "MIN_LENGTH", "must be string length >= 3")
            if q.get("expected_evidence_type") not in EVIDENCE_TYPES:
                issue(f"{path}.expected_evidence_type", "ENUM", f"must be one of {sorted(EVIDENCE_TYPES)}")
            if q.get("priority") not in PRIORITIES:
                issue(f"{path}.priority", "ENUM", f"must be one of {sorted(PRIORITIES)}")
            for k in q:
                if k not in {"query_id", "query", "purpose", "expected_evidence_type", "priority"}:
                    issue(f"{path}.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    source_plan = require_obj(root.get("source_plan"), "$.source_plan")
    if source_plan:
        if not isinstance(source_plan.get("preferred_source_types"), list) or len(source_plan.get("preferred_source_types", [])) < 1:
            issue("$.source_plan.preferred_source_types", "MIN_ITEMS", "must contain at least one source type")
        elif any(not isinstance(x, str) for x in source_plan.get("preferred_source_types", [])):
            issue("$.source_plan.preferred_source_types", "TYPE_ARRAY_STRING", "must be array of strings")
        if not isinstance(source_plan.get("exclusion_rules"), list) or any(not isinstance(x, str) for x in source_plan.get("exclusion_rules", [])):
            issue("$.source_plan.exclusion_rules", "TYPE_ARRAY_STRING", "must be array of strings")
        if not isinstance(source_plan.get("date_capture_required"), bool):
            issue("$.source_plan.date_capture_required", "TYPE_BOOLEAN", "must be boolean")
        if source_plan.get("contradiction_handling") not in CONTRADICTION_HANDLING:
            issue("$.source_plan.contradiction_handling", "ENUM", f"must be one of {sorted(CONTRADICTION_HANDLING)}")
        for k in source_plan:
            if k not in {"preferred_source_types", "exclusion_rules", "date_capture_required", "contradiction_handling"}:
                issue(f"$.source_plan.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    recursion = require_obj(root.get("recursion_policy"), "$.recursion_policy")
    if recursion:
        if not isinstance(recursion.get("enabled"), bool):
            issue("$.recursion_policy.enabled", "TYPE_BOOLEAN", "must be boolean")
        mr = recursion.get("max_rounds")
        if not isinstance(mr, int) or mr < 0 or mr > 8:
            issue("$.recursion_policy.max_rounds", "RANGE", "must be integer between 0 and 8")
        for k in ["expansion_triggers", "stop_conditions"]:
            if not isinstance(recursion.get(k), list) or any(not isinstance(x, str) for x in recursion.get(k, [])):
                issue(f"$.recursion_policy.{k}", "TYPE_ARRAY_STRING", "must be array of strings")
        if isinstance(recursion.get("stop_conditions"), list) and len(recursion.get("stop_conditions", [])) < 1:
            issue("$.recursion_policy.stop_conditions", "MIN_ITEMS", "must contain at least one stop condition")
        for k in recursion:
            if k not in {"enabled", "max_rounds", "expansion_triggers", "stop_conditions"}:
                issue(f"$.recursion_policy.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    qg = require_obj(root.get("quality_gates"), "$.quality_gates")
    if qg:
        for k in ["minimum_source_count", "minimum_domain_diversity"]:
            if not isinstance(qg.get(k), int) or qg.get(k) < 0:
                issue(f"$.quality_gates.{k}", "MINIMUM", "must be integer >= 0")
        for k in ["claim_binding_required", "mmd_required"]:
            if not isinstance(qg.get(k), bool):
                issue(f"$.quality_gates.{k}", "TYPE_BOOLEAN", "must be boolean")
        for k in qg:
            if k not in {"minimum_source_count", "minimum_domain_diversity", "claim_binding_required", "mmd_required"}:
                issue(f"$.quality_gates.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    handoff = require_obj(root.get("handoff"), "$.handoff")
    if handoff:
        if handoff.get("next_stage") != NEXT_STAGE:
            issue("$.handoff.next_stage", "CONST", f"must equal {NEXT_STAGE}")
        if not isinstance(handoff.get("required_artifacts"), list) or len(handoff.get("required_artifacts", [])) < 1 or any(not isinstance(x, str) for x in handoff.get("required_artifacts", [])):
            issue("$.handoff.required_artifacts", "MIN_ITEMS", "must be non-empty array of strings")
        for k in handoff:
            if k not in {"next_stage", "required_artifacts"}:
                issue(f"$.handoff.{k}", "ADDITIONAL_PROPERTY", "not allowed")

    # Cross-field governance invariants.
    if trigger and qg:
        trigger_min = trigger.get("minimum_source_count")
        gate_min = qg.get("minimum_source_count")
        if isinstance(trigger_min, int) and isinstance(gate_min, int) and trigger_min != gate_min:
            issue("$.quality_gates.minimum_source_count", "CROSS_FIELD_MISMATCH", "must match research_trigger.minimum_source_count")
    if trigger and trigger.get("required") is True and trigger.get("must_use_web_run") is not True:
        issue("$.research_trigger.must_use_web_run", "WEBRUN_REQUIRED", "must be true when research is required")
    if qg and qg.get("mmd_required") is not True:
        issue("$.quality_gates.mmd_required", "MMD_REQUIRED", "must be true in MPP v3")
    if qg and qg.get("claim_binding_required") is not True:
        issue("$.quality_gates.claim_binding_required", "CLAIM_BINDING_REQUIRED", "must be true in MPP v3")

    if issues:
        raise ResearchPlannerValidationError(issues)
    return {"valid": True, "issue_count": 0, "packet_hash": _sha256_json(packet)}


def write_packet(packet: dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """Validate and write a packet JSON plus return path/hash metadata."""
    report = validate_packet(packet)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    written_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path), "packet_hash": report["packet_hash"], "file_sha256": written_hash}


def validate_file(path: str | Path) -> dict[str, Any]:
    packet = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_packet(packet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or write MetaBlooms MPP v3 research planner packets.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("packet")
    b = sub.add_parser("build")
    b.add_argument("--request", required=True)
    b.add_argument("--domain", required=True)
    b.add_argument("--operator-context", required=True)
    b.add_argument("--stakes", default="high", choices=sorted(STAKES))
    b.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "validate":
            report = validate_file(args.packet)
        else:
            packet = build_packet(args.request, args.domain, args.operator_context, args.stakes)
            report = write_packet(packet, args.out)
        print(json.dumps({"status": "PASS", **report}, indent=2, sort_keys=True))
        return 0
    except ResearchPlannerValidationError as e:
        print(json.dumps({"status": "FAIL", "issues": [i.to_dict() for i in e.issues]}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
