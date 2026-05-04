#!/usr/bin/env python3
"""MetaBlooms canonical atomic append-log writer v1.

CDR CRITICAL implementation target for append-only JSONL/event/ledger streams.
Public API: append_governed_jsonl_record(envelope: dict) -> dict
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

VERSION = "atomic_append_log_writer_v1"
DEFAULT_ALLOWED_SUFFIXES = [".jsonl", ".log.jsonl", ".ledger.jsonl", ".events.jsonl"]
DEFAULT_MAX_RECORD_BYTES = 262_144
DEFAULT_MODE = 0o600
CRITICAL_SEVERITIES = {"critical", "error", "fatal", "security", "high"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(value: Any, fallback: str = "append_log") -> str:
    raw = str(value or fallback)
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in raw)[:96] or fallback


def _resolve_allowed_roots(roots: Iterable[str]) -> List[Path]:
    return [Path(r).expanduser().resolve(strict=False) for r in roots]


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _existing_symlink_component(path: Path) -> str | None:
    absolute = path if path.is_absolute() else Path.cwd() / path
    absolute = Path(os.path.abspath(str(absolute)))
    parts = absolute.parts
    start = 1 if absolute.is_absolute() else 0
    for i in range(start, len(parts) + 1):
        probe = Path(*parts[:i])
        try:
            if probe.is_symlink():
                return str(probe)
        except OSError:
            return str(probe)
    return None


def _safe_parent_fsync(parent: Path) -> Dict[str, Any]:
    result = {"attempted": True, "ok": False, "error": None}
    try:
        fd = os.open(str(parent), os.O_RDONLY)
        try:
            os.fsync(fd)
            result["ok"] = True
        finally:
            os.close(fd)
    except Exception as exc:  # platform/filesystem dependent
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _write_json_receipt(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}")
    try:
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        _safe_parent_fsync(path.parent)
    finally:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass


def _base_decision(envelope: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "artifact_type": "AtomicAppendLogDecisionPacket.v1",
        "writer_version": VERSION,
        "created_utc": _utc_now(),
        "operation_id": envelope.get("operation_id"),
        "status": "UNSET",
        "ok": False,
        "deny_reason": None,
        "error_type": None,
        "log_path": envelope.get("log_path"),
        "resolved_log_path": None,
        "allowed_roots": envelope.get("allowed_roots", []),
        "bytes_appended": 0,
        "record_sha256": None,
        "line_sha256": None,
        "fsync_file": False,
        "fsync_parent": {"attempted": False, "ok": False, "error": None},
        "file_size_after": None,
        "failure_event_path": None,
        "receipt_path": None,
    }


def _classify_failure(decision: Dict[str, Any]) -> str:
    return {
        "DENY_SCHEMA_INVALID": "schema_invalid",
        "DENY_PATH_DENIED": "path_escape_or_root_denied",
        "DENY_SYMLINK_DENIED": "symlink_blocked",
        "DENY_UNSAFE_SUFFIX": "unsafe_suffix",
        "DENY_RECORD_INVALID": "record_invalid",
        "DENY_RECORD_TOO_LARGE": "record_size_limit",
        "DENY_FILE_TOO_LARGE": "file_size_limit",
        "DENY_POLICY_DENIED": "durability_policy_denied",
        "APPEND_ERROR": "append_error",
    }.get(str(decision.get("status")), "unknown_append_log_failure")


def _emit_failure_event(envelope: Dict[str, Any], decision: Dict[str, Any]) -> str | None:
    receipt_dir = envelope.get("receipt_dir") or envelope.get("failure_registry_dir")
    if not receipt_dir:
        return None
    path = Path(receipt_dir) / f"{_safe_name(envelope.get('operation_id'))}_append_failure_event.json"
    event = {
        "artifact_type": "AtomicAppendLogFailureEvent.v1",
        "created_utc": _utc_now(),
        "operation_id": envelope.get("operation_id"),
        "writer_version": VERSION,
        "status": decision.get("status"),
        "deny_reason": decision.get("deny_reason"),
        "error_type": decision.get("error_type"),
        "log_path": envelope.get("log_path"),
        "resolved_log_path": decision.get("resolved_log_path"),
        "classification": _classify_failure(decision),
    }
    _write_json_receipt(path, event)
    return str(path)


def _emit_decision(envelope: Dict[str, Any], decision: Dict[str, Any]) -> str | None:
    receipt_dir = envelope.get("receipt_dir")
    if not receipt_dir:
        return None
    path = Path(receipt_dir) / f"{_safe_name(envelope.get('operation_id'))}_append_decision_packet.json"
    decision["receipt_path"] = str(path)
    _write_json_receipt(path, decision)
    return str(path)


def _finalize(envelope: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    if not decision.get("ok"):
        decision["failure_event_path"] = _emit_failure_event(envelope, decision)
    _emit_decision(envelope, decision)
    return decision


def _contains_nonfinite(obj: Any) -> bool:
    if isinstance(obj, float):
        return math.isnan(obj) or math.isinf(obj)
    if isinstance(obj, dict):
        return any(_contains_nonfinite(k) or _contains_nonfinite(v) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return any(_contains_nonfinite(v) for v in obj)
    return False


def _validate_record(record: Any) -> str | None:
    if not isinstance(record, dict):
        return "record_must_be_object"
    required = ["schema_version", "event_id", "timestamp_utc", "source", "event_type", "severity", "payload"]
    missing = [k for k in required if k not in record]
    if missing:
        return "missing_record_fields:" + ",".join(missing)
    for key in ["schema_version", "event_id", "timestamp_utc", "source", "event_type", "severity"]:
        if not isinstance(record.get(key), str) or not record.get(key):
            return f"record_field_invalid:{key}"
    if _contains_nonfinite(record):
        return "non_finite_json_value"
    return None


def _serialize_record(record: Dict[str, Any]) -> bytes:
    text = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    # json.dumps escapes embedded newlines in string values as \n, so raw CR/LF here would imply injection or formatter bug.
    if "\n" in text or "\r" in text:
        raise ValueError("serialized_record_contains_raw_crlf")
    return text.encode("utf-8")


def _should_fsync(envelope: Dict[str, Any], record: Dict[str, Any]) -> bool:
    mode = envelope.get("durability_mode")
    severity = str(record.get("severity", "")).lower()
    if mode == "sync_always":
        return True
    if mode == "sync_on_critical":
        return severity in CRITICAL_SEVERITIES
    return False


def append_governed_jsonl_record(envelope: Dict[str, Any]) -> Dict[str, Any]:
    decision = _base_decision(envelope if isinstance(envelope, dict) else {})
    if not isinstance(envelope, dict):
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="envelope_not_object", error_type="TypeError")
        return _finalize({}, decision)

    required = ["schema_version", "operation_id", "log_path", "allowed_roots", "record", "durability_mode", "max_record_bytes"]
    missing = [k for k in required if k not in envelope]
    if missing:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="missing_required_fields:" + ",".join(missing), error_type="SchemaError")
        return _finalize(envelope, decision)
    if envelope.get("schema_version") != "AtomicAppendLogEnvelope.v1":
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="schema_version_mismatch", error_type="SchemaError")
        return _finalize(envelope, decision)
    if not isinstance(envelope.get("allowed_roots"), list) or not envelope["allowed_roots"]:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="allowed_roots_must_be_nonempty_list", error_type="SchemaError")
        return _finalize(envelope, decision)

    durability_mode = envelope.get("durability_mode")
    if durability_mode not in {"sync_always", "sync_on_critical", "sync_never_with_exception"}:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="invalid_durability_mode", error_type="SchemaError")
        return _finalize(envelope, decision)
    if durability_mode == "sync_never_with_exception" and not envelope.get("durability_exception_authority"):
        decision.update(status="DENY_POLICY_DENIED", deny_reason="sync_never_requires_exception_authority", error_type="PolicyDenied")
        return _finalize(envelope, decision)

    try:
        raw = Path(str(envelope["log_path"])).expanduser()
        raw_abs = raw if raw.is_absolute() else Path.cwd() / raw
        symlink = _existing_symlink_component(raw_abs)
        if symlink:
            decision["resolved_log_path"] = str(raw_abs)
            decision.update(status="DENY_SYMLINK_DENIED", deny_reason=f"symlink_component:{symlink}", error_type="SymlinkBlocked")
            return _finalize(envelope, decision)
        log_path = raw.resolve(strict=False)
        decision["resolved_log_path"] = str(log_path)
        roots = _resolve_allowed_roots(envelope["allowed_roots"])
    except Exception as exc:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="path_resolution_failed", error_type=f"{type(exc).__name__}: {exc}")
        return _finalize(envelope, decision)

    if not any(_is_relative_to(log_path, root) for root in roots):
        decision.update(status="DENY_PATH_DENIED", deny_reason="resolved_log_outside_allowed_roots", error_type="PathDenied")
        return _finalize(envelope, decision)

    allowed_suffixes = envelope.get("allowed_suffixes", DEFAULT_ALLOWED_SUFFIXES)
    if not isinstance(allowed_suffixes, list) or not all(isinstance(s, str) and s.startswith(".") for s in allowed_suffixes):
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="allowed_suffixes_invalid", error_type="SchemaError")
        return _finalize(envelope, decision)
    if not any(str(log_path).endswith(s) for s in allowed_suffixes):
        decision.update(status="DENY_UNSAFE_SUFFIX", deny_reason=f"suffix_not_allowed:{log_path.name}", error_type="UnsafeSuffix")
        return _finalize(envelope, decision)

    err = _validate_record(envelope.get("record"))
    if err:
        decision.update(status="DENY_RECORD_INVALID", deny_reason=err, error_type="RecordInvalid")
        return _finalize(envelope, decision)

    try:
        record_bytes = _serialize_record(envelope["record"])
    except Exception as exc:
        decision.update(status="DENY_RECORD_INVALID", deny_reason="record_serialization_failed", error_type=f"{type(exc).__name__}: {exc}")
        return _finalize(envelope, decision)
    max_record_bytes = int(envelope.get("max_record_bytes", DEFAULT_MAX_RECORD_BYTES))
    if len(record_bytes) > max_record_bytes:
        decision.update(status="DENY_RECORD_TOO_LARGE", deny_reason=f"record_size_exceeds_limit:{len(record_bytes)}>{max_record_bytes}", error_type="RecordTooLarge")
        return _finalize(envelope, decision)
    line = record_bytes + b"\n"

    create_parent = bool(envelope.get("create_parent", False))
    if not log_path.parent.exists():
        if not create_parent:
            decision.update(status="DENY_SCHEMA_INVALID", deny_reason="parent_missing_and_create_parent_false", error_type="ParentMissing")
            return _finalize(envelope, decision)
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            decision.update(status="APPEND_ERROR", deny_reason="parent_create_failed", error_type=f"{type(exc).__name__}: {exc}")
            return _finalize(envelope, decision)
    symlink = _existing_symlink_component(log_path)
    if symlink:
        decision.update(status="DENY_SYMLINK_DENIED", deny_reason=f"symlink_component_after_parent_create:{symlink}", error_type="SymlinkBlocked")
        return _finalize(envelope, decision)

    try:
        current_size = log_path.stat().st_size if log_path.exists() else 0
    except OSError:
        current_size = 0
    max_file_bytes = envelope.get("max_file_bytes")
    if max_file_bytes is not None and current_size + len(line) > int(max_file_bytes):
        decision.update(status="DENY_FILE_TOO_LARGE", deny_reason=f"file_size_limit:{current_size}+{len(line)}>{max_file_bytes}", error_type="FileTooLarge")
        return _finalize(envelope, decision)

    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    try:
        fd = os.open(str(log_path), flags, int(envelope.get("file_mode", DEFAULT_MODE)))
        try:
            view = memoryview(line)
            written = 0
            while written < len(line):
                n = os.write(fd, view[written:])
                if n <= 0:
                    raise OSError("os.write returned non-positive byte count")
                written += n
            decision["bytes_appended"] = written
            if _should_fsync(envelope, envelope["record"]):
                os.fsync(fd)
                decision["fsync_file"] = True
        finally:
            os.close(fd)
        if decision["fsync_file"]:
            decision["fsync_parent"] = _safe_parent_fsync(log_path.parent)
        decision.update(
            status="ALLOW_APPENDED",
            ok=True,
            record_sha256=_sha256_bytes(record_bytes),
            line_sha256=_sha256_bytes(line),
            file_size_after=log_path.stat().st_size if log_path.exists() else None,
        )
        return _finalize(envelope, decision)
    except Exception as exc:
        decision.update(status="APPEND_ERROR", deny_reason="append_failed", error_type=f"{type(exc).__name__}: {exc}")
        return _finalize(envelope, decision)


append_jsonl_record = append_governed_jsonl_record
