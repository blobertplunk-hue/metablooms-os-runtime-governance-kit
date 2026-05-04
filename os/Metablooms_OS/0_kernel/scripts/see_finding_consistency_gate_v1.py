#!/usr/bin/env python3
### GOVERNANCE HEADER
# artifact_id: see_finding_consistency_gate_v1
# purpose: Before any SEE finding is promoted to an amendment or governance rule,
#          check it for contradiction with locked MetaBlooms invariants and
#          the existing amendment ledger. Guards ASI01 (Agent Goal Hijack) —
#          poisoned SEE results could redirect the governance of the OS itself.
# mutation_scope: read-only (writes gate evaluation receipt only)
# owasp_risk_addressed: ASI01 Agent Goal Hijack
# see_evidence:
#   - OWASP ASI01: "Agents cannot reliably separate instructions from data —
#     a single poisoned document can redirect an agent to pursue unintended objectives"
#   - POLARIS: "Invariants are hard-coded: irreversible actions require
#     policy context before execution; approval sinks must trail validation"
###

from __future__ import annotations

import hashlib, json, os, re, time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "1.0"
OWASP_RISK = "ASI01_AGENT_GOAL_HIJACK"

DEFAULT_LEDGER = Path("/mnt/data/Metablooms_OS_refined/1_governance/workflow_v6/WORKFLOW_AMENDMENT_LEDGER_v5.json")
DEFAULT_INVARIANTS_DIR = Path("/mnt/data/Metablooms_OS_refined/governance/invariants")
DEFAULT_RECEIPT_DIR = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/see_gate_receipts")

# Hard-locked invariants — SEE findings CANNOT contradict these
HARD_LOCKED_INVARIANTS = [
    "fail_closed_on_any_phase_failure_before_P4",
    "no_active_root_mutations_before_P3_verify",
    "staging_root_isolation_required",
    "research_SEE_CE_required_for_external_claims",
    "amendment_requires_evidence_binding",
    "sha256_chain_must_not_be_broken",
    "tool_route_guard_must_precede_P0",
]

# Patterns that suggest a finding is trying to override governance
OVERRIDE_PATTERNS = [
    re.compile(r"skip.{0,20}(SEE|research|validation)", re.IGNORECASE),
    re.compile(r"bypass.{0,20}(gate|guard|check|invariant)", re.IGNORECASE),
    re.compile(r"disable.{0,20}(governance|invariant|constraint)", re.IGNORECASE),
    re.compile(r"remove.{0,20}(fail.?closed|block|barrier)", re.IGNORECASE),
    re.compile(r"always.{0,20}(allow|pass|approve)", re.IGNORECASE),
    re.compile(r"no.{0,10}(verification|validation|receipt)\s+needed", re.IGNORECASE),
]


class GateVerdict(str, Enum):
    PASS  = "PASS"
    WARN  = "WARN"
    BLOCK = "BLOCK"


@dataclass
class GateFinding:
    check_id: str
    verdict: GateVerdict
    message: str
    evidence: str = ""

    def to_dict(self) -> Dict:
        return {"check_id": self.check_id, "verdict": self.verdict.value,
                "message": self.message, "evidence": self.evidence}


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def write_json_atomic(path: Path, data: Dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    _mb_write_json_file(tmp, data, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_see_finding_consistency_gate_v1_py_L79', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    os.replace(tmp, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_amendment_ledger(ledger_path: Path) -> List[Dict]:
    if not ledger_path.exists():
        return []
    try:
        d = json.loads(ledger_path.read_text())
        return d.get("new_amendments", [])
    except Exception:
        return []


def check_override_patterns(finding_text: str) -> List[str]:
    """Return list of matched override pattern descriptions."""
    matched = []
    for pattern in OVERRIDE_PATTERNS:
        if pattern.search(finding_text):
            matched.append(pattern.pattern)
    return matched


def check_contradiction_with_locked(finding_text: str) -> List[str]:
    """Check if finding text tries to contradict hard-locked invariants."""
    contradictions = []
    finding_lower = finding_text.lower()
    for inv in HARD_LOCKED_INVARIANTS:
        inv_words = inv.replace("_", " ").lower().split()
        # If the finding contains negation near the invariant concept
        # Only check meaningful words (≥5 chars) to avoid false positives on short words like "no"
        for word in [w for w in inv_words if len(w) >= 5][:3]:
            if word in finding_lower:
                idx = finding_lower.index(word)
                # Only flag if explicit negation is IMMEDIATELY adjacent (within 12 chars)
                context = finding_lower[max(0, idx-12):idx+len(word)+12]
                if any(neg in context for neg in ["never", "disable", "skip", "bypass", "not_", "don\t"]):
                    contradictions.append(f"Possible negation of locked invariant: {inv}")
                    break
    return contradictions


def check_duplicate_amendment(finding_text: str, existing_amendments: List[Dict]) -> Optional[str]:
    """Check if the finding substantially duplicates an existing amendment."""
    finding_words = set(finding_text.lower().split())
    for amend in existing_amendments:
        trigger = amend.get("trigger", "").lower()
        existing_words = set(trigger.split())
        overlap = finding_words & existing_words
        if len(overlap) > 8 and len(overlap) / max(len(finding_words), 1) > 0.5:
            return f"High similarity to existing {amend.get('id','?')}: trigger='{trigger[:60]}'"
    return None


def evaluate_see_finding(
    finding_text: str,
    finding_source: str,
    proposed_amendment_id: Optional[str],
    ledger_path: Path,
    invariants_dir: Path,
    receipt_dir: Path,
) -> Dict:
    """
    Evaluate a SEE finding before amendment promotion.
    Returns gate evaluation with verdict.
    """
    findings: List[GateFinding] = []
    existing_amendments = load_amendment_ledger(ledger_path)

    # Check 1: Override pattern detection
    overrides = check_override_patterns(finding_text)
    if overrides:
        findings.append(GateFinding(
            "SEE_OVERRIDE_PATTERN", GateVerdict.BLOCK,
            "SEE finding contains language that attempts to override or bypass governance",
            evidence=f"Matched patterns: {overrides[:3]}",
        ))

    # Check 2: Contradiction with locked invariants
    contradictions = check_contradiction_with_locked(finding_text)
    if contradictions:
        findings.append(GateFinding(
            "SEE_CONTRADICTS_LOCKED", GateVerdict.BLOCK,
            "SEE finding appears to contradict a hard-locked MetaBlooms invariant",
            evidence="; ".join(contradictions[:3]),
        ))

    # Check 3: Duplicate amendment
    dup = check_duplicate_amendment(finding_text, existing_amendments)
    if dup:
        findings.append(GateFinding(
            "SEE_DUPLICATE_AMENDMENT", GateVerdict.WARN,
            "SEE finding closely resembles an existing amendment — review before promoting",
            evidence=dup,
        ))

    # Check 4: Source credibility (finding must cite a real source domain)
    if finding_source:
        suspicious_sources = ["localhost", "127.0.0", "internal", "unknown", "untitled"]
        if any(s in finding_source.lower() for s in suspicious_sources):
            findings.append(GateFinding(
                "SEE_SUSPICIOUS_SOURCE", GateVerdict.WARN,
                f"SEE finding source appears suspicious: '{finding_source[:60]}'",
                evidence="May indicate hallucinated or local source",
            ))
    else:
        findings.append(GateFinding(
            "SEE_NO_SOURCE", GateVerdict.WARN,
            "SEE finding has no source citation — all claims require T1/T2 backing",
        ))

    # Check 5: Minimum word count (substantive claim)
    word_count = len(finding_text.split())
    if word_count < 10:
        findings.append(GateFinding(
            "SEE_TOO_SHORT", GateVerdict.WARN,
            f"SEE finding too short ({word_count} words) to be a substantive claim",
        ))

    # Determine verdict
    blocks = [f for f in findings if f.verdict == GateVerdict.BLOCK]
    warns  = [f for f in findings if f.verdict == GateVerdict.WARN]
    verdict = GateVerdict.BLOCK if blocks else (GateVerdict.WARN if warns else GateVerdict.PASS)

    receipt = {
        "receipt_type": "SEE_FINDING_CONSISTENCY_GATE_RECEIPT",
        "gate_version": VERSION,
        "owasp_risk": OWASP_RISK,
        "created_at": time.time(),
        "finding_text_preview": finding_text[:200],
        "finding_source": finding_source,
        "proposed_amendment_id": proposed_amendment_id,
        "verdict": verdict.value,
        "block_count": len(blocks),
        "warn_count": len(warns),
        "findings": [f.to_dict() for f in findings],
        "gate_decision": (
            "ALLOW — SEE finding may proceed to amendment promotion"
            if verdict == GateVerdict.PASS
            else "CONDITIONAL — review warnings before promoting"
            if verdict == GateVerdict.WARN
            else "DENY — SEE finding blocked from amendment promotion"
        ),
    }

    # Write receipt
    ts = int(time.time() * 1000)
    aid = (proposed_amendment_id or "UNKNOWN").replace("-", "_")
    receipt_path = receipt_dir / f"SEE_GATE_{aid}_{ts}.json"
    receipt_sha = write_json_atomic(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    receipt["receipt_sha"] = receipt_sha

    # Console output
    icon = {"PASS": "✓", "WARN": "⚠", "BLOCK": "✗"}[verdict.value]
    print(f"  [{icon}] SEE gate: {verdict.value}  blocks={len(blocks)} warns={len(warns)}")
    if blocks:
        for f in blocks:
            print(f"    BLOCK [{f.check_id}]: {f.message[:70]}")

    return receipt


def main(argv=None):
    import argparse, sys
    ap = argparse.ArgumentParser(description="MetaBlooms SEE Finding Consistency Gate v1 — ASI01 guard")
    ap.add_argument("--finding-text",   required=True)
    ap.add_argument("--finding-source", default="")
    ap.add_argument("--amendment-id",   default=None)
    ap.add_argument("--ledger",         default=str(DEFAULT_LEDGER))
    ap.add_argument("--invariants-dir", default=str(DEFAULT_INVARIANTS_DIR))
    ap.add_argument("--receipt-dir",    default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--json-output",    action="store_true")
    args = ap.parse_args(argv)

    result = evaluate_see_finding(
        finding_text=args.finding_text,
        finding_source=args.finding_source,
        proposed_amendment_id=args.amendment_id,
        ledger_path=Path(args.ledger),
        invariants_dir=Path(args.invariants_dir),
        receipt_dir=Path(args.receipt_dir),
    )
    if args.json_output:
        print(json.dumps(result, indent=2))
    sys.exit(0 if result["verdict"] in ("PASS", "WARN") else 1)


if __name__ == "__main__":
    main()
