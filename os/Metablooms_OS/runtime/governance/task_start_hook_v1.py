#!/usr/bin/env python3
"""Task-start hook v1: mandatory prompt pre-execution routing + ledger writeback."""
from __future__ import annotations
import json, pathlib, time, importlib.util, sys
ROOT_DEFAULT = pathlib.Path(__file__).resolve().parents[2]
KERNEL = ROOT_DEFAULT / "0_kernel"
if str(KERNEL) not in sys.path:
    sys.path.insert(0, str(KERNEL))
from lib.io.atomic_append_log_compat_v1 import append_jsonl_record

def _load_enforcer(root: pathlib.Path):
    p = root / "runtime/governance/prompt_route_preexecution_enforcer_v1.py"
    spec = importlib.util.spec_from_file_location("prompt_route_preexecution_enforcer_v1", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def start_task(prompt: str, root: str | pathlib.Path | None = None, context: dict | None = None) -> dict:
    root = pathlib.Path(root) if root else ROOT_DEFAULT
    mod = _load_enforcer(root)
    decision = mod.enforce_prompt_route(prompt, root=root, context=context or {})
    ledger = root / "runtime/state/PROMPT_TASK_START_LEDGER_v1.jsonl"
    rec = {"event":"task_start_preexecution_decision", "logged_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "decision":decision}
    append_jsonl_record(ledger, rec, operation_id="task_start_preexecution_decision", source="task_start_hook_v1", event_type="task_start_preexecution_decision", severity="info", allowed_roots=[str(root.resolve())])
    return decision

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--root", default=None)
    args=ap.parse_args()
    print(json.dumps(start_task(args.prompt, args.root), indent=2, sort_keys=True))
