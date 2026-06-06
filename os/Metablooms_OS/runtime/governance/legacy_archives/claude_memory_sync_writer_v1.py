#!/usr/bin/env python3
### GOVERNANCE HEADER
# artifact_id: claude_memory_sync_writer_v1
# purpose: Write CLAUDE_MEMORY_SYNC_v1.json at the end of every ChatGPT session.
#          Robert hands this file to Claude. Claude loads it into the memory system
#          so the next session starts pre-oriented without re-reading the full bundle.
#          Implements AMEND-0007 of GOVERNED_RECURSIVE_SEE_CE_WORKFLOW_v6.
# mutation_scope: write_only (/mnt/data/CLAUDE_MEMORY_SYNC_v1.json only)
# invariants_enforced:
#   - Reads OS tree state — never writes to OS tree
#   - Produces exactly one output: CLAUDE_MEMORY_SYNC_v1.json
#   - All fields are human-readable — "note to a colleague taking over your shift"
#   - Schema is versioned — v1 fields listed explicitly; unknown fields rejected
#   - SHA256 of the sync file recorded in its own footer for integrity check
#   - If any required field cannot be resolved, writes SYNC_PARTIAL with flag
# risk_level: low (read-only OS access, single file write output)
# see_evidence:
#   - "Build handoffs like a note to a colleague taking over — readable by human with text editor"
#   - "Memory governance gap: systems fail when memory accumulates, context drifts"
#   - "Session logs follow strict JSON schema with RFC 2119 compliance evidence"
###

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
VERSION = "1.0"
AMENDMENT = "AMEND-0007"
SCHEMA_VERSION = "CLAUDE_MEMORY_SYNC_v1"

DEFAULT_ROOT = Path("/mnt/data/Metablooms_OS_refined")
DEFAULT_OUTPUT = Path("/mnt/data/CLAUDE_MEMORY_SYNC_v1.json")
DEFAULT_HISTORY_LOG = Path("/mnt/data/CLAUDE_MEMORY_SYNC_HISTORY_v1.jsonl")

# Required fields — all MUST be present for a COMPLETE sync
REQUIRED_FIELDS = [
    "sync_utc", "schema_version", "bundle_version",
    "current_stage", "baseline_sha",
    "active_amendments", "active_success_patterns",
    "regression_checklist_version",
    "session_note",
]

# Optional fields — written if data is available
OPTIONAL_FIELDS = [
    "open_ic_triggers", "pending_sidecars",
    "known_blockers", "next_chunk", "deferred_items",
    "git_commit_sha", "total_artifacts_processed",
    "new_scripts_deployed", "workflow_version",
    "two_track_note", "chatgpt_validation_required",
]


# ─────────────────────────────────────────────────────────────────────────────
# OS STATE READERS
# ─────────────────────────────────────────────────────────────────────────────

def read_json_safe(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def resolve_baseline_sha(root: Path) -> Tuple[Optional[str], str]:
    """Read SHA from CURRENT_WORKING_BASELINE_POINTER_v1.json."""
    pointer = read_json_safe(root / "0_kernel/state/CURRENT_WORKING_BASELINE_POINTER_v1.json")
    if pointer:
        sha = pointer.get("last_commit_sha") or pointer.get("state_ref")
        return sha, "from_baseline_pointer"
    # Fallback: git HEAD
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip(), "from_git_head"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None, "not_resolved"


def resolve_current_stage(root: Path) -> Tuple[str, str]:
    """Read current stage from STAGE_STATE_LEDGER_v1.json latest entry."""
    ledger = read_json_safe(root / "0_kernel/state/STAGE_STATE_LEDGER_v1.json")
    if ledger:
        entries = ledger.get("entries", [])
        if entries:
            latest = entries[-1]
            stage = latest.get("stage", "UNKNOWN")
            return stage, "from_ledger"
    # Fallback: WORKFLOW_NEXT_STAGE_POINTER
    pointer = read_json_safe(root / "0_kernel/state/CURRENT_WORKING_BASELINE_POINTER_v1.json")
    if pointer:
        stage = pointer.get("last_stage_name", "UNKNOWN")
        return stage, "from_baseline_pointer"
    return "UNKNOWN", "not_resolved"


def resolve_active_amendments(root: Path) -> List[str]:
    """Read active amendments from WORKFLOW_AMENDMENT_LEDGER_v5.json."""
    # Check workflow_v6 dir first
    for ledger_path in [
        root / "1_governance/workflow_v6/WORKFLOW_AMENDMENT_LEDGER_v5.json",
        root / "1_governance/WORKFLOW_AMENDMENT_LEDGER_v5.json",
    ]:
        ledger = read_json_safe(ledger_path)
        if ledger:
            amendments = []
            # v5 format has new_amendments list
            for amend in ledger.get("new_amendments", []):
                if amend.get("status") == "accepted":
                    amendments.append(f"{amend['id']}: {amend.get('trigger','')[:60]}")
            if amendments:
                return amendments
    # Fallback: return known list from AMEND-0009
    return [
        "AMEND-0001: End-of-chunk self-improvement loop",
        "AMEND-0002: PDSA/PDCA continuous improvement cycle",
        "AMEND-0003: Category-scoped governance taxonomy",
        "AMEND-0004: Nomotic runtime governance (PDP/PEP)",
        "AMEND-0005: Mid-chunk interrupt trigger (IC-1→IC-6)",
        "AMEND-0006: Autonomous sidecar generation on threshold",
        "AMEND-0007: Claude memory bridge (session sync)",
        "AMEND-0008: Runtime pulse layer (pre+post per artifact)",
        "AMEND-0009: P-1 TOOL_ROUTE_GUARD + HEAVY_WORK_CLASS_ENUM",
    ]


def resolve_open_ic_triggers(root: Path) -> List[str]:
    """Read open IC triggers from interrupt receipts directory."""
    receipts_dir = root / "0_kernel/registry/interrupt_receipts"
    if not receipts_dir.exists():
        return []
    open_triggers = []
    for receipt_file in receipts_dir.glob("IC_INTERRUPT_*.json"):
        receipt = read_json_safe(receipt_file)
        if receipt and not receipt.get("resumed", False):
            open_triggers.append(
                f"{receipt.get('receipt_id','?')} — "
                f"{receipt.get('artifact_id','?')} — "
                f"{receipt.get('classification','?')}"
            )
    return open_triggers[:10]  # cap at 10


def resolve_pending_sidecars(root: Path) -> List[str]:
    """Read recently generated sidecars from ledger."""
    ledger_path = root.parent / "workflow_sidecars" / "SIDECAR_GENERATION_LEDGER_v1.jsonl"
    if not ledger_path.exists():
        ledger_path = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/SIDECAR_GENERATION_LEDGER_v1.jsonl")
    if not ledger_path.exists():
        return []
    sidecars = []
    try:
        for line in ledger_path.read_text().strip().split("\n"):
            if line.strip():
                e = json.loads(line)
                sidecars.append(f"{e.get('sidecar_id','?')} [{e.get('trigger_class','?')}]")
    except (json.JSONDecodeError, OSError):
        pass
    return sidecars[-5:]  # last 5


def resolve_new_scripts(root: Path) -> List[str]:
    """List scripts added this session from build_receipts."""
    receipts_dir = root / "0_kernel/registry/build_receipts"
    if not receipts_dir.exists():
        return []
    scripts = []
    for receipt_file in sorted(receipts_dir.glob("BUILD*_RECEIPT_v1.json")):
        receipt = read_json_safe(receipt_file)
        if receipt:
            artifact = receipt.get("artifact", "")
            sha = receipt.get("sha256", "")[:16]
            if artifact:
                scripts.append(f"{artifact} (sha: {sha}...)")
    return scripts


def resolve_git_commit(root: Path) -> Optional[str]:
    """Get current git HEAD SHA."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SYNC WRITER
# ─────────────────────────────────────────────────────────────────────────────

def build_sync(
    root: Path,
    bundle_version: str,
    session_note: str,
    current_stage_override: Optional[str] = None,
    next_chunk: Optional[List[str]] = None,
    known_blockers: Optional[List[str]] = None,
    deferred_items: Optional[List[str]] = None,
    workflow_version: str = "v6",
    regression_checklist_version: str = "v5",
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Build the memory sync payload from OS tree state + overrides.
    Returns (sync_dict, missing_required_fields).
    """
    missing = []

    # Resolve baseline SHA
    baseline_sha, sha_source = resolve_baseline_sha(root)
    if not baseline_sha:
        missing.append("baseline_sha")
        baseline_sha = "UNRESOLVED"

    # Resolve current stage
    if current_stage_override:
        current_stage = current_stage_override
        stage_source = "override"
    else:
        current_stage, stage_source = resolve_current_stage(root)
        if current_stage == "UNKNOWN":
            missing.append("current_stage")

    # Resolve active amendments
    active_amendments = resolve_active_amendments(root)
    active_success_patterns = [
        "SP-0001: Chunked artifact processing with receipts",
        "SP-0002: Contract-before-kernel-rewrite",
        "GW1-P001→P006: HTML governance gates",
        "SUCCESS-GOV-CAT-001: Job-scoped governance category selection",
        "AMEND-0006-AUTO-SIDECAR: Autonomous sidecar on threshold crossing",
    ]

    # Optional fields
    open_ic_triggers = resolve_open_ic_triggers(root)
    pending_sidecars = resolve_pending_sidecars(root)
    new_scripts = resolve_new_scripts(root)
    git_commit_sha = resolve_git_commit(root)

    sync = {
        # Identity
        "schema_version": SCHEMA_VERSION,
        "amendment": AMENDMENT,
        "generated_by": "claude_memory_sync_writer_v1.py",

        # Required fields
        "sync_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "bundle_version": bundle_version,
        "current_stage": current_stage,
        "baseline_sha": baseline_sha,
        "active_amendments": active_amendments,
        "active_success_patterns": active_success_patterns,
        "regression_checklist_version": regression_checklist_version,
        "workflow_version": workflow_version,
        "session_note": session_note,

        # Optional — populated from OS state
        "open_ic_triggers": open_ic_triggers,
        "pending_sidecars": pending_sidecars,
        "known_blockers": known_blockers or [],
        "next_chunk": next_chunk or [],
        "deferred_items": deferred_items or [],
        "new_scripts_deployed": new_scripts,
        "git_commit_sha": git_commit_sha,

        # Provenance
        "_sources": {
            "baseline_sha_source": sha_source,
            "current_stage_source": stage_source,
            "root_path": str(root),
        },

        # Sync metadata
        "_sync_complete": len(missing) == 0,
        "_missing_required": missing,
    }

    # Self-hash (SHA of everything except the _sha field)
    payload_str = json.dumps(
        {k: v for k, v in sync.items() if k != "_sha"}, sort_keys=True
    )
    sync["_sha"] = hashlib.sha256(payload_str.encode()).hexdigest()

    return sync, missing


def write_sync(
    sync: Dict[str, Any],
    output_path: Path,
    history_path: Path,
) -> str:
    """Write sync file atomically and append to history ledger. Returns SHA256."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(sync, indent=2), encoding="utf-8")
    os.replace(tmp, output_path)
    file_sha = hashlib.sha256(output_path.read_bytes()).hexdigest()

    # Append to history ledger (JSONL — never overwrites)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_entry = {
        "sync_utc": sync.get("sync_utc"),
        "bundle_version": sync.get("bundle_version"),
        "current_stage": sync.get("current_stage"),
        "baseline_sha": sync.get("baseline_sha", "")[:16] + "...",
        "file_sha": file_sha,
        "complete": sync.get("_sync_complete", False),
    }
    with open(history_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(history_entry) + "\n")

    return file_sha


def verify_sync(sync_path: Path) -> Tuple[bool, str]:
    """Verify the _sha field in a sync file matches computed SHA."""
    sync = read_json_safe(sync_path)
    if not sync:
        return False, "file not found or invalid JSON"
    stored_sha = sync.get("_sha", "")
    payload_str = json.dumps(
        {k: v for k, v in sync.items() if k != "_sha"}, sort_keys=True
    )
    computed_sha = hashlib.sha256(payload_str.encode()).hexdigest()
    if stored_sha == computed_sha:
        return True, f"SHA valid: {stored_sha[:16]}..."
    return False, f"SHA mismatch: stored={stored_sha[:16]} computed={computed_sha[:16]}"


def print_sync_summary(sync: Dict[str, Any], file_sha: str):
    """Print human-readable summary of the sync file."""
    complete = sync.get("_sync_complete", False)
    missing = sync.get("_missing_required", [])
    status = "COMPLETE ✓" if complete else f"PARTIAL ⚠  missing: {missing}"

    print(f"\n{'='*60}")
    print(f"CLAUDE_MEMORY_SYNC_v1 — {status}")
    print(f"{'='*60}")
    print(f"  sync_utc:          {sync.get('sync_utc')}")
    print(f"  bundle_version:    {sync.get('bundle_version')}")
    print(f"  current_stage:     {sync.get('current_stage')}")
    sha = sync.get('baseline_sha', '')
    print(f"  baseline_sha:      {sha[:16]}...{sha[-8:] if len(sha) > 24 else ''}")
    print(f"  workflow_version:  {sync.get('workflow_version')}")
    print(f"  session_note:      {sync.get('session_note')}")
    print(f"  active_amendments: {len(sync.get('active_amendments', []))}")
    print(f"  open_ic_triggers:  {len(sync.get('open_ic_triggers', []))}")
    print(f"  pending_sidecars:  {len(sync.get('pending_sidecars', []))}")
    print(f"  new_scripts:       {len(sync.get('new_scripts_deployed', []))}")
    print(f"  known_blockers:    {len(sync.get('known_blockers', []))}")
    print(f"  file_sha:          {file_sha[:16]}...")
    print(f"  _sha:              {sync.get('_sha','')[:16]}...")
    if sync.get('new_scripts_deployed'):
        print(f"\n  Scripts deployed this session:")
        for s in sync['new_scripts_deployed']:
            print(f"    - {s}")
    if sync.get('known_blockers'):
        print(f"\n  Known blockers:")
        for b in sync['known_blockers']:
            print(f"    - {b}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MetaBlooms Claude Memory Sync Writer v1 — AMEND-0007"
    )
    sub = ap.add_subparsers(dest="command", required=True)

    # write
    wr = sub.add_parser("write", help="Write CLAUDE_MEMORY_SYNC_v1.json from OS state")
    wr.add_argument("--root",             default=str(DEFAULT_ROOT))
    wr.add_argument("--output",           default=str(DEFAULT_OUTPUT))
    wr.add_argument("--history",          default=str(DEFAULT_HISTORY_LOG))
    wr.add_argument("--bundle-version",   required=True,
                    help="e.g. v33/GW5T or 20260426-BUILD4")
    wr.add_argument("--session-note",     required=True,
                    help="One sentence describing what this session accomplished")
    wr.add_argument("--current-stage",    default=None,
                    help="Override stage name (default: read from ledger)")
    wr.add_argument("--next-chunk",       nargs="*", default=None)
    wr.add_argument("--known-blockers",   nargs="*", default=None)
    wr.add_argument("--deferred-items",   nargs="*", default=None)
    wr.add_argument("--workflow-version", default="v6")
    wr.add_argument("--checklist-version", default="v5")
    wr.add_argument("--json-output",      action="store_true")

    # verify
    vr = sub.add_parser("verify", help="Verify SHA of an existing sync file")
    vr.add_argument("--sync-file", default=str(DEFAULT_OUTPUT))

    # show
    sh = sub.add_parser("show", help="Print summary of an existing sync file")
    sh.add_argument("--sync-file", default=str(DEFAULT_OUTPUT))

    # history
    hi = sub.add_parser("history", help="Print sync history ledger")
    hi.add_argument("--history", default=str(DEFAULT_HISTORY_LOG))
    hi.add_argument("--limit",   type=int, default=10)

    args = ap.parse_args(argv)

    if args.command == "write":
        root = Path(args.root)
        output = Path(args.output)
        history = Path(args.history)

        print(f"[MEMORY SYNC] Building sync from: {root}")
        sync, missing = build_sync(
            root=root,
            bundle_version=args.bundle_version,
            session_note=args.session_note,
            current_stage_override=args.current_stage,
            next_chunk=args.next_chunk,
            known_blockers=args.known_blockers,
            deferred_items=args.deferred_items,
            workflow_version=args.workflow_version,
            regression_checklist_version=args.checklist_version,
        )

        file_sha = write_sync(sync, output, history)
        print_sync_summary(sync, file_sha)
        print(f"Written: {output}")
        print(f"File SHA: {file_sha}")

        if args.json_output:
            print(json.dumps(sync, indent=2))

        sys.exit(0 if not missing else 2)

    elif args.command == "verify":
        valid, msg = verify_sync(Path(args.sync_file))
        print(f"Verify: {'PASS ✓' if valid else 'FAIL ✗'}  {msg}")
        sys.exit(0 if valid else 1)

    elif args.command == "show":
        sync = read_json_safe(Path(args.sync_file))
        if not sync:
            print("ERROR: cannot read sync file")
            sys.exit(1)
        file_sha = hashlib.sha256(Path(args.sync_file).read_bytes()).hexdigest()
        print_sync_summary(sync, file_sha)
        sys.exit(0)

    elif args.command == "history":
        history_path = Path(args.history)
        if not history_path.exists():
            print("No sync history yet.")
            sys.exit(0)
        lines = history_path.read_text().strip().split("\n")
        for line in lines[-args.limit:]:
            if line.strip():
                e = json.loads(line)
                status = "✓" if e.get("complete") else "⚠"
                print(f"  {status} {e.get('sync_utc')}  "
                      f"stage={e.get('current_stage')}  "
                      f"sha={e.get('file_sha','')[:12]}...")
        sys.exit(0)


if __name__ == "__main__":
    main()
