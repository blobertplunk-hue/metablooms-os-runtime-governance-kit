#!/usr/bin/env python3
"""Compatibility adapter for MetaBlooms bounded subprocess wrapper v1.

Provides subprocess.CompletedProcess-compatible execution for legacy callers while
routing actual process spawning through bounded_subprocess_wrapper_v1.
"""
from __future__ import annotations

import hashlib
import importlib.util
import os
import time
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def _find_runtime_root(start: Optional[Path] = None) -> Path:
    env_root = os.environ.get("METABLOOMS_RUNTIME_ROOT")
    if env_root:
        p = Path(env_root).expanduser().resolve()
        if (p / "0_kernel/lib/execution/bounded_subprocess_wrapper_v1.py").exists():
            return p
    p = (start or Path(__file__)).resolve()
    for candidate in [p] + list(p.parents):
        if (candidate / "0_kernel/lib/execution/bounded_subprocess_wrapper_v1.py").exists():
            return candidate
    return Path("/mnt/data/Metablooms_OS").resolve()


def _load_wrapper(root: Path):
    wrapper_path = root / "0_kernel/lib/execution/bounded_subprocess_wrapper_v1.py"
    spec = importlib.util.spec_from_file_location("bounded_subprocess_wrapper_v1", wrapper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load bounded wrapper from {wrapper_path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _packet_to_completed_process(cmd: List[str], packet: Dict[str, Any]) -> subprocess.CompletedProcess[str]:
    attempts = packet.get("attempts") or []
    last = attempts[-1] if attempts else {}
    result = packet.get("result_class")
    if result == "ALLOW_SUCCESS":
        rc = int(last.get("returncode", 0))
    elif result == "ALLOW_NONZERO":
        rc = int(last.get("returncode", 1))
    elif result in ("TIMEOUT_TERMINATED", "TIMEOUT_KILLED"):
        rc = 124
    elif result in ("DENY_FORBIDDEN_METHOD", "DENY_SCHEMA_INVALID", "DENY_SHELL_UNAPPROVED", "DENY_PATH_ESCAPE"):
        rc = 126
    elif result == "OUTPUT_LIMIT_EXCEEDED":
        rc = 125
    else:
        rc = 127
    stdout = last.get("stdout") or ""
    stderr = last.get("stderr") or ""
    if result not in ("ALLOW_SUCCESS", "ALLOW_NONZERO"):
        marker = f"\nMETABLOOMS_BOUNDED_SUBPROCESS_RESULT={result} FAILURE_CLASS={packet.get('failure_class')} DECISION_PACKET={packet.get('decision_packet_path')}"
        stderr = (stderr + marker).strip() + "\n"
    return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)


def run_compat(
    cmd: List[str],
    *,
    timeout_seconds: int = 10,
    cwd: Optional[str | Path] = None,
    operation_type: str = "legacy_subprocess_call",
    stage: str = "LEGACY_CALLER_RETROFIT",
    receipt_dir: Optional[str | Path] = None,
    allowed_roots: Optional[List[str]] = None,
    max_retries: int = 0,
    max_capture_bytes: int = 131072,
    env: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess[str]:
    if not isinstance(cmd, list) or not all(isinstance(x, str) and x for x in cmd):
        return subprocess.CompletedProcess(cmd, 126, stdout="", stderr="cmd must be a nonempty list[str]\n")
    root = _find_runtime_root()
    wrapper = _load_wrapper(root)
    cwd_path = Path(cwd).resolve() if cwd is not None else root
    if allowed_roots is None:
        allowed_roots = [str(root), "/mnt/data"]
    if receipt_dir is None:
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        cmd_hash = hashlib.sha256((operation_type + "\0" + "\0".join(cmd)).encode("utf-8", "replace")).hexdigest()[:12]
        receipt_dir = root / "runtime/receipts/bounded_subprocess_wrapper_v1/caller_compat" / f"{stage}_{operation_type}_{stamp}_{cmd_hash}"
    envelope = {
        "artifact_type": "METABLOOMS_BOUNDED_COMMAND_ENVELOPE_v1",
        "stage": stage,
        "operation_type": operation_type,
        "argv": cmd,
        "shell": False,
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "max_capture_bytes": max_capture_bytes,
        "cwd": str(cwd_path),
        "allowed_roots": allowed_roots,
        "receipt_dir": str(receipt_dir),
        "runtime_root": str(root),
    }
    if env:
        envelope["env"] = env
    packet = wrapper.run_governed_command(envelope)
    return _packet_to_completed_process(cmd, packet)

# subprocess.run-compatible facade for Stage4 callsite sweep.
def run(
    cmd,
    *,
    timeout=None,
    cwd=None,
    input=None,
    capture_output=False,
    text=None,
    encoding=None,
    errors=None,
    env=None,
    check=False,
    stdout=None,
    stderr=None,
    operation_type="retrofitted_subprocess_run",
    stage="BTS_BOUNDED_SUBPROCESS_WRAPPER_STAGE4_RETROFIT",
    receipt_dir=None,
    allowed_roots=None,
    max_retries=0,
    max_capture_bytes=131072,
    **kwargs,
):
    """Compatibility subset of subprocess.run routed through MetaBlooms wrapper.

    Unsupported stdin/input streaming is fail-closed as a CompletedProcess with rc=126.
    stdout/stderr redirection other than PIPE/None is not performed; output is always
    captured by the bounded wrapper and returned on the CompletedProcess.
    """
    if input is not None:
        return subprocess.CompletedProcess(cmd, 126, stdout="", stderr="input streaming is not supported by bounded_subprocess_compat_v1.run\n")
    if isinstance(cmd, tuple):
        cmd = list(cmd)
    if not isinstance(cmd, list):
        return subprocess.CompletedProcess(cmd, 126, stdout="", stderr="cmd must be list[str] or tuple[str,...] for bounded subprocess execution\n")
    if not all(isinstance(x, str) and x for x in cmd):
        return subprocess.CompletedProcess(cmd, 126, stdout="", stderr="cmd entries must be nonempty strings\n")
    timeout_seconds = 10 if timeout is None else min(max(float(timeout), 0.001), 30.0)
    env2 = None
    if env is not None:
        env2 = {str(k): str(v) for k, v in dict(env).items()}
    cp = run_compat(
        cmd,
        timeout_seconds=int(timeout_seconds) if timeout_seconds >= 1 else timeout_seconds,
        cwd=cwd,
        operation_type=operation_type,
        stage=stage,
        receipt_dir=receipt_dir,
        allowed_roots=allowed_roots,
        max_retries=max_retries,
        max_capture_bytes=max_capture_bytes,
        env=env2,
    )
    if check and cp.returncode != 0:
        raise subprocess.CalledProcessError(cp.returncode, cmd, output=cp.stdout, stderr=cp.stderr)
    return cp


def check_call(cmd, **kwargs):
    kwargs["check"] = True
    cp = run(cmd, **kwargs)
    return cp.returncode


def call(cmd, **kwargs):
    return run(cmd, **kwargs).returncode


def check_output(cmd, **kwargs):
    kwargs["check"] = True
    cp = run(cmd, **kwargs)
    return cp.stdout

