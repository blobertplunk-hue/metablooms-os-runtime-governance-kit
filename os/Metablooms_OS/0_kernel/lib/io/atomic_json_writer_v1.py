#!/usr/bin/env python3
"""MetaBlooms canonical atomic JSON writer v1.

CDR CRITICAL implementation target for safe JSON state/receipt writes.
The public API is write_atomic_json(envelope: dict) -> dict.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

VERSION = "atomic_json_writer_v1"
DEFAULT_ALLOWED_SUFFIXES = [".json"]
DEFAULT_MAX_BYTES = 2_000_000
DEFAULT_TIMEOUT_NOTE = "atomic_json_writer_is_in_process_no_subprocess_timeout"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_ready(payload: Any, *, indent: int | None, sort_keys: bool, ensure_ascii: bool) -> Tuple[bool, str | None, str | None, Any | None]:
    try:
        text = json.dumps(
            payload,
            indent=indent,
            sort_keys=sort_keys,
            ensure_ascii=ensure_ascii,
            allow_nan=False,
        ) + "\n"
        reparsed = json.loads(text)
        return True, text, None, reparsed
    except Exception as exc:  # noqa: BLE001 - deliberate decision packet capture
        return False, None, f"{type(exc).__name__}: {exc}", None


def _resolve_allowed_roots(roots: Iterable[str]) -> List[Path]:
    out: List[Path] = []
    for r in roots:
        out.append(Path(r).expanduser().resolve(strict=False))
    return out


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _existing_symlink_component(target: Path, allowed_roots: List[Path]) -> str | None:
    """Deny symlink target or symlink ancestors before opening/writing.

    This check intentionally walks the *lexical absolute path* without resolving
    symlinks first. A resolved path can turn a symlink escape into a generic
    path-escape result; the contract requires symlink authority to be surfaced
    explicitly.
    """
    absolute = target if target.is_absolute() else Path.cwd() / target
    absolute = Path(os.path.abspath(str(absolute)))
    parts = absolute.parts
    for i in range(1 if absolute.is_absolute() else 0, len(parts) + 1):
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
    except Exception as exc:  # noqa: BLE001 - durability support differs by platform/fs
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def _write_json_receipt(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
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
        "artifact_type": "AtomicJsonWriteDecisionPacket.v1",
        "writer_version": VERSION,
        "created_utc": _utc_now(),
        "operation_id": envelope.get("operation_id"),
        "status": "UNSET",
        "ok": False,
        "deny_reason": None,
        "error_type": None,
        "target_path": envelope.get("target_path"),
        "resolved_target_path": None,
        "allowed_roots": envelope.get("allowed_roots", []),
        "target_sha256": None,
        "bytes_written": 0,
        "temp_path_used": None,
        "fsync_file": False,
        "fsync_parent": {"attempted": False, "ok": False, "error": None},
        "readback_ok": False,
        "failure_event_path": None,
        "receipt_path": None,
    }


def _emit_failure_event(envelope: Dict[str, Any], decision: Dict[str, Any]) -> str | None:
    receipt_dir = envelope.get("receipt_dir")
    if not receipt_dir:
        return None
    rid = envelope.get("operation_id") or "atomic_json_write"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(rid))[:96]
    path = Path(receipt_dir) / f"{safe}_failure_event.json"
    event = {
        "artifact_type": "AtomicJsonWriteFailureEvent.v1",
        "created_utc": _utc_now(),
        "operation_id": envelope.get("operation_id"),
        "writer_version": VERSION,
        "status": decision.get("status"),
        "deny_reason": decision.get("deny_reason"),
        "error_type": decision.get("error_type"),
        "target_path": envelope.get("target_path"),
        "resolved_target_path": decision.get("resolved_target_path"),
        "classification": _classify_failure(decision),
    }
    _write_json_receipt(path, event)
    return str(path)


def _emit_decision(envelope: Dict[str, Any], decision: Dict[str, Any]) -> str | None:
    receipt_dir = envelope.get("receipt_dir")
    if not receipt_dir:
        return None
    rid = envelope.get("operation_id") or "atomic_json_write"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(rid))[:96]
    path = Path(receipt_dir) / f"{safe}_decision_packet.json"
    decision["receipt_path"] = str(path)
    _write_json_receipt(path, decision)
    return str(path)


def _classify_failure(decision: Dict[str, Any]) -> str:
    status = decision.get("status")
    mapping = {
        "DENY_SCHEMA_INVALID": "schema_invalid",
        "DENY_PATH_ESCAPE": "path_escape",
        "DENY_SYMLINK": "symlink_blocked",
        "DENY_SUFFIX": "unsafe_suffix",
        "DENY_EXISTS": "unsafe_overwrite_mode",
        "DENY_SERIALIZATION": "serialization_failure",
        "DENY_SIZE_LIMIT": "payload_size_limit",
        "WRITE_ERROR": "atomic_write_error",
        "READBACK_ERROR": "readback_error",
    }
    return mapping.get(str(status), "unknown_atomic_json_failure")


def _finalize(envelope: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    if not decision.get("ok"):
        decision["failure_event_path"] = _emit_failure_event(envelope, decision)
    _emit_decision(envelope, decision)
    return decision


def write_atomic_json(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Write JSON atomically according to AtomicJsonWriteEnvelope.v1.

    Required envelope fields:
      operation_id: stable id for receipts
      target_path: output JSON file path
      payload: JSON-serializable object
      allowed_roots: list of root directories the resolved target may live under
    Optional fields:
      create_parent: bool, default false
      overwrite_mode: replace | create_new | deny_if_exists, default replace
      allowed_suffixes: default [.json]
      max_bytes: default 2_000_000
      indent: int|null, default 2
      sort_keys: bool, default true
      ensure_ascii: bool, default false
      receipt_dir: optional decision/failure receipt location
    """
    decision = _base_decision(envelope if isinstance(envelope, dict) else {})
    if not isinstance(envelope, dict):
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="envelope_not_object", error_type="TypeError")
        return _finalize({}, decision)

    required = ["operation_id", "target_path", "payload", "allowed_roots"]
    missing = [k for k in required if k not in envelope]
    if missing:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason=f"missing_required_fields:{','.join(missing)}", error_type="SchemaError")
        return _finalize(envelope, decision)
    if not isinstance(envelope.get("allowed_roots"), list) or not envelope["allowed_roots"]:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="allowed_roots_must_be_nonempty_list", error_type="SchemaError")
        return _finalize(envelope, decision)

    try:
        target_raw = Path(str(envelope["target_path"])).expanduser()
        raw_absolute = target_raw if target_raw.is_absolute() else Path.cwd() / target_raw
        allowed_roots = _resolve_allowed_roots(envelope["allowed_roots"])
        raw_symlink_component = _existing_symlink_component(raw_absolute, allowed_roots)
        if raw_symlink_component:
            decision["resolved_target_path"] = str(raw_absolute)
            decision.update(status="DENY_SYMLINK", deny_reason=f"symlink_component:{raw_symlink_component}", error_type="SymlinkBlocked")
            return _finalize(envelope, decision)
        target = target_raw.resolve(strict=False)
        decision["resolved_target_path"] = str(target)
    except Exception as exc:  # noqa: BLE001
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="path_resolution_failed", error_type=f"{type(exc).__name__}: {exc}")
        return _finalize(envelope, decision)

    if not any(_is_relative_to(target, root) for root in allowed_roots):
        decision.update(status="DENY_PATH_ESCAPE", deny_reason="resolved_target_outside_allowed_roots", error_type="PathEscape")
        return _finalize(envelope, decision)

    allowed_suffixes = envelope.get("allowed_suffixes", DEFAULT_ALLOWED_SUFFIXES)
    if not isinstance(allowed_suffixes, list) or not all(isinstance(s, str) and s.startswith(".") for s in allowed_suffixes):
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="allowed_suffixes_invalid", error_type="SchemaError")
        return _finalize(envelope, decision)
    if target.suffix not in allowed_suffixes:
        decision.update(status="DENY_SUFFIX", deny_reason=f"suffix_not_allowed:{target.suffix}", error_type="UnsafeSuffix")
        return _finalize(envelope, decision)

    symlink_component = _existing_symlink_component(target, allowed_roots)
    if symlink_component:
        decision.update(status="DENY_SYMLINK", deny_reason=f"symlink_component:{symlink_component}", error_type="SymlinkBlocked")
        return _finalize(envelope, decision)

    create_parent = bool(envelope.get("create_parent", False))
    if not target.parent.exists():
        if not create_parent:
            decision.update(status="DENY_SCHEMA_INVALID", deny_reason="parent_missing_and_create_parent_false", error_type="ParentMissing")
            return _finalize(envelope, decision)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # noqa: BLE001
            decision.update(status="WRITE_ERROR", deny_reason="parent_create_failed", error_type=f"{type(exc).__name__}: {exc}")
            return _finalize(envelope, decision)

    if _existing_symlink_component(target, allowed_roots):
        decision.update(status="DENY_SYMLINK", deny_reason="symlink_component_after_parent_create", error_type="SymlinkBlocked")
        return _finalize(envelope, decision)

    overwrite_mode = envelope.get("overwrite_mode", "replace")
    if overwrite_mode not in {"replace", "create_new", "deny_if_exists"}:
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="invalid_overwrite_mode", error_type="SchemaError")
        return _finalize(envelope, decision)
    if target.exists() and overwrite_mode in {"create_new", "deny_if_exists"}:
        decision.update(status="DENY_EXISTS", deny_reason="target_exists_overwrite_denied", error_type="TargetExists")
        return _finalize(envelope, decision)

    indent = envelope.get("indent", 2)
    if indent is not None and not isinstance(indent, int):
        decision.update(status="DENY_SCHEMA_INVALID", deny_reason="indent_must_be_int_or_null", error_type="SchemaError")
        return _finalize(envelope, decision)
    sort_keys = bool(envelope.get("sort_keys", True))
    ensure_ascii = bool(envelope.get("ensure_ascii", False))
    ok, text, err, reparsed = _json_ready(envelope.get("payload"), indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)
    if not ok or text is None:
        decision.update(status="DENY_SERIALIZATION", deny_reason="payload_not_json_serializable_or_nonfinite", error_type=err)
        return _finalize(envelope, decision)

    max_bytes = int(envelope.get("max_bytes", DEFAULT_MAX_BYTES))
    data = text.encode("utf-8")
    if len(data) > max_bytes:
        decision.update(status="DENY_SIZE_LIMIT", deny_reason=f"serialized_size_exceeds_limit:{len(data)}>{max_bytes}", error_type="SizeLimit")
        return _finalize(envelope, decision)

    tmp_path: Path | None = None
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent), text=False)
        tmp_path = Path(tmp_name)
        decision["temp_path_used"] = str(tmp_path)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            decision["fsync_file"] = True
        if overwrite_mode == "create_new" and target.exists():
            raise FileExistsError(str(target))
        os.replace(str(tmp_path), str(target))
        decision["fsync_parent"] = _safe_parent_fsync(target.parent)
        final_bytes = target.read_bytes()
        final_payload = json.loads(final_bytes.decode("utf-8"))
        if final_payload != reparsed:
            decision.update(status="READBACK_ERROR", deny_reason="readback_payload_mismatch", error_type="ReadbackMismatch")
            return _finalize(envelope, decision)
        decision.update(
            status="ALLOW_SUCCESS",
            ok=True,
            target_sha256=_sha256_bytes(final_bytes),
            bytes_written=len(final_bytes),
            readback_ok=True,
        )
        return _finalize(envelope, decision)
    except Exception as exc:  # noqa: BLE001
        decision.update(status="WRITE_ERROR", deny_reason="atomic_replace_failed", error_type=f"{type(exc).__name__}: {exc}")
        return _finalize(envelope, decision)
    finally:
        if tmp_path is not None:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass


# Backwards-friendly alias for callers that prefer a verb phrase.
write_json_atomic = write_atomic_json
