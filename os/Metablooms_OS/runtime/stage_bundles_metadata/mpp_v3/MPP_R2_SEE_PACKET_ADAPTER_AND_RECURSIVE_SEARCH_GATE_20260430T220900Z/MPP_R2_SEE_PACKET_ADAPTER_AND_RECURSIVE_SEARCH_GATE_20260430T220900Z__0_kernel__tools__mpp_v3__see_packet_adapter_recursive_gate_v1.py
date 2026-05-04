#!/usr/bin/env python3
"""MetaBlooms MPP v3 SEE packet adapter and recursive search gate v1.

CDR V1 Rationale:
    Converts a validated RESEARCH_PLANNER packet into a canonical SEE packet
    and enforces recursive-search quality gates before CE/MMD can proceed.

CDR V2 Trust:
    Delegates SEE packet validation to the existing OS SEE validator contract
    when available. The adapter never marks a packet PASS without web.run
    evidence, source-bound claims, source diversity, recursion accounting, and
    stop-condition evidence.

CDR V3 Boundary:
    Inputs: research_planner_packet.v1 and web.run evidence payload.
    Outputs: see_packet.v1, recursive_gate_report.v1, optional files.
    Side effects: only explicit write_* helpers write JSON artifacts.

CDR V4 Failure:
    Raises SEEAdapterValidationError with deterministic issue dictionaries.
    Safe state: halt before CE/MMD and write a blocked receipt.

CDR V5 Integration:
    Stage order: RESEARCH_PLANNER -> SEE -> NORMALIZE_EVIDENCE -> CE -> MMD.
    This adapter binds MPP v3 SEE to the OS SEE_PACKET_SCHEMA_v1 and
    see_packet_validator_v1.py semantics instead of using generic legacy SEE.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SEE_PACKET_VERSION = "see_packet.v1"
SEE_STAGE = "SEE_PASS"
NEXT_STAGE = "NORMALIZE_EVIDENCE"
SOURCE_DOMAIN_RE = re.compile(r"^(?:https?://)?(?:www\.)?([^/]+)/?")


@dataclass(frozen=True)
class SEEAdapterIssue:
    path: str
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


class SEEAdapterValidationError(RuntimeError):
    def __init__(self, issues: list[SEEAdapterIssue]) -> None:
        self.issues = issues
        summary = "; ".join(f"{i.path}:{i.code}" for i in issues[:10])
        super().__init__(f"SEE_PACKET_ADAPTER_GATE_FAILED: {summary}")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _domain_from_source(source: dict[str, Any]) -> str:
    url = str(source.get("url_or_ref", ""))
    match = SOURCE_DOMAIN_RE.match(url)
    if match:
        return match.group(1).lower()
    ref = str(source.get("source_id", "unknown"))
    return ref.split(":", 1)[0].lower()


def _load_existing_see_validator(root: Path):
    validator_path = root / "0_kernel/scripts/see_packet_validator_v1.py"
    if not validator_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("see_packet_validator_v1", validator_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_research_planner_minimal(packet: dict[str, Any]) -> list[SEEAdapterIssue]:
    issues: list[SEEAdapterIssue] = []
    def issue(path: str, code: str, message: str) -> None:
        issues.append(SEEAdapterIssue(path, code, message))
    if not isinstance(packet, dict):
        return [SEEAdapterIssue("$", "TYPE_OBJECT", "research planner packet must be object")]
    if packet.get("schema_version") != "research_planner_packet.v1":
        issue("$.schema_version", "CONST", "must be research_planner_packet.v1")
    if packet.get("stage") != "RESEARCH_PLANNER":
        issue("$.stage", "CONST", "must equal RESEARCH_PLANNER")
    trigger = packet.get("research_trigger", {})
    if not isinstance(trigger, dict) or trigger.get("required") is not True:
        issue("$.research_trigger.required", "REQUIRED_TRUE", "research must be required")
    if isinstance(trigger, dict) and trigger.get("must_use_web_run") is not True:
        issue("$.research_trigger.must_use_web_run", "WEBRUN_REQUIRED", "must use web.run")
    qplan = packet.get("query_plan")
    if not isinstance(qplan, list) or len(qplan) < 1:
        issue("$.query_plan", "MIN_ITEMS", "at least one query is required")
    handoff = packet.get("handoff", {})
    if not isinstance(handoff, dict) or handoff.get("next_stage") != "SEE":
        issue("$.handoff.next_stage", "NEXT_STAGE", "research planner must hand off to SEE")
    return issues


def build_see_packet(research_packet: dict[str, Any], web_evidence: dict[str, Any]) -> dict[str, Any]:
    """Build a canonical SEE packet from a research planner packet and web evidence."""
    rp_issues = validate_research_planner_minimal(research_packet)
    if rp_issues:
        raise SEEAdapterValidationError(rp_issues)
    if not isinstance(web_evidence, dict):
        raise SEEAdapterValidationError([SEEAdapterIssue("$.web_evidence", "TYPE_OBJECT", "web evidence must be object")])

    sources = web_evidence.get("sources", [])
    claims = web_evidence.get("claims", [])
    if not isinstance(sources, list):
        sources = []
    if not isinstance(claims, list):
        claims = []

    qplan = []
    for item in research_packet.get("query_plan", []):
        if isinstance(item, dict):
            qplan.append({
                "query": str(item.get("query", "")),
                "purpose": str(item.get("purpose", "")),
                "expected_source_type": str(item.get("expected_evidence_type", "")),
                "research_planner_query_id": item.get("query_id"),
            })

    trigger_terms = []
    obj = research_packet.get("objective", {})
    if isinstance(obj, dict):
        trigger_terms = [str(obj.get("domain", "")).strip(), str(obj.get("request", "")).strip()]
        trigger_terms = [t for t in trigger_terms if t]

    packet = {
        "version": SEE_PACKET_VERSION,
        "created_at": _now_iso(),
        "stage": SEE_STAGE,
        "original_request": obj.get("request", "") if isinstance(obj, dict) else "",
        "research_trigger": {
            "required": True,
            "trigger_reason": "MPP v3 Research Planner required SEE before downstream CE/MMD stages.",
            "trigger_terms": trigger_terms or ["MPP v3", "SEE"],
            "research_planner_packet_id": research_packet.get("packet_id"),
        },
        "query_plan": qplan,
        "web_run_evidence": {
            "web_run_called": web_evidence.get("web_run_called") is True,
            "call_count": int(web_evidence.get("call_count", 0) or 0),
            "tool_reference_required": True,
            "query_refs": web_evidence.get("query_refs", []),
            "research_rounds": web_evidence.get("research_rounds", []),
        },
        "sources": sources,
        "claim_source_bindings": claims,
        "gaps_and_contradictions": web_evidence.get("gaps_and_contradictions", {"gaps": [], "contradictions": []}),
        "synthesis": web_evidence.get("synthesis", ""),
        "limitations": web_evidence.get("limitations", []),
        "see_verdict": web_evidence.get("see_verdict", "PASS"),
        "mpp_v3_adapter": {
            "adapter": "see_packet_adapter_recursive_gate_v1",
            "research_packet_hash": _sha256_json(research_packet),
            "next_stage": NEXT_STAGE,
        },
    }
    return packet


def recursive_search_gate(
    research_packet: dict[str, Any],
    see_packet: dict[str, Any],
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Enforce recursive search quality and delegate SEE validation."""
    issues: list[SEEAdapterIssue] = []
    def issue(path: str, code: str, message: str) -> None:
        issues.append(SEEAdapterIssue(path, code, message))

    qg = research_packet.get("quality_gates", {}) if isinstance(research_packet, dict) else {}
    recursion = research_packet.get("recursion_policy", {}) if isinstance(research_packet, dict) else {}
    min_sources = int(qg.get("minimum_source_count", 1) or 1) if isinstance(qg, dict) else 1
    min_diversity = int(qg.get("minimum_domain_diversity", 1) or 1) if isinstance(qg, dict) else 1
    max_rounds = int(recursion.get("max_rounds", 0) or 0) if isinstance(recursion, dict) else 0

    sources = see_packet.get("sources", []) if isinstance(see_packet, dict) else []
    claims = see_packet.get("claim_source_bindings", []) if isinstance(see_packet, dict) else []
    evidence = see_packet.get("web_run_evidence", {}) if isinstance(see_packet, dict) else {}
    gaps = see_packet.get("gaps_and_contradictions", {}) if isinstance(see_packet, dict) else {}
    rounds = evidence.get("research_rounds", []) if isinstance(evidence, dict) else []

    if not isinstance(sources, list) or len(sources) < min_sources:
        issue("$.sources", "MIN_SOURCE_COUNT", f"requires at least {min_sources} sources")
    domains = {_domain_from_source(s) for s in sources if isinstance(s, dict)}
    if len(domains) < min_diversity:
        issue("$.sources", "MIN_DOMAIN_DIVERSITY", f"requires at least {min_diversity} source domains")
    if not isinstance(claims, list) or not claims:
        issue("$.claim_source_bindings", "CLAIM_BINDING_REQUIRED", "at least one source-bound claim is required")
    if isinstance(evidence, dict) and evidence.get("web_run_called") is not True:
        issue("$.web_run_evidence.web_run_called", "WEBRUN_REQUIRED", "web.run evidence must be true")
    if not isinstance(rounds, list):
        issue("$.web_run_evidence.research_rounds", "TYPE_ARRAY", "research_rounds must be array")
        rounds = []
    if len(rounds) > max_rounds:
        issue("$.web_run_evidence.research_rounds", "MAX_RECURSION_ROUNDS", f"rounds exceed max_rounds={max_rounds}")
    if len(rounds) == 0 and max_rounds > 0:
        issue("$.web_run_evidence.research_rounds", "RECURSION_ACCOUNTING_REQUIRED", "at least one research round record is required")
    if isinstance(gaps, dict):
        critical = [g for g in gaps.get("gaps", []) if isinstance(g, dict) and g.get("severity") == "critical" and not g.get("resolved")]
        if critical:
            issue("$.gaps_and_contradictions.gaps", "CRITICAL_GAP_UNRESOLVED", "critical gaps block SEE pass")
    else:
        issue("$.gaps_and_contradictions", "TYPE_OBJECT", "must be object")

    root_path = Path(root) if root is not None else Path.cwd()
    existing_validator_result: dict[str, Any] | None = None
    module = _load_existing_see_validator(root_path)
    if module is not None:
        schema_path = root_path / "0_kernel/schemas/SEE_PACKET_SCHEMA_v1.json"
        if schema_path.exists():
            schema = _load_json(schema_path)
            existing_validator_result = module.validate_packet(see_packet, schema)
            if existing_validator_result.get("verdict") != "PASS":
                for validator_issue in existing_validator_result.get("issues", []):
                    issue("$.see_packet", "OS_SEE_VALIDATOR", str(validator_issue))
        else:
            issue("$.schema", "SEE_SCHEMA_MISSING", str(schema_path))
    else:
        issue("$.validator", "SEE_VALIDATOR_MISSING", "existing OS see_packet_validator_v1.py not found/importable")

    verdict = "PASS" if not issues else "FAIL"
    return {
        "schema_version": "mpp_v3.see_recursive_gate_report.v1",
        "stage": "SEE_RECURSIVE_SEARCH_GATE",
        "created_at": _now_iso(),
        "verdict": verdict,
        "issues": [i.to_dict() for i in issues],
        "minimum_source_count": min_sources,
        "minimum_domain_diversity": min_diversity,
        "observed_source_count": len(sources) if isinstance(sources, list) else 0,
        "observed_domain_diversity": len(domains),
        "observed_recursion_rounds": len(rounds),
        "max_recursion_rounds": max_rounds,
        "existing_see_validator_verdict": (existing_validator_result or {}).get("verdict"),
        "see_packet_hash": _sha256_json(see_packet),
        "research_packet_hash": _sha256_json(research_packet),
        "next_stage": NEXT_STAGE if verdict == "PASS" else "BLOCK_WITH_SEE_RECEIPT",
    }


def adapt_and_gate(research_packet: dict[str, Any], web_evidence: dict[str, Any], root: str | Path | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    see_packet = build_see_packet(research_packet, web_evidence)
    gate = recursive_search_gate(research_packet, see_packet, root)
    if gate["verdict"] != "PASS":
        raise SEEAdapterValidationError([SEEAdapterIssue(i["path"], i["code"], i["message"]) for i in gate["issues"]])
    return see_packet, gate


def write_json(obj: Any, path: str | Path) -> dict[str, Any]:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and gate MPP v3 SEE packets from Research Planner packets.")
    parser.add_argument("--research-packet", required=True)
    parser.add_argument("--web-evidence", required=True)
    parser.add_argument("--root", default=str(Path.cwd()))
    parser.add_argument("--out-see", required=True)
    parser.add_argument("--out-gate", required=True)
    args = parser.parse_args(argv)
    try:
        research_packet = _load_json(args.research_packet)
        web_evidence = _load_json(args.web_evidence)
        see_packet = build_see_packet(research_packet, web_evidence)
        gate = recursive_search_gate(research_packet, see_packet, args.root)
        see_meta = write_json(see_packet, args.out_see)
        gate_meta = write_json(gate, args.out_gate)
        status = {"status": "PASS" if gate["verdict"] == "PASS" else "FAIL", "see": see_meta, "gate": gate_meta, "gate_verdict": gate["verdict"], "issues": gate["issues"]}
        print(json.dumps(status, indent=2, sort_keys=True))
        return 0 if gate["verdict"] == "PASS" else 2
    except SEEAdapterValidationError as e:
        print(json.dumps({"status": "FAIL", "issues": [i.to_dict() for i in e.issues]}, indent=2, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
