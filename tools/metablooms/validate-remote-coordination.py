#!/usr/bin/env python3
"""Validate MetaBlooms remote coordination scaffold.
Stdlib-only; intended for GitHub Actions, Termux, PowerShell Python, and ChatGPT sandbox.
"""
from __future__ import annotations
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REQUIRED = [
    "governance/sync/MULTI_CHAT_SYNC_CONTRACT.json",
    "governance/sync/LEASE_PROTOCOL.json",
    "governance/sync/DELTA_MERGE_POLICY.json",
    "governance/sync/CONFLICT_RESOLUTION_POLICY.json",
    "recovery/CHAT_REGISTRY.json",
    "recovery/PROJECT_REGISTRY.json",
    "recovery/REMOTE_COORDINATION_STATE.json",
    "recovery/CURRENT_STATE.md",
    "coordination/events/README.md",
]
DIRS = [
    "coordination/events",
    "coordination/leases",
    "coordination/queue",
    "coordination/snapshots",
    "coordination/conflicts",
    "runtime/repo_sync/outbox",
    "runtime/repo_sync/receipts",
    "runtime/repo_sync/manifests",
]

def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)

def main() -> None:
    for rel in REQUIRED:
        path = ROOT / rel
        if not path.is_file():
            fail(f"missing required file: {rel}")
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            if "schema_version" not in data and "event_id" not in data:
                fail(f"json lacks schema_version/event_id: {rel}")
    for rel in DIRS:
        if not (ROOT / rel).is_dir():
            fail(f"missing required directory: {rel}")
    state = json.loads((ROOT / "recovery/REMOTE_COORDINATION_STATE.json").read_text(encoding="utf-8"))
    if state.get("coordination_model") != "append-only events + leases + compacted recovery state":
        fail("unexpected coordination model")
    print("PASS: MetaBlooms remote coordination scaffold valid")

if __name__ == "__main__":
    main()
