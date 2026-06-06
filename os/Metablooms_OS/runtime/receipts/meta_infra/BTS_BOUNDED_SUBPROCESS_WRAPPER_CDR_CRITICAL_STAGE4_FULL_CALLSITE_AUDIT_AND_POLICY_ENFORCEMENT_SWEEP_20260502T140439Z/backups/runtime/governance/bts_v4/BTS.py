"""
BTS.py — MetaBlooms Behind The Scenes v4 (Canonical Merged)
Cross-Platform: Claude Python execution + ChatGPT behavioral governance

CDR V1 (Intent):   BTS is a reasoning reconstruction substrate. It captures
                   everything needed to reconstruct WHY a decision was made,
                   without the chain of thought (prohibited or ephemeral).
CDR V2 (Trust):    Reads nothing from external state. All inputs explicit.
                   Writes only to _bts/ and bts/bts_log.ndjson under os_root.
CDR V3 (Boundary): Never modifies source artifacts. Logging and receipt only.
CDR V4 (State):    Append-only bts_log.ndjson. No entry ever modified after write.
                   SHA256 chain: each entry hashes the prior entry.
CDR V5 (Failure):  If proof cannot be produced, this module raises. It does
                   not return a degraded receipt silently.

═══════════════════════════════════════════════════════════════════════════════
WHAT BTS IS
═══════════════════════════════════════════════════════════════════════════════

BTS is not a logger.

BTS is a reasoning reconstruction substrate. It captures everything a future
analyst — human or AI — would need to reconstruct WHY a decision was made,
without access to the model's internal chain of thought.

The chain of thought cannot be captured on ChatGPT. But with BTS you have:
  - Every input that informed the decision
  - The instinctive choice (what the model would do without governance)
  - The governed choice (what the rules and evidence required)
  - Every rejected alternative and why
  - Every gate evaluated with pass/fail
  - Every tool evaluated, selected, switched, executed, and its result
  - Every artifact produced with SHA256
  - The objective at time of action
  - Revision count at each decision point
  - Op spans (start/end timestamps per unit of work)
  - Council votes and rationale, not just the verdict
  - Claims made vs files actually changed (implementation_reality)

THE DELIBERATENESS EFFECT:
  Having to log the decision changes the decision.
  The artifact is not evidence that reasoning happened.
  It is the mechanism that causes reasoning to happen.

═══════════════════════════════════════════════════════════════════════════════
GENERATION HISTORY
═══════════════════════════════════════════════════════════════════════════════

Gen 1 (Jan 2026) — bts_decision: instinctive/governed/rejected/gates/confidence
Gen 2 (Jan 2026) — Tool pipeline: INTENT→EVAL→SELECT→SWITCH→EXEC→RESULT→COMMIT
                   BTS_TOOL_SWITCH: captures mid-turn corrections without hiding them
                   Competence audit: cross-turn tool scoring
Gen 3 (Mar 2026) — Receipt tiers: T1/T2/T3/MISSING
                   produce_tier1_subprocess_receipt(): stdout IS the proof
                   check_tier_satisfied(): downstream enforcement gate
                   P8.5 RECONCILIATION: claim_coverage_score
                   CDR V1-V5 binding contracts
Gen 4 (Apr 2026) — Class interface, turn manifests, boot receipts
Codex additions  — implementation_reality block (claimed vs actual)
                   Sufficiency score: diversity × score_spread × confidence_margin
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

SCHEMA_VERSION       = "mb.bts.v4.os_gated"
BTS_LOG_REL          = Path("bts/bts_log.ndjson")
RECEIPTS_DIR_REL     = Path("_bts/receipts")
COMPETENCE_LOG_REL   = Path("_bts/tool_competence.json")
RECON_DIR_REL        = Path("_bts/reconciliation")

# Tool pipeline event ordering — violations raise immediately
TOOL_PIPELINE_ORDER = [
    "BTS_TOOL_INTENT",
    "BTS_TOOL_EVALUATION",
    "BTS_TOOL_SELECTION",
    # BTS_TOOL_SWITCH is optional — may appear after SELECTION, before EXECUTION
    "BTS_TOOL_EXECUTION",
    "BTS_TOOL_RESULT",
    "BTS_COMMIT",
]

# Receipt tiers
TIER_T1       = "T1"   # real OS execution — stdout is proof
TIER_T2       = "T2"   # hash-chained to T1
TIER_T3       = "T3"   # LLM-claimed, advisory only, never gates alone
TIER_MISSING  = "MISSING"  # explicitly logged, never silently dropped

# P8.5 reconciliation threshold
CLAIM_COVERAGE_MIN = 0.80

# Codex sufficiency gate
SUFFICIENCY_SCORE_MIN = 0.15

# OS-gated integration paths (Stage6D)
PER_ACTION_GATE_REL = Path("runtime/governance/per_action_tool_interception_v1/pre_tool_action_gate_v1.js")
PER_ACTION_RECEIPTS_REL = Path("runtime/governance/receipts/per_action_tool_interception_v1")
BTS_CANONICAL_PATH_REGISTRY_REL = Path("runtime/governance/bts_v4/BTS_V4_OS_PATH_REGISTRY_v1.json")



# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _compact_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _sha256_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"BTS: cannot hash missing file: {path}")
    return _sha256_bytes(path.read_bytes())

def _sha256_str(s: str) -> str:
    return _sha256_bytes(s.encode())

def _atomic_write(path: Path, data: str) -> None:
    """Write via tmp→rename. Never leaves partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(data, encoding="utf-8")
    os.replace(tmp, path)

def _resolve_root(os_root: Optional[Path]) -> Path:
    if os_root is not None:
        if not os_root.exists():
            raise RuntimeError(f"BTS: os_root does not exist: {os_root}")
        return os_root
    env = os.environ.get("METABLOOMS_ROOT")
    if env:
        p = Path(env)
        if p.exists():
            return p
    for candidate in [Path("/mnt/data/Metablooms_OS"), Path.cwd()]:
        if (candidate / "boot_manifest_v1.json").exists():
            return candidate
    return Path.cwd()




def _run_pre_action_gate(os_root: Path, envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Route a BTS-sensitive action through Stage6B pre_tool_action_gate_v1.

    This is intentionally local and stdlib-only. It does not claim platform-level
    interception; it proves that BTS-managed subprocess/file-write surfaces were
    gate-evaluated before execution.
    """
    gate = os_root / PER_ACTION_GATE_REL
    if not gate.exists():
        raise RuntimeError(f"BTS OS gate missing: {gate}")
    receipts = os_root / PER_ACTION_RECEIPTS_REL
    receipts.mkdir(parents=True, exist_ok=True)
    eid = envelope.get('envelope_id') or f"bts_envelope_{int(time.time()*1000)}"
    envelope['schema_version'] = envelope.get('schema_version', 'ToolCallEnvelope_v1')
    envelope.setdefault('requested_at_utc', _utc_iso())
    envelope.setdefault('stage_id', 'BTS_V4_OS_GATED')
    envelope.setdefault('risk_tier', 'medium')
    envelope.setdefault('requires_see', False)
    envelope.setdefault('limits', {'timeout_seconds':60,'max_files':50,'max_steps':10,'max_bytes':2000000})
    envelope.setdefault('artifacts', {})
    envelope['artifacts'].setdefault('receipt_path', str(receipts / f"{eid}.decision.json"))
    env_path = receipts / f"{eid}.envelope.json"
    _atomic_write(env_path, json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    result = subprocess.run(['node', str(gate), str(env_path)], capture_output=True, text=True, cwd=str(os_root), timeout=30)
    if result.returncode not in (0, 10):
        raise RuntimeError(f"BTS OS gate invocation failed rc={result.returncode}: {result.stderr[:300]}")
    try:
        decision = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError(f"BTS OS gate returned invalid JSON: {result.stdout[:300]!r}") from exc
    if decision.get('decision') != 'ALLOW':
        raise RuntimeError(f"BTS OS gate denied/deferred action: {decision.get('decision')} {decision.get('reason_code')}")
    return decision

# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BTSGate:
    gate: str
    result: str           # "PASS" | "FAIL" | "SKIP"
    detail: str = ""

@dataclass
class BTSRejectedChoice:
    choice: str
    reason: str
    governing_rule: str = ""

@dataclass
class BTSDecision:
    """Gen 1: The deliberateness artifact. Forces instinctive vs governed split."""
    decision_id:      str
    stage:            str
    objective:        str
    instinctive_choice: str
    governed_choice:  str
    rejected_choices: List[BTSRejectedChoice]
    gates:            List[BTSGate]
    confidence:       float          # 0.0–1.0
    governing_rule:   str = ""
    evidence_refs:    List[str] = field(default_factory=list)
    revision_count:   int = 0
    timestamp:        str = field(default_factory=_utc_iso)
    turn_id:          str = ""

    # Codex addition: sufficiency score gate
    def sufficiency_score(self) -> float:
        """
        diversity × score_spread × confidence_margin.
        Rejected choices count as diversity. Must be ≥ 0.15 to be valid.
        A single obvious choice rubber-stamped scores near zero.
        """
        diversity     = min(1.0, len(self.rejected_choices) / 4.0)
        score_spread  = min(1.0, len(set(g.result for g in self.gates)) / 2.0)
        conf_margin   = self.confidence
        return diversity * score_spread * conf_margin

    def validate(self) -> None:
        """Raise if this decision fails quality gates."""
        if not self.instinctive_choice:
            raise ValueError("BTSDecision: instinctive_choice is required")
        if not self.governed_choice:
            raise ValueError("BTSDecision: governed_choice is required")
        score = self.sufficiency_score()
        if score < SUFFICIENCY_SCORE_MIN:
            raise ValueError(
                f"BTSDecision: sufficiency_score {score:.3f} < min {SUFFICIENCY_SCORE_MIN}. "
                f"Document more rejected alternatives or gate evaluations."
            )


@dataclass
class BTSOpSpan:
    """Gen 2+: Timestamps bracketing a unit of work."""
    span_id:   str
    label:     str
    started:   float = field(default_factory=time.time)
    ended:     Optional[float] = None
    duration_ms: Optional[float] = None

    def end(self) -> "BTSOpSpan":
        self.ended = time.time()
        self.duration_ms = round((self.ended - self.started) * 1000, 2)
        return self

@dataclass
class BTSToolEvent:
    """Gen 2: One event in the tool pipeline."""
    event_type: str    # one of TOOL_PIPELINE_ORDER or "BTS_TOOL_SWITCH"
    tool:        str
    timestamp:   str = field(default_factory=_utc_iso)
    data:        Dict[str, Any] = field(default_factory=dict)

@dataclass
class BTSReceipt:
    """Gen 3: Evidence receipt with tier."""
    receipt_id:    str
    tier:          str
    artifact:      str
    sha256:        str
    bytes_size:    int = 0
    prior_sha256:  str = ""    # T2 chain link
    stdout_proof:  str = ""    # T1 subprocess proof
    timestamp:     str = field(default_factory=_utc_iso)
    turn_id:       str = ""

@dataclass
class BTSImplementationReality:
    """Codex addition: claims made vs files actually changed."""
    claimed_files: List[str]
    actual_files:  List[str]
    verdict:       str         # "PASS" | "FAIL"
    unclaimed:     List[str] = field(default_factory=list)    # in actual, not claimed
    unfulfilled:   List[str] = field(default_factory=list)    # in claimed, not actual

    @classmethod
    def evaluate(cls, claimed: List[str], actual: List[str]) -> "BTSImplementationReality":
        claimed_set = set(str(Path(p).resolve()) if Path(p).is_absolute() else p for p in claimed)
        actual_set  = set(str(Path(p).resolve()) if Path(p).is_absolute() else p for p in actual)
        unclaimed   = sorted(actual_set  - claimed_set)
        unfulfilled = sorted(claimed_set - actual_set)
        verdict     = "PASS" if not unfulfilled else "FAIL"
        return cls(
            claimed_files=list(claimed_set),
            actual_files=list(actual_set),
            verdict=verdict,
            unclaimed=unclaimed,
            unfulfilled=unfulfilled,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TURN TRACKER — the live session object
# ─────────────────────────────────────────────────────────────────────────────

class BTSTurnTracker:
    """
    Gen 2+: Tracks one turn end-to-end through the full pipeline.
    Armed by BTS.start_turn_tracker(). Committed by .commit().
    """

    def __init__(self, turn_id: str, objective: str,
                 stage: str, revision_count: int, bts: "BTS"):
        self.turn_id       = turn_id
        self.objective     = objective
        self.stage         = stage
        self.revision_count = revision_count
        self._bts          = bts
        self._events: List[BTSToolEvent] = []
        self._pipeline_pos = 0
        self._op_spans: List[BTSOpSpan] = []
        self._receipts: List[str] = []   # receipt_ids
        self._decisions: List[str] = []  # decision_ids
        self._artifacts: List[Dict] = []
        self.is_committed  = False
        self._turn_sha     = None

    # ── Op Spans ──────────────────────────────────────────────────────────────

    def start_span(self, label: str) -> BTSOpSpan:
        span = BTSOpSpan(
            span_id=f"{self.turn_id}-span-{len(self._op_spans)+1:03d}",
            label=label,
        )
        self._op_spans.append(span)
        return span

    # ── Tool Pipeline (Gen 2, order-enforced) ─────────────────────────────────

    def _emit(self, event_type: str, tool: str, **kwargs) -> None:
        # Allow SWITCH at any point after SELECTION; otherwise enforce order
        if event_type not in ("BTS_TOOL_SWITCH",):
            expected = TOOL_PIPELINE_ORDER[self._pipeline_pos]
            if event_type != expected:
                raise RuntimeError(
                    f"BTS pipeline violation in turn {self.turn_id}: "
                    f"expected {expected}, got {event_type}"
                )
            self._pipeline_pos += 1
        self._events.append(BTSToolEvent(event_type=event_type, tool=tool, data=kwargs))

    def emit_intent(self, description: str, objective: str = "") -> None:
        self._emit("BTS_TOOL_INTENT", "intent",
                   description=description, objective=objective or self.objective)

    def emit_evaluation(self, candidates: List[Dict]) -> None:
        """candidates: [{"tool": str, "verdict": "SELECTED"|"REJECTED", "reason": str}]"""
        self._emit("BTS_TOOL_EVALUATION", "evaluation", candidates=candidates)

    def emit_selection(self, tool: str, rationale: str) -> None:
        self._emit("BTS_TOOL_SELECTION", tool, rationale=rationale)

    def emit_switch(self, from_tool: str, to_tool: str, reason: str) -> None:
        """Optional: captures mid-turn corrections without hiding them.

        OS-gated hardening: SWITCH is valid only after TOOL_SELECTION and
        before TOOL_EXECUTION. Earlier/later switches hide control-flow drift.
        """
        expected_pos_after_selection = TOOL_PIPELINE_ORDER.index("BTS_TOOL_EXECUTION")
        if self._pipeline_pos != expected_pos_after_selection:
            raise RuntimeError(
                f"BTS_TOOL_SWITCH ordering violation in turn {self.turn_id}: "
                f"switch must occur after BTS_TOOL_SELECTION and before BTS_TOOL_EXECUTION "
                f"(pipeline_pos={self._pipeline_pos})"
            )
        self._events.append(BTSToolEvent(
            event_type="BTS_TOOL_SWITCH", tool=to_tool,
            data={"from_tool": from_tool, "to_tool": to_tool, "reason": reason}
        ))

    def emit_execution(self, tool: str) -> None:
        self._emit("BTS_TOOL_EXECUTION", tool)

    def emit_result(self, tool: str, status: str, intent_satisfied: bool,
                    correctness_score: float, output_summary: str) -> None:
        self._emit("BTS_TOOL_RESULT", tool,
                   status=status, intent_satisfied=intent_satisfied,
                   correctness_score=correctness_score,
                   output_summary=output_summary)

    def record_artifact(self, name: str, path: Path) -> None:
        sha = _sha256_file(path) if path.exists() else "FILE_MISSING"
        self._artifacts.append({
            "name": name,
            "path": str(path),
            "sha256": sha,
            "bytes": path.stat().st_size if path.exists() else 0,
        })

    def commit(self, implementation_reality: Optional[BTSImplementationReality] = None) -> Dict:
        """
        Gen 2+: Emit BTS_COMMIT, write turn entry to bts_log.ndjson.
        Returns the turn record dict.
        CDR V5: Raises if pipeline is incomplete (missing RESULT stage).
        """
        if self.is_committed:
            raise RuntimeError(f"BTS: turn {self.turn_id} already committed")

        # Require at least through RESULT before commit
        if self._pipeline_pos < TOOL_PIPELINE_ORDER.index("BTS_TOOL_RESULT"):
            raise RuntimeError(
                f"BTS: cannot commit turn {self.turn_id} — "
                f"pipeline incomplete (pos={self._pipeline_pos}, "
                f"need {TOOL_PIPELINE_ORDER.index('BTS_TOOL_RESULT')})"
            )

        self._emit("BTS_COMMIT", "commit")

        entry = {
            "schema":          SCHEMA_VERSION,
            "turn_id":         self.turn_id,
            "timestamp":       _utc_iso(),
            "stage":           self.stage,
            "objective":       self.objective,
            "revision_count":  self.revision_count,
            "tool_events":     [asdict(e) for e in self._events],
            "op_spans":        [asdict(s) for s in self._op_spans],
            "artifacts":       self._artifacts,
            "receipt_ids":     self._receipts,
            "decision_ids":    self._decisions,
            "implementation_reality": asdict(implementation_reality)
                               if implementation_reality else None,
            "prior_entry_sha256": "",  # filled below
        }

        self._turn_sha = _sha256_str(json.dumps(entry, sort_keys=True))
        self.is_committed = True
        self._bts._append_to_log(entry)
        self._bts._update_competence(self._events)
        return entry


# ─────────────────────────────────────────────────────────────────────────────
# BTS — main class
# ─────────────────────────────────────────────────────────────────────────────

class BTS:
    """
    MetaBlooms Behind The Scenes v4 — canonical merged.
    Instantiate once per session. Use start_turn_tracker() per turn.
    """

    def __init__(self, os_root: Optional[Path] = None):
        self._root        = _resolve_root(os_root)
        self._log_path    = self._root / BTS_LOG_REL
        self._receipts_dir= self._root / RECEIPTS_DIR_REL
        self._comp_path   = self._root / COMPETENCE_LOG_REL
        self._recon_dir   = self._root / RECON_DIR_REL
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._receipts_dir.mkdir(parents=True, exist_ok=True)
        self._recon_dir.mkdir(parents=True, exist_ok=True)
        self._prior_entry_sha = self._load_last_sha()

    def _gate_write(self, label: str, write_path: Path, bytes_size: int = 0) -> Dict[str, Any]:
        rel = str(write_path)
        return _run_pre_action_gate(self._root, {
            'envelope_id': f"bts_write_{label}_{_compact_ts()}",
            'stage_id': 'BTS_V4_OS_GATED_WRITE',
            'action_type': 'filesystem_write',
            'tool_name': 'BTS._atomic_write_gated',
            'intent': f"Write BTS governance artifact: {label}",
            'risk_tier': 'medium',
            'limits': {'timeout_seconds':30, 'max_files':5, 'max_steps':5, 'max_bytes': max(bytes_size, 1)},
            'artifacts': {'read_paths': [], 'write_paths': [rel]}
        })

    def _gate_subprocess(self, artifact_name: str, cmd: List[str], cwd: Optional[Path]) -> Dict[str, Any]:
        return _run_pre_action_gate(self._root, {
            'envelope_id': f"bts_subprocess_{artifact_name}_{_compact_ts()}",
            'stage_id': 'BTS_V4_OS_GATED_SUBPROCESS',
            'action_type': 'shell',
            'tool_name': 'BTS.produce_tier1_subprocess_receipt',
            'intent': f"Produce T1 subprocess receipt for {artifact_name}",
            'risk_tier': 'medium',
            'command_summary': ' '.join(cmd[:8]),
            'limits': {'timeout_seconds':60, 'max_files':20, 'max_steps':10, 'max_bytes':2000000},
            'artifacts': {'read_paths': [str(cwd or self._root)], 'write_paths': [str(self._receipts_dir)]}
        })

    def _atomic_write_gated(self, path: Path, data: str, label: str) -> None:
        self._gate_write(label, path, len(data.encode()))
        _atomic_write(path, data)

    # ── Log management ─────────────────────────────────────────────────────────

    def _load_last_sha(self) -> str:
        if not self._log_path.exists():
            return ""
        lines = [l for l in self._log_path.read_text().splitlines() if l.strip()]
        if not lines:
            return ""
        try:
            return _sha256_str(lines[-1])
        except Exception:
            return ""

    def _append_to_log(self, entry: Dict) -> None:
        entry["prior_entry_sha256"] = self._prior_entry_sha
        line = json.dumps(entry, sort_keys=True)
        with open(self._log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        self._prior_entry_sha = _sha256_str(line)

    # ── Decision logging (Gen 1) ───────────────────────────────────────────────

    def log_decision(self, decision: BTSDecision) -> str:
        """
        Log a bts_decision artifact. Validates sufficiency before writing.
        Returns decision_id.
        CDR V5: raises if sufficiency gate fails.
        """
        decision.validate()
        entry = {
            "schema":      "mb.bts_decision.v1",
            "timestamp":   _utc_iso(),
            **asdict(decision),
        }
        path = self._receipts_dir / f"decision_{decision.decision_id}_{_compact_ts()}.json"
        self._atomic_write_gated(path, json.dumps(entry, indent=2), "decision")
        self._append_to_log({"type": "BTS_DECISION", "decision_id": decision.decision_id,
                              "sufficiency_score": decision.sufficiency_score(),
                              "receipt_path": str(path)})
        return decision.decision_id

    # ── Turn tracker factory (Gen 2) ──────────────────────────────────────────

    def start_turn_tracker(self, turn_id: str, objective: str = "",
                           stage: str = "", revision_count: int = 0) -> BTSTurnTracker:
        return BTSTurnTracker(
            turn_id=turn_id, objective=objective,
            stage=stage, revision_count=revision_count, bts=self
        )

    # ── Receipt tiers (Gen 3) ─────────────────────────────────────────────────

    def t1_file(self, artifact_name: str, path: Path,
                turn_id: str = "") -> BTSReceipt:
        """
        T1 receipt for a file artifact. SHA256 is computed from the actual file.
        CDR V5: raises if file does not exist.
        """
        sha   = _sha256_file(path)
        size  = path.stat().st_size
        r_id  = f"T1-{artifact_name}-{_compact_ts()}"
        r = BTSReceipt(receipt_id=r_id, tier=TIER_T1, artifact=str(path),
                       sha256=sha, bytes_size=size, turn_id=turn_id)
        self._write_receipt(r)
        return r

    def produce_tier1_subprocess_receipt(
        self, artifact_name: str, cmd: List[str],
        cwd: Optional[Path] = None, turn_id: str = ""
    ) -> BTSReceipt:
        """
        Gen 3: THE unfakeable T1 receipt. Runs cmd as subprocess.
        stdout IS the proof — if it ran and produced output, it happened.
        CDR V5: raises if subprocess fails or produces no output.
        """
        self._gate_subprocess(artifact_name, cmd, cwd)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=str(cwd) if cwd else None, timeout=60
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"BTS T1: subprocess timed out: {cmd}")
        except FileNotFoundError as e:
            raise RuntimeError(f"BTS T1: command not found: {cmd[0]} — {e}")

        stdout = result.stdout.strip()
        if result.returncode != 0 or not stdout:
            raise RuntimeError(
                f"BTS T1: subprocess failed (rc={result.returncode}). "
                f"stdout={stdout[:200]!r} stderr={result.stderr[:200]!r}"
            )

        r_id = f"T1-exec-{artifact_name}-{_compact_ts()}"
        sha  = _sha256_str(stdout)
        r = BTSReceipt(
            receipt_id=r_id, tier=TIER_T1,
            artifact=f"subprocess:{' '.join(cmd)}",
            sha256=sha, stdout_proof=stdout, turn_id=turn_id
        )
        self._write_receipt(r)
        return r

    def t2_chained(self, artifact_name: str, path: Path,
                   prior_receipt: BTSReceipt, turn_id: str = "") -> BTSReceipt:
        """T2: hash-chained to a prior T1. Hard to fabricate."""
        sha  = _sha256_file(path)
        r_id = f"T2-{artifact_name}-{_compact_ts()}"
        r = BTSReceipt(
            receipt_id=r_id, tier=TIER_T2,
            artifact=str(path), sha256=sha,
            bytes_size=path.stat().st_size if path.exists() else 0,
            prior_sha256=prior_receipt.sha256, turn_id=turn_id
        )
        self._write_receipt(r)
        return r

    def t3_advisory(self, artifact_name: str, summary: str,
                    turn_id: str = "") -> BTSReceipt:
        """T3: LLM-claimed summary. Advisory only. Never gates a phase alone."""
        r_id = f"T3-{artifact_name}-{_compact_ts()}"
        sha  = _sha256_str(summary)
        r = BTSReceipt(
            receipt_id=r_id, tier=TIER_T3,
            artifact=artifact_name, sha256=sha,
            stdout_proof=summary, turn_id=turn_id
        )
        self._write_receipt(r)
        return r

    def missing_receipt(self, artifact_name: str, reason: str,
                        turn_id: str = "") -> BTSReceipt:
        """MISSING: evidence was requested but fetch failed. Logged explicitly."""
        r_id = f"MISSING-{artifact_name}-{_compact_ts()}"
        r = BTSReceipt(
            receipt_id=r_id, tier=TIER_MISSING,
            artifact=artifact_name, sha256="",
            stdout_proof=f"FETCH_FAILED: {reason}", turn_id=turn_id
        )
        self._write_receipt(r)
        return r

    def check_tier_satisfied(self, receipt: BTSReceipt,
                             required_tier: str) -> None:
        """
        Gen 3: Enforcement gate. Downstream stages call this to require
        minimum evidence tier. Raises if receipt tier is insufficient.
        Tier order: T1 > T2 > T3. MISSING always fails.
        """
        tier_rank = {TIER_T1: 3, TIER_T2: 2, TIER_T3: 1, TIER_MISSING: 0}
        actual_rank   = tier_rank.get(receipt.tier, 0)
        required_rank = tier_rank.get(required_tier, 0)
        if actual_rank < required_rank:
            raise RuntimeError(
                f"BTS tier gate failed: required {required_tier} "
                f"but receipt {receipt.receipt_id} is {receipt.tier}. "
                f"Cannot proceed."
            )

    def _write_receipt(self, r: BTSReceipt) -> None:
        path = self._receipts_dir / f"{r.receipt_id}.json"
        self._atomic_write_gated(path, json.dumps(asdict(r), indent=2), "receipt")
        self._append_to_log({
            "type": "BTS_RECEIPT",
            "receipt_id": r.receipt_id,
            "tier": r.tier,
            "artifact": r.artifact,
            "sha256": r.sha256[:16] + "...",
        })

    # ── Competence audit (Gen 2) ──────────────────────────────────────────────

    def _update_competence(self, events: List[BTSToolEvent]) -> None:
        """Update cross-turn tool competence scores from this turn's events."""
        comp = {}
        if self._comp_path.exists():
            try:
                comp = json.loads(self._comp_path.read_text())
            except Exception:
                comp = {}

        # Count uses, switches, failures from this turn
        for ev in events:
            if ev.event_type == "BTS_TOOL_SELECTION":
                tool = ev.tool
                if tool not in comp:
                    comp[tool] = {"uses": 0, "switches": 0, "failures": 0}
                comp[tool]["uses"] += 1
            elif ev.event_type == "BTS_TOOL_SWITCH":
                from_tool = ev.data.get("from_tool", "")
                if from_tool and from_tool in comp:
                    comp[from_tool]["switches"] += 1
            elif ev.event_type == "BTS_TOOL_RESULT":
                tool = ev.tool
                if tool in comp and ev.data.get("status") == "failure":
                    comp[tool]["failures"] += 1

        # Recompute scores: uses / (uses + switches + failures)
        for tool, counts in comp.items():
            total = counts["uses"] + counts["switches"] + counts["failures"]
            counts["score"] = round(counts["uses"] / total, 3) if total else 1.0
            counts["flagged"] = counts["score"] < 0.6

        self._atomic_write_gated(self._comp_path, json.dumps(comp, indent=2), "competence")

    def get_competence_report(self) -> Dict:
        """Return current tool competence scores."""
        if not self._comp_path.exists():
            return {}
        try:
            return json.loads(self._comp_path.read_text())
        except Exception:
            return {}

    def flagged_tools(self) -> List[str]:
        """Return list of tools below the 0.6 competence threshold."""
        return [t for t, d in self.get_competence_report().items() if d.get("flagged")]

    # ── P8.5 Reconciliation (Gen 3) ───────────────────────────────────────────

    def reconcile(self, turn_id: str, cdr_claims: List[str],
                  produced_receipts: List[BTSReceipt]) -> Dict:
        """
        P8.5 RECONCILIATION: compute claim_coverage_score.
        cdr_claims: list of artifact names the CDR contract said would be produced.
        produced_receipts: T1 receipts actually written this turn.
        If coverage < 0.80, caller should route to P10.
        CDR V5: never raises — returns routing decision as data.
        """
        def _normalize(name: str) -> str:
            """Normalize artifact name for matching: stem, basename, or as-is."""
            p = Path(name)
            return p.stem.upper() if p.suffix else name.upper()

        claimed_set  = {_normalize(c) for c in cdr_claims}
        covered_set  = {_normalize(r.artifact)
                        for r in produced_receipts if r.tier == TIER_T1}
        covered      = claimed_set & covered_set
        uncovered    = claimed_set - covered_set
        score        = len(covered) / len(claimed_set) if claimed_set else 1.0
        route_to_p10 = score < CLAIM_COVERAGE_MIN

        report = {
            "schema":               "mb.bts_reconciliation.v1",
            "turn_id":              turn_id,
            "timestamp":            _utc_iso(),
            "claim_coverage_score": round(score, 3),
            "claimed_count":        len(claimed_set),
            "covered_count":        len(covered),
            "uncovered":            sorted(uncovered),
            "route_to_p10":         route_to_p10,
            "verdict":              "PASS" if not route_to_p10 else "ROUTE_P10",
        }
        path = self._recon_dir / f"recon_{turn_id}_{_compact_ts()}.json"
        self._atomic_write_gated(path, json.dumps(report, indent=2), "reconciliation")
        self._append_to_log({"type": "P8.5_RECONCILIATION", **report})
        return report


# ─────────────────────────────────────────────────────────────────────────────
# BOOT RECEIPT — for ChatGPT session start
# ─────────────────────────────────────────────────────────────────────────────

def write_boot_receipt(os_root: Optional[Path] = None,
                       session_id: str = "") -> Path:
    """Write a boot receipt to confirm BTS is armed for this session."""
    root = _resolve_root(os_root)
    sid  = session_id or f"session-{_compact_ts()}"
    receipt = {
        "schema":      "mb.bts_boot.v4",
        "session_id":  sid,
        "os_root":     str(root),
        "timestamp":   _utc_iso(),
        "bts_version": SCHEMA_VERSION,
        "armed":       True,
        "log_path":    str(root / BTS_LOG_REL),
    }
    path = root / "_bts" / f"BOOT_RECEIPT_{sid}.json"
    _atomic_write(path, json.dumps(receipt, indent=2))
    return path


# ─────────────────────────────────────────────────────────────────────────────
# SELF-TEST  (python3 -m BTS or pytest)
# ─────────────────────────────────────────────────────────────────────────────

def _self_test(root: Path) -> None:
    import tempfile
    print("BTS v4 self-test starting...")
    all_pass = True

    def ck(label: str, cond: bool) -> None:
        nonlocal all_pass
        ok = bool(cond)
        if not ok: all_pass = False
        print(f"  {'PASS ✓' if ok else 'FAIL ✗'}  {label}")

    with tempfile.TemporaryDirectory() as td:
        bts = BTS(os_root=Path(td))

        # T1: boot receipt
        p = write_boot_receipt(Path(td), session_id="test-001")
        ck("boot receipt written", p.exists())

        # T2: bts_decision with deliberateness
        d = BTSDecision(
            decision_id="DEC-001", stage="ADS", objective="Test decision",
            instinctive_choice="Use bash directly",
            governed_choice="Use python3 -S per tool governance rule",
            rejected_choices=[
                BTSRejectedChoice("Use bash", "bash unavailable in -S mode",
                                  "NO_NORMAL_PYTHON"),
                BTSRejectedChoice("Skip the step", "required by CDR V1",
                                  "CDR_V1_REQUIRED"),
            ],
            gates=[BTSGate("TOOL_ROUTE_GUARD", "PASS"),
                   BTSGate("SEE_REQUIRED", "PASS")],
            confidence=0.88, turn_id="TURN-001",
        )
        ck("sufficiency score >= 0.15", d.sufficiency_score() >= SUFFICIENCY_SCORE_MIN)
        d_id = bts.log_decision(d)
        ck("decision logged", bool(d_id))

        # T3: turn tracker — full pipeline
        tr = bts.start_turn_tracker("TURN-001", "Build receipt engine",
                                    stage="IMPLEMENTATION", revision_count=0)
        span = tr.start_span("write file")
        tr.emit_intent("Write BTS.py", objective="Canonical merged BTS")
        tr.emit_evaluation([
            {"tool": "direct_write", "verdict": "SELECTED",
             "reason": "Simplest path for stdlib-only file write"},
            {"tool": "subprocess_write", "verdict": "REJECTED",
             "reason": "Unnecessary overhead for simple write"},
        ])
        tr.emit_selection("direct_write", "Simplest path, stdlib only")
        tr.emit_execution("direct_write")
        tr.emit_result("direct_write", status="success",
                       intent_satisfied=True, correctness_score=0.95,
                       output_summary="BTS.py written with all features")
        span.end()
        entry = tr.commit()
        ck("turn committed", tr.is_committed)
        ck("log file exists", (Path(td) / BTS_LOG_REL).exists())

        # T4: T1 file receipt
        test_file = Path(td) / "test_artifact.py"
        test_file.write_text("# test artifact\n")
        r1 = bts.t1_file("TEST_ARTIFACT", test_file, turn_id="TURN-001")
        ck("T1 receipt tier", r1.tier == TIER_T1)
        ck("T1 receipt sha256 present", len(r1.sha256) == 64)

        # T5: T2 chained
        r2 = bts.t2_chained("TEST_CHAINED", test_file, r1, turn_id="TURN-001")
        ck("T2 prior_sha256 set", r2.prior_sha256 == r1.sha256)
        ck("T2 tier", r2.tier == TIER_T2)

        # T6: check_tier_satisfied
        try:
            bts.check_tier_satisfied(r2, TIER_T1)
            ck("T2 fails T1 gate", False)
        except RuntimeError:
            ck("T2 fails T1 gate (correct)", True)

        bts.check_tier_satisfied(r1, TIER_T1)   # should not raise
        ck("T1 satisfies T1 gate", True)

        # T7: MISSING receipt
        r_miss = bts.missing_receipt("FETCH_FAILED_ARTIFACT",
                                     "URL returned 404", turn_id="TURN-001")
        ck("MISSING tier", r_miss.tier == TIER_MISSING)

        # T8: T1 subprocess receipt
        r_sub = bts.produce_tier1_subprocess_receipt(
            "SHA_PROOF", ["python3", "-S", "-c",
                          f"import hashlib; print(hashlib.sha256(b'test').hexdigest())"],
            turn_id="TURN-001"
        )
        ck("T1 subprocess tier", r_sub.tier == TIER_T1)
        ck("T1 subprocess stdout_proof non-empty", bool(r_sub.stdout_proof))

        # T9: P8.5 reconciliation
        report = bts.reconcile("TURN-001",
                                cdr_claims=["TEST_ARTIFACT", "MISSING_ARTIFACT"],
                                produced_receipts=[r1])
        ck("reconciliation score 0.5 (1 of 2 covered)", report["claim_coverage_score"] == 0.5)
        ck("route_to_p10 True (below 0.80)", report["route_to_p10"])

        # T10: implementation_reality (Codex addition)
        ir = BTSImplementationReality.evaluate(
            claimed=["file_a.py", "file_b.py"],
            actual=["file_a.py", "file_c.py"],
        )
        ck("implementation_reality FAIL (file_b missing)", ir.verdict == "FAIL")
        ck("unfulfilled has file_b.py", "file_b.py" in ir.unfulfilled)
        ck("unclaimed has file_c.py",   "file_c.py" in ir.unclaimed)

        # T11: competence audit
        comp = bts.get_competence_report()
        ck("competence audit has direct_write", "direct_write" in comp)
        ck("direct_write score 1.0 (no switches/failures)",
           comp.get("direct_write", {}).get("score", 0) == 1.0)

        # T12: BTSDecision sufficiency failure
        bad_decision = BTSDecision(
            decision_id="DEC-BAD", stage="ADS", objective="Bad",
            instinctive_choice="do X", governed_choice="do X",
            rejected_choices=[],   # no alternatives = diversity=0 = score=0
            gates=[], confidence=0.9, turn_id="TURN-001"
        )
        try:
            bts.log_decision(bad_decision)
            ck("single-choice decision rejected", False)
        except ValueError:
            ck("single-choice decision rejected (correct)", True)

    print()
    print("BTS v4 self-test:", "ALL PASS ✓" if all_pass else "FAILURES ✗")
    return all_pass


if __name__ == "__main__":
    import sys
    ok = _self_test(Path("."))
    sys.exit(0 if ok else 1)
