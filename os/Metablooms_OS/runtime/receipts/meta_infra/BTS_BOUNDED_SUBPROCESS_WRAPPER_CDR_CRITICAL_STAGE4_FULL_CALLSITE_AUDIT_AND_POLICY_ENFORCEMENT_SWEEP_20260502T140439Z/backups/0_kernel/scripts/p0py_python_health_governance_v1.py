#!/usr/bin/env python3
"""P0PY Python Health Governance Gate v1.1.

Stdlib-only gate. Must be launched with python3 -S. It probes the sandbox
Python startup lanes and writes an auditable decision record that downstream
stages can use to quarantine normal Python while preserving a safe stdlib lane.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

GATE_ID = "P0PY_PYTHON_HEALTH"
VERSION = "1.1.0"
ROOT = Path(os.environ.get("METABLOOMS_ROOT", "/mnt/data/Metablooms_OS"))
DEFAULT_STATE = ROOT / "runtime/governance/python_health/PYTHON_HEALTH_STATE_v1.json"
DEFAULT_DECISIONS = ROOT / "runtime/governance/decision_logs/python_health"
POLICY_PATH = ROOT / "runtime/governance/PYTHON_RESILIENT_EXECUTION_POLICY_v1.json"
LAUNCHER_PATH = ROOT / "runtime/governance/python3_S_lane_exec_v1.sh"

THRESHOLDS = {
    "python3_S_max_ms": 500,
    "normal_warn_ms": 800,
    "normal_quarantine_ms": 1400,
    "normal_timeout_s": 8,
}

WORK_ROUTES = {
    "file_audit": "shell_coreutils",
    "zip_ops": "shell_coreutils",
    "sha_verify": "shell_coreutils",
    "json_read": "python3_dash_S_stdlib",
    "json_write": "python3_dash_S_stdlib",
    "schema_validate": "python3_dash_S_stdlib",
    "stdlib_python": "python3_dash_S_stdlib",
    "external_package_python": "normal_python_quarantine_with_timeout_only",
    "html_generation": "node_or_static_artifact",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def launched_with_no_site() -> bool:
    return bool(getattr(sys.flags, "no_site", 0)) and "site" not in sys.modules


def run_timed(cmd: List[str], timeout_s: int) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr_excerpt": proc.stderr.strip()[:800],
            "elapsed_ms": elapsed_ms,
            "timeout": False,
            "available": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr_excerpt": (exc.stderr or "").strip()[:800] if isinstance(exc.stderr, str) else "",
            "elapsed_ms": elapsed_ms,
            "timeout": True,
            "available": False,
        }
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return {
            "cmd": cmd,
            "returncode": None,
            "stdout": "",
            "stderr_excerpt": repr(exc),
            "elapsed_ms": elapsed_ms,
            "timeout": False,
            "available": False,
        }


def inspect_normal_python_risk() -> Dict[str, Any]:
    """Inspect normal-python startup risk without executing normal python.

    The sandbox regression can leave artifact-tool daemon FDs open after a normal
    python startup, which makes the caller hang even when the child process exits.
    R8 therefore treats normal-python execution as a quarantined lane unless an
    operator explicitly opts into an unsafe probe.
    """
    pth = Path("/opt/pyvenv/lib/python3.13/site-packages/000_oai_py_sys_path_prepend.pth")
    hook = Path("/opt/python-hooks/sitecustomize.py")
    artifact_pkg = Path("/opt/pyvenv/lib/python3.13/site-packages/presentation_artifact_tool")
    findings = ROOT / "receipts/python_probe/PYTHON_SANDBOX_FINDINGS_20260428T011802Z.json"
    evidence = {
        "pth_exists": pth.exists(),
        "sitecustomize_exists": hook.exists(),
        "presentation_artifact_tool_exists": artifact_pkg.exists(),
        "prior_findings_receipt_exists": findings.exists(),
        "unsafe_normal_probe_executed": False,
        "risk_basis": "hook-chain inspection plus prior same-runtime forensic receipts; normal python execution is intentionally not run by default",
    }
    if findings.exists():
        evidence["prior_findings_sha256"] = sha256_path(findings)
    risk = evidence["pth_exists"] and evidence["sitecustomize_exists"] and evidence["presentation_artifact_tool_exists"]
    return {
        "available": False if risk else None,
        "elapsed_ms": 999999 if risk else -1,
        "stdout": json.dumps({"site_loaded": True, "risk_inspected_without_execution": True}),
        "timeout": False,
        "risk_quarantined_without_execution": bool(risk),
        "evidence": evidence,
    }


def live_probe() -> Dict[str, Any]:
    py_s = run_timed([
        "python3", "-S", "-c",
        "import sys,json; print(json.dumps({'no_site': bool(sys.flags.no_site), 'site_loaded': 'site' in sys.modules}))"
    ], timeout_s=5)
    normal = inspect_normal_python_risk()
    return {"python3_dash_S": py_s, "python3_normal": normal}


def simulated_probe(request: Dict[str, Any]) -> Dict[str, Any]:
    probe = request.get("simulated_probe")
    if not isinstance(probe, dict):
        raise ValueError("simulated mode requires object field simulated_probe")
    return probe


def classify(probe: Dict[str, Any]) -> Tuple[str, List[str], List[str], Dict[str, str]]:
    blocks: List[str] = []
    warnings: List[str] = []
    py_s = probe.get("python3_dash_S", {})
    normal = probe.get("python3_normal", {})

    if not py_s.get("available"):
        blocks.append("python3 -S lane unavailable")
    if float(py_s.get("elapsed_ms", 999999)) > THRESHOLDS["python3_S_max_ms"]:
        blocks.append("python3 -S lane exceeds max startup threshold")
    stdout = py_s.get("stdout", "")
    try:
        parsed_stdout = json.loads(stdout) if stdout else {}
    except Exception:
        parsed_stdout = {}
    if parsed_stdout.get("site_loaded") is True:
        blocks.append("python3 -S probe shows site module loaded")
    if parsed_stdout and parsed_stdout.get("no_site") is not True:
        blocks.append("python3 -S probe does not report no_site=true")

    normal_ms = float(normal.get("elapsed_ms", 999999))
    if normal.get("timeout"):
        status = "normal_python_unavailable_or_hung"
        warnings.append("normal python timed out; quarantine normal-python lane")
    elif normal.get("risk_quarantined_without_execution"):
        status = "normal_python_quarantined_without_execution"
        warnings.append("normal python hook-chain risk detected; quarantined without executing normal python")
    elif not normal.get("available"):
        status = "normal_python_unavailable_or_failed"
        warnings.append("normal python failed; quarantine normal-python lane")
    elif normal_ms >= THRESHOLDS["normal_quarantine_ms"]:
        status = "normal_python_expensive_quarantine"
        warnings.append("normal python exceeds quarantine startup threshold")
    elif normal_ms >= THRESHOLDS["normal_warn_ms"]:
        status = "normal_python_degraded_prefer_safe_lane"
        warnings.append("normal python exceeds warning startup threshold")
    else:
        status = "healthy_but_safe_lane_preferred"

    routes = dict(WORK_ROUTES)
    if status == "healthy_but_safe_lane_preferred":
        routes["external_package_python"] = "normal_python_with_timeout_allowed_if_declared"

    return status, blocks, warnings, routes


def build_decision(request: Dict[str, Any], probe: Dict[str, Any], mode: str) -> Dict[str, Any]:
    status, blocks, warnings, routes = classify(probe)
    policy_hash = sha256_path(POLICY_PATH) if POLICY_PATH.exists() else None
    launcher_hash = sha256_path(LAUNCHER_PATH) if LAUNCHER_PATH.exists() else None
    target = request.get("target_work_type", "governed_stage_python_routing")
    decision = "deny" if blocks else "allow_with_route_controls"
    did_src = f"{GATE_ID}|{utc_now()}|{target}|{status}|{len(blocks)}|{len(warnings)}"
    return {
        "decision_id": hashlib.sha256(did_src.encode("utf-8")).hexdigest()[:24],
        "gate_id": GATE_ID,
        "version": VERSION,
        "created_utc": utc_now(),
        "mode": mode,
        "decision": decision,
        "python_health_status": status,
        "blocks": blocks,
        "warnings": warnings,
        "target_work_type": target,
        "required_launcher": "runtime/governance/python3_S_lane_exec_v1.sh",
        "launched_with_no_site": launched_with_no_site(),
        "policy_path": str(POLICY_PATH),
        "policy_sha256": policy_hash,
        "launcher_path": str(LAUNCHER_PATH),
        "launcher_sha256": launcher_hash,
        "thresholds": THRESHOLDS,
        "probe": probe,
        "routing_recommendation": routes,
        "policy_basis": [
            "normal python is quarantined when startup is degraded, expensive, failed, or hung",
            "governed stdlib Python work must use python3 -S launcher",
            "normal python may only be used for declared site-package dependency with timeout and independent verification",
        ],
    }


def load_request(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {"target_work_type": "governed_stage_python_routing"}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("request JSON must be an object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="MetaBlooms P0PY Python health gate")
    parser.add_argument("--request-json")
    parser.add_argument("--state-path", default=str(DEFAULT_STATE))
    parser.add_argument("--decision-dir", default=str(DEFAULT_DECISIONS))
    parser.add_argument("--mode", choices=["live", "simulated"], default="live")
    parser.add_argument("--report", help="optional explicit report path")
    args = parser.parse_args()

    if not launched_with_no_site():
        denied = {
            "decision_id": hashlib.sha256(f"{GATE_ID}|bad-launch|{time.time()}".encode()).hexdigest()[:24],
            "gate_id": GATE_ID,
            "version": VERSION,
            "created_utc": utc_now(),
            "decision": "deny",
            "blocks": ["gate must be launched with python3 -S; site module must not be preloaded"],
            "warnings": [],
            "launched_with_no_site": False,
        }
        out = Path(args.report) if args.report else DEFAULT_DECISIONS / f"P0PY_DECISION_BAD_LAUNCH_{int(time.time())}.json"
        write_json_atomic(out, denied)
        print(json.dumps(denied, indent=2, sort_keys=True))
        return 2

    request = load_request(args.request_json)
    probe = live_probe() if args.mode == "live" else simulated_probe(request)
    decision = build_decision(request, probe, args.mode)
    state_path = Path(args.state_path)
    write_json_atomic(state_path, decision)
    out = Path(args.report) if args.report else Path(args.decision_dir) / f"P0PY_DECISION_{decision['decision_id']}.json"
    write_json_atomic(out, decision)
    print(json.dumps(decision, indent=2, sort_keys=True))
    return 0 if decision["decision"] != "deny" else 2


if __name__ == "__main__":
    raise SystemExit(main())
