#!/usr/bin/env python3
"""MetaBlooms tracker stage finalization hook v1.

Canonical finalization wrapper for bounded governed stages.

It runs after a stage receipt and handoff have been written and before the
assistant's final response. It updates runtime/state/TRACKER_STATE_v1.json,
renders a mobile-safe tracker preview, and validates that the state is bound to
that stage's receipt/handoff.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _infer_stage_from_handoff(handoff: Dict[str, Any], fallback: str) -> str:
    for key in ("stage_id", "stage", "current_stage", "stage_name"):
        value = handoff.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return fallback


def _infer_text(handoff: Dict[str, Any], keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        value = handoff.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return default


def _run(cmd: list[str], timeout_seconds: int = 8) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=False, timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd, 124,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else str(exc.stdout or ""),
            stderr=((exc.stderr or "") if isinstance(exc.stderr, str) else str(exc.stderr or "")) + f"\nTIMEOUT_AFTER_SECONDS={timeout_seconds}",
        )


def _write_json_atomic(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
        try:
            dfd = os.open(str(path.parent), os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except Exception:
            pass
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def _write_probe(directory: Path) -> str:
    directory.mkdir(parents=True, exist_ok=True)
    probe = directory / f".tracker_write_probe_{os.getpid()}"
    try:
        probe.write_text("probe", encoding="utf-8")
        probe.unlink()
        return "PASS"
    except Exception as exc:
        return f"FAIL:{exc!r}"


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Finalize a bounded MetaBlooms stage tracker update.")
    p.add_argument("--root", required=True)
    p.add_argument("--receipt", required=True)
    p.add_argument("--handoff", required=True)
    p.add_argument("--stage")
    p.add_argument("--project-name", default="MetaBlooms Governed Workflow")
    p.add_argument("--stage-index", type=int, required=True)
    p.add_argument("--stage-total", type=int, required=True)
    p.add_argument("--status", default="DONE")
    p.add_argument("--now")
    p.add_argument("--next")
    p.add_argument("--stop-rule")
    p.add_argument("--report", required=True)
    p.add_argument("--preview", required=True)
    p.add_argument("--state")
    p.add_argument("--timestamp-utc", default=_utc_now())
    args = p.parse_args(argv)

    root = Path(args.root).resolve()
    receipt = Path(args.receipt).resolve()
    handoff = Path(args.handoff).resolve()
    state = Path(args.state).resolve() if args.state else root / "runtime/state/TRACKER_STATE_v1.json"
    report = Path(args.report).resolve()
    preview = Path(args.preview).resolve()
    cartridge_dir = root / "0_kernel/cartridges/inline_project_tracker"
    updater = cartridge_dir / "TRACKER_STATE_UPDATER_v1.py"
    validator = cartridge_dir / "TRACKER_HANDOFF_UPDATE_VALIDATOR_v1.py"

    errors: list[str] = []
    for label, path, is_dir in [
        ("root", root, True), ("receipt", receipt, False), ("handoff", handoff, False),
        ("state", state, False), ("updater", updater, False), ("validator", validator, False),
    ]:
        if is_dir and not path.is_dir():
            errors.append(f"{label}_missing:{path}")
        if not is_dir and not path.is_file():
            errors.append(f"{label}_missing:{path}")
    if args.stage_index < 0 or args.stage_total <= 0 or args.stage_index > args.stage_total:
        errors.append("invalid_stage_index_or_total")

    handoff_obj: Dict[str, Any] = {}
    if handoff.is_file():
        try:
            handoff_obj = _load_json(handoff)
        except Exception as exc:  # pragma: no cover - defensive report path
            errors.append(f"handoff_json_invalid:{exc}")

    stage = args.stage or _infer_stage_from_handoff(handoff_obj, receipt.parent.name)
    now = args.now or _infer_text(handoff_obj, ("now", "summary", "status_summary"), f"Finalized {stage}")
    next_action = args.next or _infer_text(handoff_obj, ("next", "next_allowed_action", "next_continuation_prompt"), "continue from latest handoff")
    stop_rule = args.stop_rule or _infer_text(handoff_obj, ("stop_rule", "stop", "stop_condition"), "stop before next bounded stage")

    report.parent.mkdir(parents=True, exist_ok=True)
    preview.parent.mkdir(parents=True, exist_ok=True)
    report_write_probe = _write_probe(report.parent)
    preview_write_probe = _write_probe(preview.parent)
    if not report_write_probe.startswith("PASS"):
        errors.append(f"report_dir_write_probe_failed:{report_write_probe}")
    if not preview_write_probe.startswith("PASS"):
        errors.append(f"preview_dir_write_probe_failed:{preview_write_probe}")

    update_cmd = [
        sys.executable, "-S", str(updater),
        "--root", str(root),
        "--state", str(state),
        "--receipt", str(receipt),
        "--handoff", str(handoff),
        "--stage", stage,
        "--stage-index", str(args.stage_index),
        "--stage-total", str(args.stage_total),
        "--status", args.status,
        "--now", now,
        "--next", next_action,
        "--stop-rule", stop_rule,
        "--timestamp-utc", args.timestamp_utc,
        "--render-preview", str(preview),
    ]
    validation_report = report.with_name(report.stem + "_handoff_validation.json")
    validate_cmd = [
        sys.executable, "-S", str(validator),
        "--root", str(root),
        "--state", str(state),
        "--receipt", str(receipt),
        "--handoff", str(handoff),
        "--preview", str(preview),
        "--stage", stage,
        "--report", str(validation_report),
    ]

    update_result = None
    validate_result = None
    if not errors:
        update_result = _run(update_cmd, timeout_seconds=8)
        if update_result.returncode != 0:
            errors.append("tracker_state_updater_failed")
        validate_result = _run(validate_cmd, timeout_seconds=8)
        if validate_result.returncode != 0:
            errors.append("tracker_handoff_validator_failed")

    preview_text = preview.read_text(encoding="utf-8") if preview.is_file() else ""
    max_width = max((len(line) for line in preview_text.splitlines()), default=0)
    if preview_text and not preview_text.startswith("TRACKER ▸"):
        errors.append("preview_missing_top_marker")
    if max_width > 64:
        errors.append(f"preview_width_exceeds_64:{max_width}")
    if "%" in preview_text:
        errors.append("preview_contains_percent_symbol")

    failure_capture_report = report.with_name(report.stem + "_failure_event_capture.json")
    failure_capture = root / "0_kernel/scripts/failure_event_capture_hook_v1.py"
    failure_capture_result = None
    if failure_capture.is_file():
        capture_cmd = [
            sys.executable, "-S", str(failure_capture),
            "--root", str(root),
            "--stage", stage,
            "--receipt", str(receipt),
            "--handoff", str(handoff),
            "--tracker-status", "PASS" if not errors else "FAIL",
            "--tracker-errors-json", json.dumps(errors),
            "--capture-report", str(failure_capture_report),
            "--timestamp-utc", args.timestamp_utc,
        ]
        failure_capture_result = _run(capture_cmd, timeout_seconds=8)
        if failure_capture_result.returncode != 0:
            errors.append("failure_event_capture_hook_failed")
    else:
        failure_capture_report = None

    out = {
        "artifact_type": "TRACKER_STAGE_FINALIZATION_HOOK_REPORT",
        "hook": "TRACKER_STAGE_FINALIZATION_HOOK_v1",
        "created_utc": args.timestamp_utc,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "stage": stage,
        "project_name": args.project_name,
        "stage_index": args.stage_index,
        "stage_total": args.stage_total,
        "root": str(root),
        "state_path": str(state),
        "receipt_path": str(receipt),
        "handoff_path": str(handoff),
        "preview_path": str(preview),
        "validation_report_path": str(validation_report),
        "failure_event_capture_report_path": str(failure_capture_report) if failure_capture_report else None,
        "checks": {
            "report_dir_write_probe": report_write_probe,
            "preview_dir_write_probe": preview_write_probe,
            "hook_runs_after_receipt_and_handoff_exist": "PASS" if receipt.is_file() and handoff.is_file() else "FAIL",
            "state_updated": "PASS" if update_result and update_result.returncode == 0 else "FAIL",
            "handoff_binding_validated": "PASS" if validate_result and validate_result.returncode == 0 else "FAIL",
            "preview_top_marker": "PASS" if preview_text.startswith("TRACKER ▸") else "FAIL",
            "mobile_safe_width_max_64": "PASS" if max_width <= 64 else "FAIL",
            "fake_percent_rejection_preserved": "PASS" if "%" not in preview_text else "FAIL",
        },
        "update_stdout": update_result.stdout if update_result else "",
        "update_stderr": update_result.stderr if update_result else "",
        "validate_stdout": validate_result.stdout if validate_result else "",
        "validate_stderr": validate_result.stderr if validate_result else "",
        "failure_capture_stdout": failure_capture_result.stdout if failure_capture_result else "",
        "failure_capture_stderr": failure_capture_result.stderr if failure_capture_result else "",
        "rendered_preview": preview_text,
    }
    _write_json_atomic(report, out)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
