#!/usr/bin/env python3
"""Compatibility helpers for MetaBlooms canonical atomic JSON writer v1.

This module is intentionally thin: legacy callers can replace local ad-hoc
atomic/write_json helpers with write_json_file(...) while the actual authority
remains atomic_json_writer_v1.write_atomic_json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_IO_DIR = Path(__file__).resolve().parent
if str(_IO_DIR) not in sys.path:
    sys.path.insert(0, str(_IO_DIR))
from atomic_json_writer_v1 import write_atomic_json  # noqa: E402

DEFAULT_ROOT = Path('/mnt/data').resolve()

def utc_now() -> str:
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())

def default_allowed_roots_for(path: Path, extra: Optional[Iterable[str]] = None) -> List[str]:
    roots = [str(DEFAULT_ROOT)]
    path = Path(path)
    try:
        roots.append(str(path.resolve(strict=False).parent))
    except Exception:
        roots.append(str(path.parent))
    if extra:
        roots.extend(str(x) for x in extra)
    seen=[]
    for r in roots:
        if r not in seen:
            seen.append(r)
    return seen

def write_json_file(
    path: str | Path,
    payload: Any,
    *,
    operation_id: str = 'legacy_json_write',
    receipt_dir: str | Path | None = None,
    allowed_roots: Optional[Iterable[str]] = None,
    create_parent: bool = True,
    overwrite_mode: str = 'replace',
    indent: int | None = 2,
    sort_keys: bool = True,
    ensure_ascii: bool = False,
    max_bytes: int = 2_000_000,
) -> Dict[str, Any]:
    target = Path(path)
    envelope = {
        'operation_id': operation_id,
        'target_path': str(target),
        'payload': payload,
        'allowed_roots': list(allowed_roots) if allowed_roots is not None else default_allowed_roots_for(target),
        'create_parent': create_parent,
        'overwrite_mode': overwrite_mode,
        'indent': indent,
        'sort_keys': sort_keys,
        'ensure_ascii': ensure_ascii,
        'max_bytes': max_bytes,
    }
    if receipt_dir:
        envelope['receipt_dir'] = str(receipt_dir)
    decision = write_atomic_json(envelope)
    if not decision.get('ok'):
        raise RuntimeError(f"atomic_json_write_failed:{decision.get('status')}:{decision.get('deny_reason') or decision.get('error_type')}")
    return decision

def write_json_result(path: str | Path, payload: Any, *, operation_id: str = 'legacy_json_result') -> Dict[str, Any]:
    return write_json_file(path, payload, operation_id=operation_id)

def dumps_for_stdout(payload: Any, *, indent: int | None = 2, sort_keys: bool = True) -> str:
    return json.dumps(payload, indent=indent, sort_keys=sort_keys, allow_nan=False)
