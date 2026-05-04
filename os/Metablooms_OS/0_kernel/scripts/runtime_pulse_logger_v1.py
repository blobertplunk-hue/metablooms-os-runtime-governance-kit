#!/usr/bin/env python3
### GOVERNANCE HEADER
# artifact_id: runtime_pulse_logger_v1
# purpose: Execution-time governance layer. Runs lightweight pre+post artifact
#          pulse checks and writes every result to a hash-chained, append-only
#          RUNTIME_PULSE_LOG_v1.jsonl ledger. Implements AMEND-0008.
# mutation_scope: read-only (writes pulse log only; never mutates OS tree)
# invariants_enforced:
#   - RP-PRE-1 through RP-PRE-4 run before each artifact
#   - RP-POST-1 through RP-POST-4 run after each artifact
#   - T1 failures BLOCK; T2 failures FLAG
#   - Every pulse entry chained to prior entry SHA256 (tamper-evident)
#   - No external tool calls — context-only checks, constant-time overhead
#   - T1 block on RP-PRE-4: open IC trigger from prior artifact blocks next start
# risk_level: governance-layer
# see_evidence:
#   - "Append-only log where each entry includes hash linking to previous — any alteration invalidates chain"
#   - "Tamper-resistant timestamped ledger of every system modification or agent action"
#   - "Observability turns Responsible AI into an engineering control loop — enforcement not aspiration"
###

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# MetaBlooms Stage4 atomic append-log enforcement shim.
import sys as _MB_SYS
_MB_SELF = Path(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_IO_LIB = _MB_PARENT / "0_kernel" / "lib" / "io"
    if (_MB_IO_LIB / "atomic_append_log_compat_v1.py").exists():
        if str(_MB_IO_LIB) not in _MB_SYS.path:
            _MB_SYS.path.insert(0, str(_MB_IO_LIB))
        break
from atomic_append_log_compat_v1 import append_jsonl_record as _mb_append_jsonl_record

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
VERSION = "1.0"
AMENDMENT = "AMEND-0008"
WORKFLOW_VERSION = "v6"

DEFAULT_ROOT = Path("/mnt/data/Metablooms_OS")
DEFAULT_PULSE_LOG = Path(
    "/mnt/data/Metablooms_OS/0_kernel/registry/RUNTIME_PULSE_LOG_v1.jsonl"
)
INTERRUPT_RECEIPT_DIR = Path(
    "/mnt/data/Metablooms_OS/0_kernel/registry/interrupt_receipts"
)


class PulsePhase(str, Enum):
    PRE  = "pre"
    POST = "post"


class PulseTier(str, Enum):
    T1 = "T1"   # block on failure
    T2 = "T2"   # flag on failure, continue


class PulseDecision(str, Enum):
    PASS  = "pass"
    BLOCK = "block"
    FLAG  = "flag"


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PulseCheck:
    pulse_id: str
    phase: PulsePhase
    tier: PulseTier
    description: str

    def evaluate(self, ctx: "ArtifactPulseContext") -> "PulseResult":
        raise NotImplementedError


@dataclass
class PulseResult:
    pulse_id: str
    phase: PulsePhase
    tier: PulseTier
    decision: PulseDecision
    evidence: str
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pulse_id": self.pulse_id,
            "phase": self.phase.value,
            "tier": self.tier.value,
            "decision": self.decision.value,
            "evidence": self.evidence,
            "ts": self.ts,
        }


@dataclass
class ArtifactPulseContext:
    """All context needed to evaluate pulse checks for one artifact."""
    artifact_id: str
    stage_name: str
    stage_id: str

    # RP-PRE-1: is this artifact in the current queue?
    in_current_queue: bool = True

    # RP-PRE-2: is the artifact SHA known?
    sha_known: bool = True
    declared_sha: Optional[str] = None

    # RP-PRE-3: does this artifact class require SEE?
    see_required: bool = False
    see_loaded: bool = False

    # RP-PRE-4: is there an open IC trigger from prior artifact?
    open_ic_trigger: bool = False
    open_ic_receipt_id: Optional[str] = None

    # RP-POST-1: does the receipt exist with required fields?
    receipt_path: Optional[str] = None
    receipt_required_fields: List[str] = field(
        default_factory=lambda: ["artifact_id", "verdict", "created_at"]
    )

    # RP-POST-2: are output artifact SHAs declared in the receipt?
    output_shas_declared: bool = True

    # RP-POST-3: IC trigger detected post-processing?
    ic_triggered_post: bool = False
    ic_condition: Optional[str] = None

    # RP-POST-4: new success pattern emerged?
    success_pattern_detected: bool = False
    success_pattern_id: Optional[str] = None

    # Extra context
    extra: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# PULSE CHECK IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────────────────────────

class RpPre1(PulseCheck):
    """RP-PRE-1 (T1): Artifact in current queue — block if not."""
    def __init__(self):
        super().__init__("RP-PRE-1", PulsePhase.PRE, PulseTier.T1,
                         "Artifact must be in current queue")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if ctx.in_current_queue:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "artifact in current queue")
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.BLOCK,
                           f"artifact '{ctx.artifact_id}' not in current queue — possible rogue execution")


class RpPre2(PulseCheck):
    """RP-PRE-2 (T1): Artifact SHA known/verified — block if unknown."""
    def __init__(self):
        super().__init__("RP-PRE-2", PulsePhase.PRE, PulseTier.T1,
                         "Artifact SHA must be known before processing")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if ctx.sha_known:
            sha_info = f"SHA: {ctx.declared_sha[:16]}..." if ctx.declared_sha else "SHA known"
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, sha_info)
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.BLOCK,
                           f"SHA unknown for '{ctx.artifact_id}' — cannot verify provenance")


class RpPre3(PulseCheck):
    """RP-PRE-3 (T2): SEE pre-loaded if artifact class requires it — flag if missing."""
    def __init__(self):
        super().__init__("RP-PRE-3", PulsePhase.PRE, PulseTier.T2,
                         "SEE packet must be loaded for research-requiring artifacts")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if not ctx.see_required:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "SEE not required for this artifact class")
        if ctx.see_loaded:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "SEE packet pre-loaded ✓")
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.FLAG,
                           f"SEE required but not loaded for '{ctx.artifact_id}' — "
                           f"claims may be T4-TRAINING-ONLY")


class RpPre4(PulseCheck):
    """RP-PRE-4 (T1): No open IC trigger from prior artifact — block until resolved."""
    def __init__(self):
        super().__init__("RP-PRE-4", PulsePhase.PRE, PulseTier.T1,
                         "Open IC triggers from prior artifact must be resolved")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if not ctx.open_ic_trigger:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "no open IC triggers")
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.BLOCK,
                           f"open IC trigger not resolved: {ctx.open_ic_receipt_id} — "
                           f"resolve before processing next artifact")


class RpPost1(PulseCheck):
    """RP-POST-1 (T1): Receipt exists with required fields — block export if missing."""
    def __init__(self):
        super().__init__("RP-POST-1", PulsePhase.POST, PulseTier.T1,
                         "Artifact receipt must exist with all required fields")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if not ctx.receipt_path:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.BLOCK,
                               f"no receipt path declared for '{ctx.artifact_id}' — block export")
        rp = Path(ctx.receipt_path)
        if not rp.exists():
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.BLOCK,
                               f"receipt file not found: {ctx.receipt_path}")
        try:
            receipt_data = json.loads(rp.read_text())
            missing = [f for f in ctx.receipt_required_fields if f not in receipt_data]
            if missing:
                return PulseResult(self.pulse_id, self.phase, self.tier,
                                   PulseDecision.BLOCK,
                                   f"receipt missing required fields: {missing}")
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS,
                               f"receipt valid with {len(receipt_data)} fields")
        except (json.JSONDecodeError, OSError) as e:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.BLOCK, f"receipt unreadable: {e}")


class RpPost2(PulseCheck):
    """RP-POST-2 (T1): Output SHAs declared in receipt — block if missing."""
    def __init__(self):
        super().__init__("RP-POST-2", PulsePhase.POST, PulseTier.T1,
                         "All output artifact SHAs must be declared in receipt")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if ctx.output_shas_declared:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "output SHAs declared in receipt ✓")
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.BLOCK,
                           f"output SHAs not declared for '{ctx.artifact_id}' — "
                           f"provenance chain broken")


class RpPost3(PulseCheck):
    """RP-POST-3 (T2): IC condition triggered post-processing — interrupt if yes."""
    def __init__(self):
        super().__init__("RP-POST-3", PulsePhase.POST, PulseTier.T2,
                         "Post-processing IC trigger check")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if not ctx.ic_triggered_post:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "no IC conditions triggered post-processing")
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.FLAG,
                           f"IC condition triggered: {ctx.ic_condition} — "
                           f"interrupt checker should have been called for this artifact")


class RpPost4(PulseCheck):
    """RP-POST-4 (T2): New success pattern emerged — log and optionally generate sidecar."""
    def __init__(self):
        super().__init__("RP-POST-4", PulsePhase.POST, PulseTier.T2,
                         "Check for new success patterns post-processing")

    def evaluate(self, ctx: ArtifactPulseContext) -> PulseResult:
        if not ctx.success_pattern_detected:
            return PulseResult(self.pulse_id, self.phase, self.tier,
                               PulseDecision.PASS, "no new success pattern detected")
        return PulseResult(self.pulse_id, self.phase, self.tier,
                           PulseDecision.FLAG,
                           f"success pattern detected: {ctx.success_pattern_id} — "
                           f"log to SUCCESS_PATTERN_REGISTRY and consider sidecar generation")


# ─────────────────────────────────────────────────────────────────────────────
# HASH-CHAINED PULSE LOG
# ─────────────────────────────────────────────────────────────────────────────

SENTINEL_HASH = "0" * 64  # genesis chain anchor

def _chain_hash(prior_entry_sha: str, entry: Dict[str, Any]) -> str:
    """Compute chain link: SHA256(prior_sha + json(entry))."""
    payload = prior_entry_sha + json.dumps(entry, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()


def append_pulse_entry(
    log_path: Path,
    entry: Dict[str, Any],
) -> str:
    """
    Append a pulse entry to the JSONL log with hash chain.
    Returns the SHA256 of the written entry (chain link for next entry).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Read last entry to get prior chain hash
    prior_hash = SENTINEL_HASH
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines):
                if line.strip():
                    last = json.loads(line)
                    prior_hash = last.get("chain_sha", SENTINEL_HASH)
                    break
        except (json.JSONDecodeError, OSError):
            prior_hash = SENTINEL_HASH

    # Normalize the record before hashing so the serialized append-log record
    # preserves the same hash-chain semantics that verification recomputes.
    entry.setdefault("schema_version", "RuntimePulseLogEntry.v1")
    entry.setdefault("event_id", f"pulse_{int(time.time() * 1000000)}")
    entry.setdefault("timestamp_utc", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    entry.setdefault("source", "runtime_pulse_logger_v1")
    entry.setdefault("event_type", str(entry.get("phase") or entry.get("pulse_id") or "runtime_pulse"))
    entry.setdefault("severity", "critical" if entry.get("decision") == "block" else "info")
    entry.setdefault("payload", {"pulse_record_keys": sorted(str(k) for k in entry.keys())})

    # Add chain link after normalization.
    entry["chain_sha"] = _chain_hash(prior_hash, entry)
    entry["prior_chain_sha"] = prior_hash

    _mb_append_jsonl_record(
        log_path,
        entry,
        operation_id=f"runtime_pulse_append_{entry.get('event_id')}",
        allowed_roots=[str(DEFAULT_ROOT.resolve())],
        receipt_dir=DEFAULT_ROOT / "runtime" / "receipts" / "append_log_writer" / "runtime_pulse",
        source="runtime_pulse_logger_v1",
        event_type=str(entry.get("event_type") or "runtime_pulse"),
        severity=str(entry.get("severity") or "info"),
        durability_mode="sync_on_critical",
    )

    return entry["chain_sha"]


def verify_pulse_log(log_path: Path) -> Tuple[bool, int, List[str]]:
    """
    Verify hash chain integrity of the entire pulse log.
    Returns (is_valid, entries_checked, list_of_violations).
    """
    if not log_path.exists():
        return True, 0, []

    lines = [l for l in log_path.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
    violations = []
    prior_hash = SENTINEL_HASH

    for i, line in enumerate(lines):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            violations.append(f"Line {i+1}: JSON parse error: {e}")
            continue

        stored_chain = entry.get("chain_sha", "")
        stored_prior = entry.get("prior_chain_sha", SENTINEL_HASH)

        # Recompute chain hash (without chain fields)
        check_entry = {k: v for k, v in entry.items()
                       if k not in ("chain_sha", "prior_chain_sha")}
        expected_chain = _chain_hash(stored_prior, check_entry)

        if stored_prior != prior_hash:
            violations.append(
                f"Line {i+1}: prior_chain_sha mismatch "
                f"(expected {prior_hash[:16]}... got {stored_prior[:16]}...)"
            )
        if stored_chain != expected_chain:
            violations.append(
                f"Line {i+1}: chain_sha invalid "
                f"(expected {expected_chain[:16]}... got {stored_chain[:16]}...)"
            )

        prior_hash = stored_chain

    return len(violations) == 0, len(lines), violations


# ─────────────────────────────────────────────────────────────────────────────
# PULSE RUNNER
# ─────────────────────────────────────────────────────────────────────────────

PRE_CHECKS  = [RpPre1(),  RpPre2(),  RpPre3(),  RpPre4()]
POST_CHECKS = [RpPost1(), RpPost2(), RpPost3(), RpPost4()]


def run_pulse(
    ctx: ArtifactPulseContext,
    phase: PulsePhase,
    log_path: Path,
) -> Tuple[bool, List[PulseResult]]:
    """
    Run all pulse checks for a given phase.
    Returns (all_passed, list_of_results).
    Writes each result to the hash-chained log immediately.
    """
    checks = PRE_CHECKS if phase == PulsePhase.PRE else POST_CHECKS
    results: List[PulseResult] = []
    has_block = False

    for check in checks:
        result = check.evaluate(ctx)
        results.append(result)

        # Write to log immediately
        log_entry = {
            "artifact_id": ctx.artifact_id,
            "stage_name": ctx.stage_name,
            "stage_id": ctx.stage_id,
            **result.to_dict(),
        }
        append_pulse_entry(log_path, log_entry)

        # Console feedback
        icon = "✓" if result.decision == PulseDecision.PASS else (
               "⚠" if result.decision == PulseDecision.FLAG else "✗")
        tier_str = f"[{result.tier.value}]"
        print(f"    {icon} {result.pulse_id} {tier_str}: {result.evidence[:70]}")

        if result.decision == PulseDecision.BLOCK:
            has_block = True

    return not has_block, results


def run_pre_pulse(ctx: ArtifactPulseContext,
                  log_path: Optional[Path] = None) -> Tuple[bool, List[PulseResult]]:
    if log_path is None:
        log_path = DEFAULT_PULSE_LOG
    print(f"  [PRE-PULSE] {ctx.artifact_id}")
    return run_pulse(ctx, PulsePhase.PRE, log_path)


def run_post_pulse(ctx: ArtifactPulseContext,
                   log_path: Optional[Path] = None) -> Tuple[bool, List[PulseResult]]:
    if log_path is None:
        log_path = DEFAULT_PULSE_LOG
    print(f"  [POST-PULSE] {ctx.artifact_id}")
    return run_pulse(ctx, PulsePhase.POST, log_path)


def run_full_pulse(ctx: ArtifactPulseContext,
                   log_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Run pre + post pulse for a single artifact.
    Returns summary dict with: pre_passed, post_passed, blocks, flags, results.
    """
    if log_path is None:
        log_path = DEFAULT_PULSE_LOG

    pre_passed, pre_results = run_pre_pulse(ctx, log_path)
    post_passed, post_results = run_post_pulse(ctx, log_path)

    all_results = pre_results + post_results
    blocks = [r for r in all_results if r.decision == PulseDecision.BLOCK]
    flags  = [r for r in all_results if r.decision == PulseDecision.FLAG]

    return {
        "artifact_id": ctx.artifact_id,
        "pre_passed": pre_passed,
        "post_passed": post_passed,
        "all_passed": pre_passed and post_passed,
        "block_count": len(blocks),
        "flag_count": len(flags),
        "blocks": [{"pulse_id": b.pulse_id, "evidence": b.evidence} for b in blocks],
        "flags":  [{"pulse_id": f.pulse_id, "evidence": f.evidence} for f in flags],
    }


# ─────────────────────────────────────────────────────────────────────────────
# LOG QUERY UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def query_pulse_log(
    log_path: Path,
    artifact_id: Optional[str] = None,
    stage_id: Optional[str] = None,
    decision_filter: Optional[str] = None,  # "pass" | "block" | "flag"
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Query pulse log entries with optional filters."""
    if not log_path.exists():
        return []

    results = []
    for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if artifact_id and entry.get("artifact_id") != artifact_id:
            continue
        if stage_id and entry.get("stage_id") != stage_id:
            continue
        if decision_filter and entry.get("decision") != decision_filter:
            continue

        results.append(entry)
        if len(results) >= limit:
            break

    return results


def pulse_log_summary(log_path: Path) -> Dict[str, Any]:
    """Return aggregate statistics from the pulse log."""
    if not log_path.exists():
        return {"total": 0, "pass": 0, "block": 0, "flag": 0, "artifacts": 0}

    total = pass_c = block_c = flag_c = 0
    artifacts: set = set()

    for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        d = e.get("decision", "")
        if d == "pass":
            pass_c += 1
        elif d == "block":
            block_c += 1
        elif d == "flag":
            flag_c += 1
        if "artifact_id" in e:
            artifacts.add(e["artifact_id"])

    valid, checked, violations = verify_pulse_log(log_path)
    return {
        "total_entries": total,
        "pass": pass_c,
        "block": block_c,
        "flag": flag_c,
        "artifacts_logged": len(artifacts),
        "chain_valid": valid,
        "chain_entries_checked": checked,
        "chain_violations": violations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MetaBlooms Runtime Pulse Logger v1 — RP-PRE-1→4 + RP-POST-1→4"
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # run-pre
    pre = sub.add_parser("run-pre", help="Run pre-artifact pulse checks")
    pre.add_argument("--artifact-id",  required=True)
    pre.add_argument("--stage-name",   required=True)
    pre.add_argument("--stage-id",     required=True)
    pre.add_argument("--in-queue",     type=lambda x: x.lower()=="true", default=True)
    pre.add_argument("--sha-known",    type=lambda x: x.lower()=="true", default=True)
    pre.add_argument("--declared-sha", default=None)
    pre.add_argument("--see-required", type=lambda x: x.lower()=="true", default=False)
    pre.add_argument("--see-loaded",   type=lambda x: x.lower()=="true", default=False)
    pre.add_argument("--open-ic",      type=lambda x: x.lower()=="true", default=False)
    pre.add_argument("--open-ic-id",   default=None)
    pre.add_argument("--log",          default=str(DEFAULT_PULSE_LOG))

    # run-post
    post = sub.add_parser("run-post", help="Run post-artifact pulse checks")
    post.add_argument("--artifact-id",          required=True)
    post.add_argument("--stage-name",            required=True)
    post.add_argument("--stage-id",              required=True)
    post.add_argument("--receipt-path",          default=None)
    post.add_argument("--shas-declared",         type=lambda x: x.lower()=="true", default=True)
    post.add_argument("--ic-triggered",          type=lambda x: x.lower()=="true", default=False)
    post.add_argument("--ic-condition",          default=None)
    post.add_argument("--success-pattern",       type=lambda x: x.lower()=="true", default=False)
    post.add_argument("--success-pattern-id",    default=None)
    post.add_argument("--log",                   default=str(DEFAULT_PULSE_LOG))

    # verify
    verify = sub.add_parser("verify", help="Verify pulse log chain integrity")
    verify.add_argument("--log", default=str(DEFAULT_PULSE_LOG))

    # summary
    summ = sub.add_parser("summary", help="Print pulse log summary statistics")
    summ.add_argument("--log", default=str(DEFAULT_PULSE_LOG))

    # query
    qry = sub.add_parser("query", help="Query pulse log entries")
    qry.add_argument("--log",       default=str(DEFAULT_PULSE_LOG))
    qry.add_argument("--artifact-id", default=None)
    qry.add_argument("--stage-id",    default=None)
    qry.add_argument("--decision",    default=None, choices=["pass","block","flag"])
    qry.add_argument("--limit",       type=int, default=20)

    args = ap.parse_args(argv)
    import sys

    if args.command in ("run-pre", "run-post"):
        ctx = ArtifactPulseContext(
            artifact_id=args.artifact_id,
            stage_name=args.stage_name,
            stage_id=args.stage_id,
        )
        log_path = Path(args.log)

        if args.command == "run-pre":
            ctx.in_current_queue  = args.in_queue
            ctx.sha_known         = args.sha_known
            ctx.declared_sha      = args.declared_sha
            ctx.see_required      = args.see_required
            ctx.see_loaded        = args.see_loaded
            ctx.open_ic_trigger   = args.open_ic
            ctx.open_ic_receipt_id = args.open_ic_id
            passed, results = run_pre_pulse(ctx, log_path)
        else:
            ctx.receipt_path          = args.receipt_path
            ctx.output_shas_declared  = args.shas_declared
            ctx.ic_triggered_post     = args.ic_triggered
            ctx.ic_condition          = args.ic_condition
            ctx.success_pattern_detected = args.success_pattern
            ctx.success_pattern_id    = args.success_pattern_id
            passed, results = run_post_pulse(ctx, log_path)

        blocks = [r for r in results if r.decision == PulseDecision.BLOCK]
        print(f"\n  Result: {'PASS' if passed else 'BLOCK'}  "
              f"Blocks: {len(blocks)}")
        sys.exit(0 if passed else 1)

    elif args.command == "verify":
        valid, count, violations = verify_pulse_log(Path(args.log))
        print(f"Chain integrity: {'VALID ✓' if valid else 'INVALID ✗'}")
        print(f"Entries checked: {count}")
        if violations:
            print("Violations:")
            for v in violations:
                print(f"  {v}")
        sys.exit(0 if valid else 1)

    elif args.command == "summary":
        s = pulse_log_summary(Path(args.log))
        print(json.dumps(s, indent=2))
        sys.exit(0)

    elif args.command == "query":
        entries = query_pulse_log(
            Path(args.log),
            artifact_id=args.artifact_id,
            stage_id=args.stage_id,
            decision_filter=args.decision,
            limit=args.limit,
        )
        for e in entries:
            print(json.dumps(e))
        sys.exit(0)


if __name__ == "__main__":
    main()
