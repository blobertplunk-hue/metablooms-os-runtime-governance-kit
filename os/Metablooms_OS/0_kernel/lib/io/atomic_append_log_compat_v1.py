#!/usr/bin/env python3
"""Compatibility adapter for MetaBlooms atomic append-log writer v1.

Routes legacy JSONL/NDJSON append call sites through the governed canonical
append writer while preserving the caller's record fields and adding the
minimum schema fields required by AtomicAppendLogEnvelope.v1.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    from .atomic_append_log_writer_v1 import append_governed_jsonl_record
except ImportError:  # standalone sys.path shim import
    from atomic_append_log_writer_v1 import append_governed_jsonl_record

DEFAULT_ALLOWED_SUFFIXES = [".jsonl", ".log.jsonl", ".ledger.jsonl", ".events.jsonl", ".ndjson"]


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_id(prefix: str, path: Path, record: Dict[str, Any]) -> str:
    seed = json.dumps({"path": str(path), "record": record, "ts": time.time()}, sort_keys=True, default=str)
    return f"{prefix}_{hashlib.sha256(seed.encode()).hexdigest()[:16]}"


def normalize_legacy_record(record: Dict[str, Any], *, source: str, event_type: str, severity: str = "info") -> Dict[str, Any]:
    if not isinstance(record, dict):
        raise TypeError("append-log records must be dictionaries")
    out = dict(record)
    out.setdefault("schema_version", str(record.get("schema_version") or "MetaBloomsAppendLogRecord.v1"))
    out.setdefault("event_id", str(record.get("event_id") or record.get("trace_id") or record.get("span_id") or _safe_id("event", Path(source), record)))
    out.setdefault("timestamp_utc", str(record.get("timestamp_utc") or record.get("logged_utc") or record.get("created_utc") or _utc()))
    out.setdefault("source", source)
    out.setdefault("event_type", str(record.get("event_type") or record.get("event") or event_type))
    out.setdefault("severity", str(record.get("severity") or severity).lower())
    out.setdefault("payload", record.get("payload", {"legacy_record_keys": sorted(str(k) for k in record.keys())}))
    return out


def append_jsonl_record(
    path: str | Path,
    record: Dict[str, Any],
    *,
    operation_id: Optional[str] = None,
    allowed_roots: Optional[Iterable[str]] = None,
    receipt_dir: str | Path | None = None,
    source: str = "legacy_append_stream",
    event_type: str = "append_record",
    severity: str = "info",
    durability_mode: str = "sync_on_critical",
    durability_exception_authority: Optional[str] = None,
    create_parent: bool = True,
    max_record_bytes: int = 262_144,
    max_file_bytes: Optional[int] = None,
    allowed_suffixes: Optional[list[str]] = None,
) -> Dict[str, Any]:
    p = Path(path)
    roots = [str(Path(r).resolve()) for r in (allowed_roots or ["/mnt/data"])]
    normalized = normalize_legacy_record(record, source=source, event_type=event_type, severity=severity)
    envelope: Dict[str, Any] = {
        "schema_version": "AtomicAppendLogEnvelope.v1",
        "operation_id": operation_id or _safe_id("append", p, normalized),
        "log_path": str(p),
        "allowed_roots": roots,
        "record": normalized,
        "durability_mode": durability_mode,
        "create_parent": create_parent,
        "max_record_bytes": max_record_bytes,
        "allowed_suffixes": allowed_suffixes or DEFAULT_ALLOWED_SUFFIXES,
    }
    if receipt_dir is not None:
        envelope["receipt_dir"] = str(receipt_dir)
    if max_file_bytes is not None:
        envelope["max_file_bytes"] = max_file_bytes
    if durability_exception_authority:
        envelope["durability_exception_authority"] = durability_exception_authority
    decision = append_governed_jsonl_record(envelope)
    if not decision.get("ok"):
        raise RuntimeError(f"append-log write denied/failed: {decision.get('status')} {decision.get('deny_reason')}")
    return decision


append_jsonl = append_jsonl_record
