#!/usr/bin/env python3
"""MetaBlooms bounded subprocess wrapper v1.

CDR CRITICAL implementation stage artifact. This module is intentionally stdlib-only
and designed for use with python3 -S inside the ChatGPT/Linux sandbox.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

_IO_LIB = pathlib.Path(__file__).resolve().parents[1] / "io"
if str(_IO_LIB) not in sys.path:
    sys.path.insert(0, str(_IO_LIB))
from atomic_json_compat_v1 import write_json_file

RESULT_ALLOW_SUCCESS = "ALLOW_SUCCESS"
RESULT_ALLOW_NONZERO = "ALLOW_NONZERO"
RESULT_DENY_FORBIDDEN_METHOD = "DENY_FORBIDDEN_METHOD"
RESULT_DENY_SCHEMA_INVALID = "DENY_SCHEMA_INVALID"
RESULT_DENY_SHELL_UNAPPROVED = "DENY_SHELL_UNAPPROVED"
RESULT_DENY_PATH_ESCAPE = "DENY_PATH_ESCAPE"
RESULT_TIMEOUT_TERMINATED = "TIMEOUT_TERMINATED"
RESULT_TIMEOUT_KILLED = "TIMEOUT_KILLED"
RESULT_SPAWN_ERROR = "SPAWN_ERROR"
RESULT_OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"

SAFE_ENV_KEYS = ("PATH", "HOME", "LANG", "LC_ALL", "TZ")
DEFAULT_MAX_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 1
DEFAULT_MAX_CAPTURE_BYTES = 131072


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def stable_hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()


def atomic_write_json(path: pathlib.Path, obj: Dict[str, Any]) -> None:
    write_json_file(
        path,
        obj,
        operation_id="bounded_subprocess_internal_receipt",
        allowed_roots=["/mnt/data"],
        create_parent=True,
        max_bytes=2_000_000,
    )


def load_json_if_exists(path: pathlib.Path) -> Dict[str, Any]:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return {}


def truncate_text(data: str, limit: int) -> Tuple[str, bool, int, str]:
    raw = data.encode("utf-8", "replace")
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) <= limit:
        return data, False, len(raw), digest
    truncated = raw[:limit].decode("utf-8", "replace")
    return truncated, True, len(raw), digest


def _realpath(path: str) -> pathlib.Path:
    return pathlib.Path(path).expanduser().resolve()


def _is_under(path: pathlib.Path, roots: List[pathlib.Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def validate_envelope(envelope: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not isinstance(envelope, dict):
        return ["envelope_not_object"]
    argv = envelope.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        errors.append("argv_must_be_nonempty_list_of_strings")
    if envelope.get("shell", False) is not False:
        if not (envelope.get("exception_token") and envelope.get("policy_authority")):
            errors.append("shell_requires_exception_token_and_policy_authority")
    timeout = envelope.get("timeout_seconds", 10)
    if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > DEFAULT_MAX_TIMEOUT_SECONDS:
        errors.append("timeout_seconds_out_of_range")
    retries = envelope.get("max_retries", 0)
    if not isinstance(retries, int) or retries < 0 or retries > DEFAULT_MAX_RETRIES:
        errors.append("max_retries_out_of_range")
    cap = envelope.get("max_capture_bytes", DEFAULT_MAX_CAPTURE_BYTES)
    if not isinstance(cap, int) or cap < 0 or cap > DEFAULT_MAX_CAPTURE_BYTES:
        errors.append("max_capture_bytes_out_of_range")
    roots = envelope.get("allowed_roots")
    if not isinstance(roots, list) or not roots or not all(isinstance(x, str) and x for x in roots):
        errors.append("allowed_roots_required")
    cwd = envelope.get("cwd")
    if cwd is not None and not isinstance(cwd, str):
        errors.append("cwd_must_be_string_or_null")
    env = envelope.get("env")
    if env is not None:
        if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k,v in env.items()):
            errors.append("env_must_be_string_map")
    rid = envelope.get("receipt_dir")
    if rid is not None and not isinstance(rid, str):
        errors.append("receipt_dir_must_be_string_or_null")
    op = envelope.get("operation_type")
    if not isinstance(op, str) or not op:
        errors.append("operation_type_required")
    return errors


def load_forbidden_methods(root: pathlib.Path) -> List[Dict[str, Any]]:
    candidates = [
        root / "FORBIDDEN_VALIDATION_METHODS_v1.json",
        root / "runtime" / "authority" / "FORBIDDEN_VALIDATION_METHODS_v1.json",
        root / "0_kernel" / "registry" / "export_authority" / "BASELINE_INTERNALIZE_1_20260430T021800Z" / "FORBIDDEN_VALIDATION_METHODS_v1.json",
    ]
    for path in candidates:
        data = load_json_if_exists(path)
        methods = data.get("forbidden_methods")
        if isinstance(methods, list):
            return methods
    return []


def command_matches_forbidden(argv: List[str], operation_type: str, forbidden_methods: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    joined = " ".join(argv)
    for method in forbidden_methods:
        observed = str(method.get("observed_failure", "")).lower()
        method_id = str(method.get("method_id", ""))
        if method.get("forbidden_by_default") is True:
            if "unzip -tqq" in observed and len(argv) >= 2 and pathlib.Path(argv[0]).name == "unzip" and "-tqq" in argv[1:]:
                return {"method_id": method_id, "reason": "matched_observed_unzip_tqq_forbidden_method", "method": method}
            if "jar xf" in observed and len(argv) >= 2 and pathlib.Path(argv[0]).name == "jar" and argv[1] == "xf":
                return {"method_id": method_id, "reason": "matched_observed_jar_xf_forbidden_method", "method": method}
            if operation_type == "full_archive_recursive_extraction" and "archive" in str(method.get("scope", "")).lower():
                return {"method_id": method_id, "reason": "matched_forbidden_operation_type", "method": method}
            if "unzip -tqq" in joined.lower():
                return {"method_id": method_id, "reason": "matched_joined_unzip_tqq", "method": method}
    return None


def make_failure_event(packet: Dict[str, Any], failure_class: str, root: pathlib.Path) -> Dict[str, Any]:
    return {
        "artifact_type": "METABLOOMS_SUBPROCESS_FAILURE_LEARNING_EVENT_v1",
        "created_utc": utc_now(),
        "stage": packet.get("stage"),
        "operation_type": packet.get("operation_type"),
        "failure_class": failure_class,
        "result_class": packet.get("result_class"),
        "argv_redacted": packet.get("argv_redacted"),
        "cwd": packet.get("cwd"),
        "attempts": packet.get("attempts", []),
        "policy_matches": packet.get("policy_matches", []),
        "recommendation": "Route future matching operations through bounded wrapper and method reliability policy before spawn.",
        "root": str(root),
    }


def write_failure_event_if_needed(packet: Dict[str, Any], receipt_dir: pathlib.Path, root: pathlib.Path) -> Optional[str]:
    if packet.get("result_class") == RESULT_ALLOW_SUCCESS:
        return None
    failure_class = packet.get("failure_class") or packet.get("result_class") or "UNKNOWN_FAILURE"
    event = make_failure_event(packet, failure_class, root)
    name = f"SUBPROCESS_FAILURE_EVENT_{packet.get('operation_type','operation')}_{utc_now()}_{stable_hash_text(json.dumps(packet, sort_keys=True))[:12]}.json"
    path = receipt_dir / name
    atomic_write_json(path, event)
    # Candidate registry copy, append-only by event file. No mutation of global registry in this stage.
    registry_path = root / "0_kernel" / "registry" / "failure_learning" / "bounded_subprocess_wrapper_v1" / name
    atomic_write_json(registry_path, event)
    return str(path)


def run_governed_command(envelope: Dict[str, Any]) -> Dict[str, Any]:
    start = time.monotonic()
    created = utc_now()
    root = _realpath(envelope.get("runtime_root", "/mnt/data/Metablooms_OS")) if isinstance(envelope, dict) else pathlib.Path("/mnt/data/Metablooms_OS").resolve()
    receipt_dir = pathlib.Path(envelope.get("receipt_dir") or (root / "runtime" / "receipts" / "bounded_subprocess_wrapper_v1" / created)).resolve()
    receipt_dir.mkdir(parents=True, exist_ok=True)
    base_packet: Dict[str, Any] = {
        "artifact_type": "METABLOOMS_BOUNDED_COMMAND_DECISION_PACKET_v1",
        "created_utc": created,
        "stage": envelope.get("stage") if isinstance(envelope, dict) else None,
        "operation_type": envelope.get("operation_type") if isinstance(envelope, dict) else None,
        "result_class": None,
        "failure_class": None,
        "argv_redacted": envelope.get("argv") if isinstance(envelope, dict) else None,
        "cwd": envelope.get("cwd") if isinstance(envelope, dict) else None,
        "receipt_dir": str(receipt_dir),
        "policy_matches": [],
        "attempts": [],
        "total_elapsed_ms": None,
        "failure_event_path": None,
        "pre_spawn_receipt_path": None,
    }
    errors = validate_envelope(envelope)
    if errors:
        base_packet.update({"result_class": RESULT_DENY_SCHEMA_INVALID, "failure_class": "SCHEMA_INVALID", "schema_errors": errors})
        packet_path = receipt_dir / "decision_packet.json"
        base_packet["failure_event_path"] = write_failure_event_if_needed(base_packet, receipt_dir, root)
        base_packet["decision_packet_path"] = str(packet_path)
        atomic_write_json(packet_path, base_packet)
        return base_packet

    argv: List[str] = envelope["argv"]
    allowed_roots = [_realpath(x) for x in envelope["allowed_roots"]]
    cwd = _realpath(envelope.get("cwd") or str(root))
    if not _is_under(cwd, allowed_roots):
        base_packet.update({"result_class": RESULT_DENY_PATH_ESCAPE, "failure_class": "CWD_OUTSIDE_ALLOWED_ROOTS", "resolved_cwd": str(cwd), "allowed_roots_resolved": [str(x) for x in allowed_roots]})
        path = receipt_dir / "decision_packet.json"
        base_packet["failure_event_path"] = write_failure_event_if_needed(base_packet, receipt_dir, root)
        base_packet["decision_packet_path"] = str(path)
        atomic_write_json(path, base_packet)
        return base_packet

    if envelope.get("shell", False) is not False:
        base_packet.update({"result_class": RESULT_DENY_SHELL_UNAPPROVED, "failure_class": "SHELL_UNAPPROVED"})
        path = receipt_dir / "decision_packet.json"
        base_packet["failure_event_path"] = write_failure_event_if_needed(base_packet, receipt_dir, root)
        base_packet["decision_packet_path"] = str(path)
        atomic_write_json(path, base_packet)
        return base_packet

    executable = shutil.which(argv[0]) if not os.path.isabs(argv[0]) else argv[0]
    if not executable:
        base_packet.update({"result_class": RESULT_SPAWN_ERROR, "failure_class": "EXECUTABLE_NOT_FOUND"})
        path = receipt_dir / "decision_packet.json"
        base_packet["failure_event_path"] = write_failure_event_if_needed(base_packet, receipt_dir, root)
        base_packet["decision_packet_path"] = str(path)
        atomic_write_json(path, base_packet)
        return base_packet
    argv_resolved = [str(pathlib.Path(executable).resolve())] + argv[1:]
    base_packet["argv_resolved"] = argv_resolved

    forbidden_methods = load_forbidden_methods(root)
    match = command_matches_forbidden(argv_resolved, envelope.get("operation_type", ""), forbidden_methods)
    if match:
        base_packet["policy_matches"].append(match)
        base_packet.update({"result_class": RESULT_DENY_FORBIDDEN_METHOD, "failure_class": "FORBIDDEN_METHOD"})
        pre = receipt_dir / "pre_spawn_receipt.json"
        atomic_write_json(pre, {"created_utc": utc_now(), "decision": "DENY_BEFORE_SPAWN", "reason": match, "argv_resolved": argv_resolved})
        base_packet["pre_spawn_receipt_path"] = str(pre)
        path = receipt_dir / "decision_packet.json"
        base_packet["failure_event_path"] = write_failure_event_if_needed(base_packet, receipt_dir, root)
        base_packet["decision_packet_path"] = str(path)
        atomic_write_json(path, base_packet)
        return base_packet

    pre = receipt_dir / "pre_spawn_receipt.json"
    atomic_write_json(pre, {"created_utc": utc_now(), "decision": "ALLOW_SPAWN", "argv_resolved": argv_resolved, "cwd": str(cwd), "timeout_seconds": envelope.get("timeout_seconds")})
    base_packet["pre_spawn_receipt_path"] = str(pre)

    timeout_seconds = float(envelope.get("timeout_seconds", 10))
    max_retries = int(envelope.get("max_retries", 0))
    cap = int(envelope.get("max_capture_bytes", DEFAULT_MAX_CAPTURE_BYTES))
    env = {k: os.environ[k] for k in SAFE_ENV_KEYS if k in os.environ}
    env.update(envelope.get("env") or {})
    final_result = RESULT_SPAWN_ERROR
    failure_class = None

    for attempt_idx in range(max_retries + 1):
        attempt_start = time.monotonic()
        attempt: Dict[str, Any] = {"attempt_index": attempt_idx, "started_utc": utc_now(), "timeout_seconds": timeout_seconds}
        proc = None
        try:
            proc = subprocess.Popen(argv_resolved, cwd=str(cwd), env=env, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=(os.name == "posix"))
            try:
                stdout, stderr = proc.communicate(timeout=timeout_seconds)
                elapsed_ms = int((time.monotonic() - attempt_start) * 1000)
                out_text, out_trunc, out_bytes, out_hash = truncate_text(stdout or "", cap)
                err_text, err_trunc, err_bytes, err_hash = truncate_text(stderr or "", cap)
                attempt.update({
                    "returncode": proc.returncode,
                    "elapsed_ms": elapsed_ms,
                    "stdout": out_text,
                    "stderr": err_text,
                    "stdout_bytes": out_bytes,
                    "stderr_bytes": err_bytes,
                    "stdout_sha256": out_hash,
                    "stderr_sha256": err_hash,
                    "stdout_truncated": out_trunc,
                    "stderr_truncated": err_trunc,
                })
                if out_trunc or err_trunc:
                    final_result = RESULT_OUTPUT_LIMIT_EXCEEDED
                    failure_class = "OUTPUT_LIMIT_EXCEEDED"
                elif proc.returncode == 0:
                    final_result = RESULT_ALLOW_SUCCESS
                    failure_class = None
                else:
                    final_result = RESULT_ALLOW_NONZERO
                    failure_class = "NONZERO_EXIT"
                base_packet["attempts"].append(attempt)
                if final_result == RESULT_ALLOW_SUCCESS:
                    break
                if final_result == RESULT_OUTPUT_LIMIT_EXCEEDED:
                    break
            except subprocess.TimeoutExpired:
                killed_group = False
                try:
                    if os.name == "posix":
                        os.killpg(proc.pid, signal.SIGTERM)
                        killed_group = True
                    else:
                        proc.terminate()
                    try:
                        stdout, stderr = proc.communicate(timeout=2)
                        result = RESULT_TIMEOUT_TERMINATED
                    except subprocess.TimeoutExpired:
                        if os.name == "posix":
                            os.killpg(proc.pid, signal.SIGKILL)
                        else:
                            proc.kill()
                        stdout, stderr = proc.communicate(timeout=2)
                        result = RESULT_TIMEOUT_KILLED
                except Exception as exc:
                    try:
                        proc.kill(); stdout, stderr = proc.communicate(timeout=2)
                    except Exception:
                        stdout, stderr = "", ""
                    result = RESULT_TIMEOUT_KILLED
                    attempt["kill_exception"] = repr(exc)
                out_text, out_trunc, out_bytes, out_hash = truncate_text(stdout or "", cap)
                err_text, err_trunc, err_bytes, err_hash = truncate_text(stderr or "", cap)
                attempt.update({"elapsed_ms": int((time.monotonic()-attempt_start)*1000), "returncode": proc.returncode, "stdout": out_text, "stderr": err_text, "stdout_bytes": out_bytes, "stderr_bytes": err_bytes, "stdout_sha256": out_hash, "stderr_sha256": err_hash, "stdout_truncated": out_trunc, "stderr_truncated": err_trunc, "killed_process_group": killed_group})
                base_packet["attempts"].append(attempt)
                final_result = result
                failure_class = "TIMEOUT"
                # Retry only timeout, and only within explicit retry count.
                if attempt_idx >= max_retries:
                    break
        except Exception as exc:
            attempt.update({"elapsed_ms": int((time.monotonic()-attempt_start)*1000), "spawn_exception": repr(exc)})
            base_packet["attempts"].append(attempt)
            final_result = RESULT_SPAWN_ERROR
            failure_class = "SPAWN_ERROR"
            break

    base_packet["result_class"] = final_result
    base_packet["failure_class"] = failure_class
    base_packet["total_elapsed_ms"] = int((time.monotonic() - start) * 1000)
    path = receipt_dir / "decision_packet.json"
    base_packet["failure_event_path"] = write_failure_event_if_needed(base_packet, receipt_dir, root)
    base_packet["decision_packet_path"] = str(path)
    atomic_write_json(path, base_packet)
    return base_packet


def _main(argv: List[str]) -> int:
    if len(argv) != 2:
        print("usage: bounded_subprocess_wrapper_v1.py ENVELOPE_JSON", file=sys.stderr)
        return 2
    envelope_path = pathlib.Path(argv[1])
    envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
    packet = run_governed_command(envelope)
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet.get("result_class") == RESULT_ALLOW_SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
