#!/usr/bin/env python3
### GOVERNANCE HEADER
# artifact_id: autonomous_sidecar_generator_v1
# purpose: Standalone autonomous sidecar bundle generator. Fires when any
#          trigger class crosses threshold. Packages evidence, README, and
#          SHA-indexed index — never attempts repair, only surfaces.
#          Implements AMEND-0006 of GOVERNED_RECURSIVE_SEE_CE_WORKFLOW_v6.
# mutation_scope: sidecar_only (/mnt/data/workflow_sidecars/ writes only)
# invariants_enforced:
#   - Never modifies OS tree — writes to workflow_sidecars/ only
#   - Every sidecar has: README, TRIGGER_EVIDENCE, governance artifacts, SIDECAR_INDEX with SHA
#   - Blocked sidecar writes produce SIDECAR_BLOCKED_RECEIPT instead of failing silently
#   - All 5 trigger classes handled: IC_FAILURE, TOOL_FAILURE, SEE_GAP, AMENDMENT_CANDIDATE, SUCCESS_PATTERN
#   - Threshold is configurable per trigger class (default: 2)
#   - Evidence is immutable once written — append-only via JSONL ledger
# risk_level: governance-layer
# see_evidence:
#   - "Each incident becomes a learning opportunity — patterns stored in knowledge repositories"
#   - "Promote successful patterns into reusable playbooks that next projects can inherit"
#   - "Self-healing risk: a loop that runs until the system is wide open — sidecar generator stops after packaging, never repairs"
###

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import sys
KERNEL = Path(__file__).resolve().parents[1]
if str(KERNEL) not in sys.path:
    sys.path.insert(0, str(KERNEL))
from lib.io.atomic_append_log_compat_v1 import append_jsonl_record

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
VERSION = "1.0"
AMENDMENT = "AMEND-0006"
WORKFLOW_VERSION = "v6"

DEFAULT_SIDECAR_DIR = Path("/mnt/data/workflow_sidecars")
DEFAULT_LEDGER = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/SIDECAR_GENERATION_LEDGER_v1.jsonl")

DEFAULT_THRESHOLDS = {
    "IC_FAILURE":          2,
    "TOOL_FAILURE":        2,
    "SEE_GAP":             2,
    "AMENDMENT_CANDIDATE": 1,   # every proposed amendment gets a sidecar
    "SUCCESS_PATTERN":     1,   # every promoted pattern gets a sidecar
}


# ─────────────────────────────────────────────────────────────────────────────
# TRIGGER CLASSES
# ─────────────────────────────────────────────────────────────────────────────

class TriggerClass(str, Enum):
    IC_FAILURE          = "IC_FAILURE"          # IC-1→IC-6 repeat triggers
    TOOL_FAILURE        = "TOOL_FAILURE"        # canmore, timeout, routing failure
    SEE_GAP             = "SEE_GAP"             # SEE returned 0 results 2+ times
    AMENDMENT_CANDIDATE = "AMENDMENT_CANDIDATE" # W3 produced an amendment proposal
    SUCCESS_PATTERN     = "SUCCESS_PATTERN"     # W5 promoted a success pattern


TRIGGER_DESCRIPTIONS = {
    TriggerClass.IC_FAILURE: (
        "IC interrupt condition fired on 2+ artifacts in the same chunk. "
        "This sidecar packages the trigger evidence for review and potential amendment."
    ),
    TriggerClass.TOOL_FAILURE: (
        "Same tool routing failure class occurred 2+ times. "
        "This sidecar documents the failure mode and fallback router state."
    ),
    TriggerClass.SEE_GAP: (
        "SEE search returned 0 relevant results 2+ times for the same topic. "
        "This sidecar documents the gap for future query refinement."
    ),
    TriggerClass.AMENDMENT_CANDIDATE: (
        "W3 (Study) phase produced an amendment candidate (AMEND-XXXX). "
        "This sidecar bundles the candidate for review before promotion to WORKFLOW_AMENDMENT_LEDGER."
    ),
    TriggerClass.SUCCESS_PATTERN: (
        "W5 (Promote) phase identified a new success pattern. "
        "This sidecar bundles the pattern for promotion to SUCCESS_PATTERN_REGISTRY."
    ),
}

RECOMMENDED_ACTIONS = {
    TriggerClass.IC_FAILURE: (
        "1. Review trigger instances in TRIGGER_EVIDENCE_v1.json. "
        "2. Determine if this is systemic (→ amendment) or one-off (→ document and close). "
        "3. If systemic, reference this sidecar in the amendment proposal."
    ),
    TriggerClass.TOOL_FAILURE: (
        "1. Review failure instances in TRIGGER_EVIDENCE_v1.json. "
        "2. Update METABLOOMS_TOOL_FAILURE_AND_FALLBACK_ROUTER_v1.json with new fallback rule. "
        "3. Verify P-1 TOOL_ROUTE_GUARD catches this class in future stages."
    ),
    TriggerClass.SEE_GAP: (
        "1. Review failed search queries in TRIGGER_EVIDENCE_v1.json. "
        "2. Refine query strategy — add synonyms, broaden scope, or split into sub-queries. "
        "3. If gap is structural (topic not indexable), label affected claims T4-TRAINING-ONLY."
    ),
    TriggerClass.AMENDMENT_CANDIDATE: (
        "1. Review AMENDMENT_PROPOSAL.json in this sidecar. "
        "2. Validate against existing amendments in WORKFLOW_AMENDMENT_LEDGER_v5.json. "
        "3. If approved, add to ledger and update regression checklist."
    ),
    TriggerClass.SUCCESS_PATTERN: (
        "1. Review SUCCESS_PATTERN_PROPOSAL.json in this sidecar. "
        "2. Validate evidence source and reuse_rule. "
        "3. If approved, add to SUCCESS_PATTERN_REGISTRY and reference in regression checklist."
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TriggerInstance:
    """A single occurrence that contributed to the threshold being crossed."""
    artifact_id: str
    stage_name: str
    condition_or_subclass: str     # e.g. "IC-2", "canmore", "web_search_empty"
    evidence: str
    timestamp: float = field(default_factory=time.time)
    receipt_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "stage_name": self.stage_name,
            "condition_or_subclass": self.condition_or_subclass,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
            "receipt_id": self.receipt_id,
        }


@dataclass
class SidecarRequest:
    """All inputs needed to generate one sidecar bundle."""
    trigger_class: TriggerClass
    stage_name: str
    chunk_id: str
    instances: List[TriggerInstance]
    governance_artifacts: Dict[str, Any] = field(default_factory=dict)
    amendment_proposal: Optional[Dict[str, Any]] = None
    success_pattern_proposal: Optional[Dict[str, Any]] = None
    extra_context: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, data: Dict[str, Any]) -> str:
    """Write JSON atomically and return SHA256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    _mb_write_json_file(tmp, data, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_autonomous_sidecar_generator_v1_py_L174', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    os.replace(tmp, path)
    return sha256_file(path)


def write_jsonl_append(path: Path, record: Dict[str, Any]):
    """Append a record to a JSONL file."""
    append_jsonl_record(path, record, operation_id="autonomous_sidecar_generator_append", source="autonomous_sidecar_generator_v1", event_type="sidecar_ledger_append", severity="info", allowed_roots=["/mnt/data"], durability_mode="sync_on_critical")


def sidecar_name_for(trigger_class: TriggerClass, subclass: str = "") -> str:
    ts = int(time.time() * 1000)
    sub = f"_{subclass.upper().replace('-','_').replace(' ','_')}" if subclass else ""
    return f"{trigger_class.value}{sub}_SIDECAR_{ts}"


# ─────────────────────────────────────────────────────────────────────────────
# SIDECAR GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_sidecar(
    request: SidecarRequest,
    sidecar_dir: Path,
    ledger_path: Path,
) -> Dict[str, Any]:
    """
    Generate a sidecar bundle for a given trigger request.
    Returns summary dict with sidecar_id, path, index_sha, files.
    Never raises — returns blocked receipt on failure.
    """
    # Determine subclass from first instance
    subclass = request.instances[0].condition_or_subclass if request.instances else ""
    sidecar_id = sidecar_name_for(request.trigger_class, subclass)
    bundle_path = sidecar_dir / sidecar_id
    files: List[Dict[str, str]] = []

    try:
        bundle_path.mkdir(parents=True, exist_ok=True)

        # ── 1. README ──────────────────────────────────────────────────────
        readme = {
            "sidecar_id": sidecar_id,
            "trigger_class": request.trigger_class.value,
            "subclass": subclass,
            "stage_name": request.stage_name,
            "chunk_id": request.chunk_id,
            "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "amendment": AMENDMENT,
            "workflow_version": WORKFLOW_VERSION,
            "description": TRIGGER_DESCRIPTIONS[request.trigger_class],
            "instance_count": len(request.instances),
            "recommended_action": RECOMMENDED_ACTIONS[request.trigger_class],
            "must_stop_execution": False,   # sidecar surfaces, never blocks
            "auto_generated": True,
        }
        readme_path = bundle_path / "README.json"
        readme_sha = write_json_atomic(readme_path, readme)
        files.append({"file": "README.json", "sha256": readme_sha})
        print(f"    [SIDECAR] README written")

        # ── 2. TRIGGER_EVIDENCE ────────────────────────────────────────────
        evidence = {
            "trigger_class": request.trigger_class.value,
            "chunk_id": request.chunk_id,
            "stage_name": request.stage_name,
            "instances": [i.to_dict() for i in request.instances],
            "threshold_crossed": len(request.instances) >= DEFAULT_THRESHOLDS.get(request.trigger_class.value, 2),
            "extra_context": request.extra_context,
        }
        evidence_path = bundle_path / "TRIGGER_EVIDENCE_v1.json"
        evidence_sha = write_json_atomic(evidence_path, evidence)
        files.append({"file": "TRIGGER_EVIDENCE_v1.json", "sha256": evidence_sha})
        print(f"    [SIDECAR] Trigger evidence written ({len(request.instances)} instances)")

        # ── 3. Governance artifacts (passthrough if provided) ──────────────
        for artifact_name, artifact_data in request.governance_artifacts.items():
            ga_path = bundle_path / artifact_name
            if isinstance(artifact_data, dict):
                ga_sha = write_json_atomic(ga_path, artifact_data)
            else:
                ga_path.write_text(str(artifact_data), encoding="utf-8")
                ga_sha = sha256_file(ga_path)
            files.append({"file": artifact_name, "sha256": ga_sha})

        # ── 4. Amendment proposal (if provided) ───────────────────────────
        if request.amendment_proposal:
            prop_path = bundle_path / "AMENDMENT_PROPOSAL.json"
            prop_sha = write_json_atomic(prop_path, request.amendment_proposal)
            files.append({"file": "AMENDMENT_PROPOSAL.json", "sha256": prop_sha})
            print(f"    [SIDECAR] Amendment proposal included")

        # ── 5. Success pattern proposal (if provided) ─────────────────────
        if request.success_pattern_proposal:
            sp_path = bundle_path / "SUCCESS_PATTERN_PROPOSAL.json"
            sp_sha = write_json_atomic(sp_path, request.success_pattern_proposal)
            files.append({"file": "SUCCESS_PATTERN_PROPOSAL.json", "sha256": sp_sha})
            print(f"    [SIDECAR] Success pattern proposal included")

        # ── 6. SIDECAR_INDEX ──────────────────────────────────────────────
        index = {
            "sidecar_id": sidecar_id,
            "trigger_class": request.trigger_class.value,
            "generated_utc": readme["generated_utc"],
            "files": files,
            "total_files": len(files),
        }
        index_path = bundle_path / "SIDECAR_INDEX_v1.json"
        index_sha = write_json_atomic(index_path, index)
        print(f"    [SIDECAR] Index written — {len(files)} files  SHA: {index_sha[:16]}...")

        # ── 7. Append to generation ledger ────────────────────────────────
        ledger_entry = {
            "sidecar_id": sidecar_id,
            "trigger_class": request.trigger_class.value,
            "stage_name": request.stage_name,
            "instance_count": len(request.instances),
            "path": str(bundle_path),
            "index_sha": index_sha,
            "ts": time.time(),
        }
        write_jsonl_append(ledger_path, ledger_entry)

        print(f"  [SIDECAR GENERATED] {sidecar_id}")
        return {
            "verdict": "GENERATED",
            "sidecar_id": sidecar_id,
            "path": str(bundle_path),
            "index_sha": index_sha,
            "files": files,
            "trigger_class": request.trigger_class.value,
        }

    except Exception as e:
        # Write blocked receipt — never raise
        blocked = {
            "receipt_type": "SIDECAR_BLOCKED_RECEIPT",
            "sidecar_id": sidecar_id,
            "trigger_class": request.trigger_class.value,
            "stage_name": request.stage_name,
            "created_at": time.time(),
            "error": str(e),
            "must_stop": False,  # blocked sidecar does NOT stop execution
        }
        blocked_path = sidecar_dir / f"SIDECAR_BLOCKED_{sidecar_id}.json"
        try:
            sidecar_dir.mkdir(parents=True, exist_ok=True)
            write_json_atomic(blocked_path, blocked)
        except Exception:
            pass
        print(f"  [SIDECAR BLOCKED] {sidecar_id}: {e}")
        return {
            "verdict": "BLOCKED",
            "sidecar_id": sidecar_id,
            "error": str(e),
            "blocked_receipt": str(blocked_path),
        }


# ─────────────────────────────────────────────────────────────────────────────
# THRESHOLD MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class ThresholdManager:
    """
    Tracks trigger instances per class per chunk.
    Fires sidecar generation when threshold is crossed.
    Resets per-chunk on new_chunk().
    """

    def __init__(
        self,
        sidecar_dir: Path = DEFAULT_SIDECAR_DIR,
        ledger_path: Path = DEFAULT_LEDGER,
        thresholds: Optional[Dict[str, int]] = None,
    ):
        self.sidecar_dir = sidecar_dir
        self.ledger_path = ledger_path
        self.thresholds = thresholds or DEFAULT_THRESHOLDS.copy()
        self._instances: Dict[str, List[TriggerInstance]] = {}
        self._fired: set = set()
        self._chunk_id: str = "GLOBAL"
        self._stage_name: str = "UNKNOWN"

    def new_chunk(self, chunk_id: str, stage_name: str):
        self._chunk_id = chunk_id
        self._stage_name = stage_name
        self._instances = {}
        self._fired = set()

    def record(
        self,
        trigger_class: TriggerClass,
        artifact_id: str,
        condition_or_subclass: str,
        evidence: str,
        receipt_id: Optional[str] = None,
        governance_artifacts: Optional[Dict] = None,
        amendment_proposal: Optional[Dict] = None,
        success_pattern_proposal: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record a trigger instance.
        Returns sidecar result if threshold crossed, else None.
        """
        key = f"{trigger_class.value}:{condition_or_subclass}"
        self._instances.setdefault(key, [])
        self._instances[key].append(TriggerInstance(
            artifact_id=artifact_id,
            stage_name=self._stage_name,
            condition_or_subclass=condition_or_subclass,
            evidence=evidence,
            receipt_id=receipt_id,
        ))

        threshold = self.thresholds.get(trigger_class.value, 2)
        count = len(self._instances[key])

        print(f"  [THRESHOLD] {key}: {count}/{threshold}")

        # Fire once per key per chunk
        if count >= threshold and key not in self._fired:
            self._fired.add(key)
            print(f"  [THRESHOLD CROSSED] Generating sidecar for {key}")
            request = SidecarRequest(
                trigger_class=trigger_class,
                stage_name=self._stage_name,
                chunk_id=self._chunk_id,
                instances=self._instances[key].copy(),
                governance_artifacts=governance_artifacts or {},
                amendment_proposal=amendment_proposal,
                success_pattern_proposal=success_pattern_proposal,
            )
            return generate_sidecar(request, self.sidecar_dir, self.ledger_path)

        return None

    def force_generate(
        self,
        trigger_class: TriggerClass,
        instances: List[TriggerInstance],
        governance_artifacts: Optional[Dict] = None,
        amendment_proposal: Optional[Dict] = None,
        success_pattern_proposal: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Force-generate a sidecar regardless of threshold.
        Used for AMENDMENT_CANDIDATE and SUCCESS_PATTERN (threshold=1).
        """
        request = SidecarRequest(
            trigger_class=trigger_class,
            stage_name=self._stage_name,
            chunk_id=self._chunk_id,
            instances=instances,
            governance_artifacts=governance_artifacts or {},
            amendment_proposal=amendment_proposal,
            success_pattern_proposal=success_pattern_proposal,
        )
        return generate_sidecar(request, self.sidecar_dir, self.ledger_path)


# ─────────────────────────────────────────────────────────────────────────────
# LEDGER QUERY
# ─────────────────────────────────────────────────────────────────────────────

def query_sidecar_ledger(
    ledger_path: Path,
    trigger_class: Optional[str] = None,
    stage_name: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Query the sidecar generation ledger."""
    if not ledger_path.exists():
        return []
    results = []
    for line in ledger_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if trigger_class and entry.get("trigger_class") != trigger_class:
            continue
        if stage_name and entry.get("stage_name") != stage_name:
            continue
        results.append(entry)
        if len(results) >= limit:
            break
    return results


def sidecar_ledger_summary(ledger_path: Path) -> Dict[str, Any]:
    """Aggregate sidecar generation stats."""
    if not ledger_path.exists():
        return {"total": 0, "by_class": {}}
    total = 0
    by_class: Dict[str, int] = {}
    for line in ledger_path.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        cls = e.get("trigger_class", "UNKNOWN")
        by_class[cls] = by_class.get(cls, 0) + 1
    return {"total": total, "by_class": by_class}


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MetaBlooms Autonomous Sidecar Generator v1 — AMEND-0006"
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # generate
    gen = sub.add_parser("generate", help="Generate a sidecar for a trigger class")
    gen.add_argument("--trigger-class", required=True,
                     choices=[c.value for c in TriggerClass])
    gen.add_argument("--stage-name",  required=True)
    gen.add_argument("--chunk-id",    required=True)
    gen.add_argument("--instances",   required=True,
                     help="Path to JSON file with list of trigger instances")
    gen.add_argument("--governance-artifacts", default=None,
                     help="Path to JSON file with governance artifacts to include")
    gen.add_argument("--amendment-proposal",   default=None,
                     help="Path to JSON file with amendment proposal")
    gen.add_argument("--success-pattern",      default=None,
                     help="Path to JSON file with success pattern proposal")
    gen.add_argument("--sidecar-dir",  default=str(DEFAULT_SIDECAR_DIR))
    gen.add_argument("--ledger",       default=str(DEFAULT_LEDGER))
    gen.add_argument("--json-output",  action="store_true")

    # record (threshold-tracked)
    rec = sub.add_parser("record", help="Record a trigger instance and generate if threshold crossed")
    rec.add_argument("--trigger-class",  required=True, choices=[c.value for c in TriggerClass])
    rec.add_argument("--artifact-id",    required=True)
    rec.add_argument("--stage-name",     required=True)
    rec.add_argument("--chunk-id",       required=True)
    rec.add_argument("--condition",      required=True)
    rec.add_argument("--evidence",       required=True)
    rec.add_argument("--receipt-id",     default=None)
    rec.add_argument("--sidecar-dir",    default=str(DEFAULT_SIDECAR_DIR))
    rec.add_argument("--ledger",         default=str(DEFAULT_LEDGER))

    # ledger summary
    summ = sub.add_parser("summary", help="Print sidecar ledger summary")
    summ.add_argument("--ledger", default=str(DEFAULT_LEDGER))

    # query
    qry = sub.add_parser("query", help="Query sidecar ledger")
    qry.add_argument("--ledger",        default=str(DEFAULT_LEDGER))
    qry.add_argument("--trigger-class", default=None)
    qry.add_argument("--stage-name",    default=None)
    qry.add_argument("--limit",         type=int, default=10)

    args = ap.parse_args(argv)
    import sys

    if args.command == "generate":
        instances_data = json.loads(Path(args.instances).read_text())
        instances = [TriggerInstance(**i) for i in instances_data]
        governance_artifacts = {}
        if args.governance_artifacts:
            governance_artifacts = json.loads(Path(args.governance_artifacts).read_text())
        amendment_proposal = None
        if args.amendment_proposal:
            amendment_proposal = json.loads(Path(args.amendment_proposal).read_text())
        success_pattern = None
        if args.success_pattern:
            success_pattern = json.loads(Path(args.success_pattern).read_text())

        request = SidecarRequest(
            trigger_class=TriggerClass(args.trigger_class),
            stage_name=args.stage_name,
            chunk_id=args.chunk_id,
            instances=instances,
            governance_artifacts=governance_artifacts,
            amendment_proposal=amendment_proposal,
            success_pattern_proposal=success_pattern,
        )
        result = generate_sidecar(request, Path(args.sidecar_dir), Path(args.ledger))
        if args.json_output:
            print(json.dumps(result, indent=2))
        sys.exit(0 if result["verdict"] == "GENERATED" else 1)

    elif args.command == "record":
        tm = ThresholdManager(Path(args.sidecar_dir), Path(args.ledger))
        tm.new_chunk(args.chunk_id, args.stage_name)
        result = tm.record(
            trigger_class=TriggerClass(args.trigger_class),
            artifact_id=args.artifact_id,
            condition_or_subclass=args.condition,
            evidence=args.evidence,
            receipt_id=args.receipt_id,
        )
        if result:
            print(json.dumps(result, indent=2))
            sys.exit(0 if result["verdict"] == "GENERATED" else 1)
        sys.exit(0)

    elif args.command == "summary":
        s = sidecar_ledger_summary(Path(args.ledger))
        print(json.dumps(s, indent=2))
        sys.exit(0)

    elif args.command == "query":
        entries = query_sidecar_ledger(
            Path(args.ledger),
            trigger_class=args.trigger_class,
            stage_name=args.stage_name,
            limit=args.limit,
        )
        for e in entries:
            print(json.dumps(e))
        sys.exit(0)


if __name__ == "__main__":
    main()
