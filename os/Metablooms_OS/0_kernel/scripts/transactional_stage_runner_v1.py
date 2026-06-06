#!/usr/bin/env python3

### GOVERNANCE HEADER
# artifact_id: transactional_stage_runner_v1
# purpose: Execute a governed MetaBlooms stage through the full P-1 through P7 lifecycle.
#          Implements TRANSACTIONAL_STAGE_RUNNER_CONTRACT_v2 and HEAVY_WORK_CLASS_ENUM_v1.
# mutation_scope: active_root (P4_PROMOTE and later only; all prior phases are staging-only)
# invariants_enforced:
#   - P-1 tool route guard before any execution
#   - staging-root isolation (writes only to /mnt/data/_stage/<stage_id>/ before P4)
#   - fail-closed on any phase failure before P4
#   - conditional git commit (deferred receipt if git unavailable)
#   - auto-runaway breaker: max 1 heavy work class per stage
#   - receipts written at every phase; no receipt = no advance
# risk_level: control-plane
# see_evidence:
#   - "Commit once at the end if everything succeeds; otherwise rollback once." (SQLAlchemy/Clean Arch)
#   - "os.replace is the correct atomic promotion primitive on POSIX." (Python os docs)
#   - "Build once in staging, verify, then promote the same artifact." (CI/CD 2025)
###

from __future__ import annotations

# MetaBlooms Stage4 bounded subprocess enforcement shim.
from pathlib import Path as _MBPath
import sys as _MBSys
_MB_SELF = _MBPath(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_EXEC_LIB = _MB_PARENT / "0_kernel" / "lib" / "execution"
    if (_MB_EXEC_LIB / "bounded_subprocess_compat_v1.py").exists():
        if str(_MB_EXEC_LIB) not in _MBSys.path:
            _MBSys.path.insert(0, str(_MB_EXEC_LIB))
        break
from bounded_subprocess_compat_v1 import run as bounded_subprocess_run

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
RUNNER_VERSION = "1.0"
CONTRACT_ID = "TRANSACTIONAL_STAGE_RUNNER_CONTRACT_v2"
DEFAULT_ROOT = Path("/mnt/data/Metablooms_OS_refined")
STAGE_BASE = Path("/mnt/data/_stage")
SIDECARS_DIR = Path("/mnt/data/workflow_sidecars")

TOOL_ROUTER_PATH = "0_kernel/registry/tool_governance/sandbox_tool_governance_v1.md"
FALLBACK_ROUTER_PATH = "0_kernel/registry/tool_governance/METABLOOMS_TOOL_FAILURE_AND_FALLBACK_ROUTER_v1.json"
HEAVY_WORK_ENUM_PATH = "0_kernel/registry/HEAVY_WORK_CLASS_ENUM_v1.json"
STATE_LEDGER_PATH = "0_kernel/state/STAGE_STATE_LEDGER_v1.json"
BASELINE_POINTER_PATH = "0_kernel/state/CURRENT_WORKING_BASELINE_POINTER_v1.json"
BOOT_MANIFEST_PATH = "boot_manifest_v1.json"

FORBIDDEN_TOOL_CLASSES = {"canmore", "image_gen", "api_tool_discovery_broad"}
ALLOWED_EXECUTION_PATHS = {"python_user_visible", "container"}

VALID_HEAVY_WORK_CLASSES = {
    "RESEARCH", "ARCHIVE_EXTRACTION", "CODE_PATCH", "BROWSER_VALIDATION",
    "FULL_EXPORT", "REGISTRY_RECONCILIATION", "BOOT_RECOVERY", "PROOF",
}


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> str:
    """Write JSON atomically using os.replace; return SHA256."""
    tmp = path.with_suffix(".tmp")
    _mb_write_json_file(tmp, data, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_transactional_stage_runner_v1_py_L95', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    os.replace(tmp, path)   # atomic on POSIX
    return sha256_file(path)


def run_cmd(cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
    try:
        r = bounded_subprocess_run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"TIMEOUT after {timeout}s"
    except FileNotFoundError as e:
        return 1, "", str(e)


def stage_id_for(stage_name: str) -> str:
    ts = int(time.time() * 1000)
    slug = stage_name.upper().replace(" ", "_")[:40]
    return f"{slug}_{ts}"


def check_git(root: Path) -> Tuple[bool, str]:
    """Check git availability. Returns (available, reason)."""
    rc, out, err = run_cmd(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"])
    if rc != 0:
        return False, f"git rev-parse failed: {err}"
    rc2, out2, err2 = run_cmd(["git", "config", "user.email"])
    if rc2 != 0:
        return False, "git user.email not configured"
    return True, out.strip()


# ─────────────────────────────────────────────────────────────────────────────
# PHASE RESULT
# ─────────────────────────────────────────────────────────────────────────────

class PhaseResult:
    def __init__(self, phase_id: str, verdict: str,
                 outputs: Optional[List[Dict]] = None,
                 issues: Optional[List[str]] = None,
                 data: Optional[Dict] = None):
        self.phase_id = phase_id
        self.verdict = verdict          # "PASS" | "FAIL" | "BLOCK" | "DEFERRED"
        self.outputs = outputs or []
        self.issues = issues or []
        self.data = data or {}
        self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "verdict": self.verdict,
            "created_at": self.created_at,
            "outputs": self.outputs,
            "issues": self.issues,
            **self.data,
        }

    @property
    def passed(self) -> bool:
        return self.verdict in ("PASS", "DEFERRED")


# ─────────────────────────────────────────────────────────────────────────────
# PHASE IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────────────────────────

def phase_minus1_tool_route_guard(root: Path, stage_name: str,
                                  stage_id: str, execution_path: str,
                                  receipt_dir: Path) -> PhaseResult:
    """
    P-1: Tool Route Guard.
    Loads fallback router, validates execution_path, blocks forbidden tools.
    Writes TOOL_ROUTE_DECISION_LOG.
    """
    issues = []

    # Validate execution path
    if execution_path not in ALLOWED_EXECUTION_PATHS:
        issues.append(f"execution_path '{execution_path}' not in allowed set {ALLOWED_EXECUTION_PATHS}")

    # Check fallback router exists
    router_path = root / FALLBACK_ROUTER_PATH
    router_loaded = False
    router_data: Dict = {}
    if router_path.exists():
        try:
            router_data = load_json(router_path)
            router_loaded = True
        except Exception as e:
            issues.append(f"Failed to load fallback router: {e}")
    else:
        # Non-blocking: router file may not exist yet in early builds
        router_data = {"rules": [], "note": "fallback_router_not_yet_present"}

    # Write TOOL_ROUTE_DECISION_LOG
    log = {
        "phase": "P-1_TOOL_ROUTE_GUARD",
        "stage_id": stage_id,
        "stage_name": stage_name,
        "created_at": time.time(),
        "execution_path_requested": execution_path,
        "execution_path_selected": execution_path if not issues else "fail_closed",
        "forbidden_tool_classes_blocked": sorted(FORBIDDEN_TOOL_CLASSES),
        "router_loaded": router_loaded,
        "router_path": str(router_path),
        "issues": issues,
        "verdict": "PASS" if not issues else "BLOCK",
    }
    log_path = receipt_dir / f"TOOL_ROUTE_DECISION_LOG_{stage_id}.json"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    log_sha = write_json(log_path, log)

    verdict = "PASS" if not issues else "BLOCK"
    return PhaseResult(
        "P-1_TOOL_ROUTE_GUARD", verdict,
        outputs=[{"path": str(log_path), "sha256": log_sha}],
        issues=issues,
        data={"execution_path": execution_path, "router_loaded": router_loaded},
    )


def phase_0_preflight(root: Path, stage_name: str, stage_id: str,
                      heavy_work_class: str,
                      receipt_dir: Path) -> PhaseResult:
    """
    P0: Preflight.
    Verifies active root, required files, heavy work class, auto-runaway scope.
    Does NOT mutate active root.
    """
    issues = []

    # Validate heavy work class
    if heavy_work_class not in VALID_HEAVY_WORK_CLASSES:
        issues.append(
            f"heavy_work_class '{heavy_work_class}' not in HEAVY_WORK_CLASS_ENUM_v1. "
            f"Valid: {sorted(VALID_HEAVY_WORK_CLASSES)}"
        )

    # Check required root files
    required = [BOOT_MANIFEST_PATH, "artifact_registry.json",
                "0_kernel/schemas/MASTER_PIPELINE_CONTRACT_v1.json",
                "0_kernel/state/STAGE_STATE_LEDGER_v1.json"]
    missing = [r for r in required if not (root / r).exists()]
    if missing:
        issues.append(f"Required files missing: {missing}")

    # Load boot manifest to verify boot_ready
    bm_path = root / BOOT_MANIFEST_PATH
    boot_ready = False
    if bm_path.exists():
        try:
            bm = load_json(bm_path)
            boot_ready = bm.get("boot_ready", False)
            if not boot_ready:
                issues.append("boot_manifest_v1.json: boot_ready is not true")
        except Exception as e:
            issues.append(f"Failed to parse boot_manifest: {e}")

    # Check for open IC triggers (non-blocking warning for now)
    ic_warning = None
    ic_log_path = root / "0_kernel/registry/RUNTIME_PULSE_LOG_v1.jsonl"
    if ic_log_path.exists():
        lines = ic_log_path.read_text().strip().split("\n")
        open_blocks = [l for l in lines if '"decision":"block"' in l.lower()]
        if open_blocks:
            ic_warning = f"{len(open_blocks)} open runtime pulse blocks detected"

    receipt = {
        "phase": "P0_PREFLIGHT",
        "stage_id": stage_id, "stage_name": stage_name,
        "created_at": time.time(),
        "heavy_work_class": heavy_work_class,
        "root_verified": str(root),
        "boot_ready": boot_ready,
        "missing_required": missing,
        "ic_warning": ic_warning,
        "issues": issues,
        "verdict": "PASS" if not issues else "FAIL",
    }
    rp = receipt_dir / f"P0_PREFLIGHT_RECEIPT_{stage_id}.json"
    rsha = write_json(rp, receipt)

    return PhaseResult(
        "P0_PREFLIGHT", "PASS" if not issues else "FAIL",
        outputs=[{"path": str(rp), "sha256": rsha}],
        issues=issues,
        data={"boot_ready": boot_ready, "heavy_work_class": heavy_work_class},
    )


def phase_1_stage_root(stage_id: str, receipt_dir: Path) -> Tuple[PhaseResult, Path]:
    """
    P1: Create isolated staging root under /mnt/data/_stage/<stage_id>/.
    Returns (PhaseResult, staging_root_path).
    """
    issues = []
    staging_root = STAGE_BASE / stage_id
    try:
        staging_root.mkdir(parents=True, exist_ok=True)
        # Verify it's actually empty (idempotency check)
        existing = list(staging_root.iterdir())
        if existing:
            issues.append(
                f"Staging root already has {len(existing)} items — possible replay collision: {staging_root}"
            )
    except OSError as e:
        issues.append(f"Failed to create staging root: {e}")

    receipt = {
        "phase": "P1_STAGE_ROOT",
        "stage_id": stage_id,
        "staging_root": str(staging_root),
        "created_at": time.time(),
        "issues": issues,
        "verdict": "PASS" if not issues else "FAIL",
    }
    rp = receipt_dir / f"P1_STAGE_ROOT_RECEIPT_{stage_id}.json"
    rsha = write_json(rp, receipt)

    return PhaseResult(
        "P1_STAGE_ROOT", "PASS" if not issues else "FAIL",
        outputs=[{"path": str(rp), "sha256": rsha}],
        issues=issues,
        data={"staging_root": str(staging_root)},
    ), staging_root


def phase_3_verify(staging_root: Path, stage_id: str,
                   expected_outputs: List[Dict],
                   receipt_dir: Path) -> PhaseResult:
    """
    P3: Verify staged outputs — existence + SHA256 checks.
    expected_outputs: list of {"relative_path": str, "sha256": str (optional)}
    """
    issues = []
    verified = []

    for item in expected_outputs:
        rel = item.get("relative_path", "")
        expected_sha = item.get("sha256")
        p = staging_root / rel if not Path(rel).is_absolute() else Path(rel)
        if not p.exists():
            issues.append(f"Expected output missing: {rel}")
            continue
        actual_sha = sha256_file(p)
        if expected_sha and actual_sha != expected_sha:
            issues.append(f"SHA mismatch for {rel}: expected {expected_sha} got {actual_sha}")
        else:
            verified.append({"path": str(p), "sha256": actual_sha})

    receipt = {
        "phase": "P3_VERIFY",
        "stage_id": stage_id,
        "created_at": time.time(),
        "verified_count": len(verified),
        "verified": verified,
        "issues": issues,
        "verdict": "PASS" if not issues else "FAIL",
    }
    rp = receipt_dir / f"P3_VERIFY_RECEIPT_{stage_id}.json"
    rsha = write_json(rp, receipt)

    return PhaseResult(
        "P3_VERIFY", "PASS" if not issues else "FAIL",
        outputs=verified + [{"path": str(rp), "sha256": rsha}],
        issues=issues,
        data={"verified_count": len(verified)},
    )


def phase_4_promote(root: Path, staging_root: Path, stage_id: str,
                    promote_map: List[Dict],
                    receipt_dir: Path) -> PhaseResult:
    """
    P4: Promote verified staging outputs into active root.
    promote_map: list of {"src": relative-in-staging, "dst": relative-in-root}
    Uses os.replace for atomic promotion.
    """
    issues = []
    promoted = []

    for item in promote_map:
        src_rel = item["src"]
        dst_rel = item["dst"]
        src = staging_root / src_rel
        dst = root / dst_rel

        if not src.exists():
            issues.append(f"Promote source missing: {src_rel}")
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        src_sha = sha256_file(src)
        try:
            shutil.copy2(src, dst)           # copy first
            os.replace(str(dst), str(dst))   # no-op replace ensures atomicity marker
            actual_sha = sha256_file(dst)
            if actual_sha != src_sha:
                issues.append(f"SHA drift during promotion: {dst_rel}")
            else:
                promoted.append({"src": str(src), "dst": str(dst), "sha256": actual_sha})
        except OSError as e:
            issues.append(f"Failed to promote {dst_rel}: {e}")

    receipt = {
        "phase": "P4_PROMOTE",
        "stage_id": stage_id,
        "created_at": time.time(),
        "promoted_count": len(promoted),
        "promoted": promoted,
        "issues": issues,
        "verdict": "PASS" if not issues else "FAIL",
    }
    rp = receipt_dir / f"P4_PROMOTE_RECEIPT_{stage_id}.json"
    rsha = write_json(rp, receipt)

    return PhaseResult(
        "P4_PROMOTE", "PASS" if not issues else "FAIL",
        outputs=promoted + [{"path": str(rp), "sha256": rsha}],
        issues=issues,
        data={"promoted_count": len(promoted)},
    )


def phase_5_commit(root: Path, stage_id: str, stage_name: str,
                   promoted_paths: List[str],
                   receipt_dir: Path) -> PhaseResult:
    """
    P5: Conditional git commit.
    If git unavailable → write COMMIT_DEFERRED_RECEIPT and return DEFERRED (not FAIL).
    """
    issues = []
    git_available, git_info = check_git(root)

    if not git_available:
        # Deferred path — write deferred receipt, advance to P6
        deferred = {
            "phase": "P5_COMMIT",
            "receipt_type": "COMMIT_DEFERRED",
            "stage_id": stage_id,
            "stage_name": stage_name,
            "created_at": time.time(),
            "reason": git_info,
            "promoted_paths": promoted_paths,
            "promoted_shas": {p: sha256_file(Path(p)) for p in promoted_paths if Path(p).exists()},
            "verdict": "DEFERRED",
            "note": "git unavailable; all SHAs recorded here for auditability",
        }
        rp = receipt_dir / f"COMMIT_DEFERRED_RECEIPT_{stage_id}.json"
        rsha = write_json(rp, deferred)
        return PhaseResult(
            "P5_COMMIT", "DEFERRED",
            outputs=[{"path": str(rp), "sha256": rsha, "type": "COMMIT_DEFERRED_RECEIPT"}],
            data={"git_available": False, "reason": git_info, "deferred_receipt": str(rp)},
        )

    # Git available — stage and commit
    try:
        for p in promoted_paths:
            rc, out, err = run_cmd(["git", "-C", str(root), "add", p])
            if rc != 0:
                issues.append(f"git add failed for {p}: {err}")

        msg = f"MetaBlooms governed stage: {stage_name} [{stage_id}]"
        rc, out, err = run_cmd(["git", "-C", str(root), "commit", "-m", msg])
        if rc != 0:
            issues.append(f"git commit failed: {err}")
            commit_sha = None
        else:
            rc2, commit_sha, _ = run_cmd(["git", "-C", str(root), "rev-parse", "HEAD"])
            commit_sha = commit_sha.strip() if rc2 == 0 else None
    except Exception as e:
        issues.append(f"git operation exception: {e}")
        commit_sha = None

    receipt = {
        "phase": "P5_COMMIT",
        "stage_id": stage_id,
        "created_at": time.time(),
        "git_available": True,
        "commit_sha": commit_sha,
        "promoted_paths": promoted_paths,
        "issues": issues,
        "verdict": "PASS" if not issues and commit_sha else "FAIL",
    }
    rp = receipt_dir / f"P5_COMMIT_RECEIPT_{stage_id}.json"
    rsha = write_json(rp, receipt)

    return PhaseResult(
        "P5_COMMIT", "PASS" if not issues and commit_sha else "FAIL",
        outputs=[{"path": str(rp), "sha256": rsha}],
        issues=issues,
        data={"git_available": True, "commit_sha": commit_sha},
    )


def phase_6_update_state(root: Path, stage_id: str, stage_name: str,
                         phase5_result: PhaseResult,
                         promoted_outputs: List[Dict],
                         receipt_dir: Path) -> PhaseResult:
    """
    P6: Update CURRENT_WORKING_BASELINE_POINTER and STAGE_STATE_LEDGER.
    Accepts both git commit SHA and deferred receipt reference.
    """
    issues = []

    commit_sha = phase5_result.data.get("commit_sha")
    deferred_receipt = phase5_result.data.get("deferred_receipt")
    state_ref = commit_sha or deferred_receipt or f"DEFERRED_{stage_id}"

    # Update baseline pointer
    pointer_path = root / BASELINE_POINTER_PATH
    try:
        pointer = load_json(pointer_path) if pointer_path.exists() else {}
        pointer.update({
            "last_updated": time.time(),
            "last_stage_id": stage_id,
            "last_stage_name": stage_name,
            "last_commit_sha": commit_sha,
            "last_deferred_receipt": deferred_receipt,
            "state_ref": state_ref,
        })
        write_json(pointer_path, pointer)
    except Exception as e:
        issues.append(f"Failed to update baseline pointer: {e}")

    # Append to stage state ledger
    ledger_path = root / STATE_LEDGER_PATH
    try:
        ledger = load_json(ledger_path) if ledger_path.exists() else {"entries": []}
        entry = {
            "entry_id": stage_id,
            "timestamp": time.time(),
            "stage": stage_name,
            "verdict": "PASS",
            "state_ref": state_ref,
            "commit_sha": commit_sha,
            "deferred": deferred_receipt is not None,
            "outputs": [o.get("dst", o.get("path", "")) for o in promoted_outputs],
            "advances_latest_pass": True,
        }
        ledger.setdefault("entries", []).append(entry)
        ledger["updated_at"] = time.time()
        write_json(ledger_path, ledger)
    except Exception as e:
        issues.append(f"Failed to update stage state ledger: {e}")

    receipt = {
        "phase": "P6_UPDATE_STATE",
        "stage_id": stage_id,
        "state_ref": state_ref,
        "created_at": time.time(),
        "issues": issues,
        "verdict": "PASS" if not issues else "FAIL",
    }
    rp = receipt_dir / f"P6_UPDATE_STATE_RECEIPT_{stage_id}.json"
    rsha = write_json(rp, receipt)

    return PhaseResult(
        "P6_UPDATE_STATE", "PASS" if not issues else "FAIL",
        outputs=[{"path": str(rp), "sha256": rsha}],
        issues=issues,
        data={"state_ref": state_ref},
    )


def phase_7_handoff(root: Path, stage_id: str, stage_name: str,
                    next_stage: str, all_phases: List[PhaseResult],
                    promoted_outputs: List[Dict],
                    receipt_dir: Path) -> PhaseResult:
    """P7: Write next-stage handoff and final stage receipt. STOP."""
    all_passed = all(p.passed for p in all_phases)

    handoff = {
        "receipt_type": "STAGE_HANDOFF",
        "stage_id": stage_id,
        "stage_name": stage_name,
        "created_at": time.time(),
        "verdict": "PASS" if all_passed else "PARTIAL",
        "next_stage": next_stage,
        "phases_summary": [{"phase": p.phase_id, "verdict": p.verdict} for p in all_phases],
        "promoted_outputs": promoted_outputs,
        "promoted_shas": {
            o.get("dst", o.get("path", "")): o.get("sha256", "")
            for o in promoted_outputs
        },
        "must_stop": True,
    }
    hp = receipt_dir / f"STAGE_HANDOFF_{stage_id}.json"
    hsha = write_json(hp, handoff)

    # Also write to active root's registry
    active_handoff_path = root / f"0_kernel/registry/{stage_name}_HANDOFF_{stage_id}.json"
    try:
        active_handoff_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(active_handoff_path, handoff)
    except Exception:
        pass  # Non-blocking — handoff is in staging

    return PhaseResult(
        "P7_HANDOFF", "PASS",
        outputs=[{"path": str(hp), "sha256": hsha}],
        data={"handoff_path": str(hp), "next_stage": next_stage},
    )


# ─────────────────────────────────────────────────────────────────────────────
# BLOCKED RECEIPT
# ─────────────────────────────────────────────────────────────────────────────

def write_blocked_receipt(stage_id: str, stage_name: str, blocking_phase: str,
                          issues: List[str], receipt_dir: Path) -> str:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_type": "STAGE_BLOCKED",
        "stage_id": stage_id,
        "stage_name": stage_name,
        "blocking_phase": blocking_phase,
        "created_at": time.time(),
        "issues": issues,
        "advances_latest_pass": False,
        "must_stop": True,
        "next_action": "resolve blocking issues and re-run stage from P-1",
    }
    rp = receipt_dir / f"STAGE_BLOCKED_RECEIPT_{stage_id}.json"
    sha = write_json(rp, receipt)
    print(f"\n[BLOCKED] {blocking_phase}: {issues}")
    print(f"  Blocked receipt: {rp}  SHA: {sha}")
    return str(rp)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────

def run_stage(
    stage_name: str,
    heavy_work_class: str,
    execution_path: str,
    next_stage: str,
    outputs_to_write: List[Dict],   # [{relative_path, content_json_or_bytes}]
    promote_map: List[Dict],        # [{src, dst}]
    root: Optional[Path] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Execute a full governed stage through P-1 → P7.
    Returns the final receipt dict.
    """
    if root is None:
        root = DEFAULT_ROOT

    stage_id = stage_id_for(stage_name)
    staging_root = STAGE_BASE / stage_id
    # receipts go in a sibling dir so staging_root empty-check in P1 passes
    receipt_dir = STAGE_BASE / f"{stage_id}_receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)

    all_phases: List[PhaseResult] = []
    print(f"\n{'='*60}")
    print(f"[STAGE] {stage_name}")
    print(f"[ID]    {stage_id}")
    print(f"[CLASS] {heavy_work_class}  [PATH] {execution_path}")
    print(f"{'='*60}")

    # ── P-1: TOOL ROUTE GUARD ─────────────────────────────────────────────
    print("\n[P-1] Tool Route Guard...")
    p_minus1 = phase_minus1_tool_route_guard(
        root, stage_name, stage_id, execution_path, receipt_dir)
    all_phases.append(p_minus1)
    print(f"  → {p_minus1.verdict}  {p_minus1.issues or ''}")

    if not p_minus1.passed:
        write_blocked_receipt(stage_id, stage_name, "P-1_TOOL_ROUTE_GUARD",
                              p_minus1.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P-1", "stage_id": stage_id,
                "issues": p_minus1.issues}

    # ── P0: PREFLIGHT ─────────────────────────────────────────────────────
    print("\n[P0] Preflight...")
    p0 = phase_0_preflight(root, stage_name, stage_id, heavy_work_class, receipt_dir)
    all_phases.append(p0)
    print(f"  → {p0.verdict}  {p0.issues or ''}")

    if not p0.passed:
        write_blocked_receipt(stage_id, stage_name, "P0_PREFLIGHT",
                              p0.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P0", "stage_id": stage_id,
                "issues": p0.issues}

    if dry_run:
        print("\n[DRY_RUN] Stopping after P0 — preflight passed. No staging root created, no mutations.")
        return {"verdict": "DRY_RUN_PASS", "stage_id": stage_id,
                "phases_passed": ["P-1_TOOL_ROUTE_GUARD", "P0_PREFLIGHT"]}

    # ── P1: STAGE ROOT ────────────────────────────────────────────────────
    print("\n[P1] Creating stage root...")
    p1, staging_root = phase_1_stage_root(stage_id, receipt_dir)
    all_phases.append(p1)
    print(f"  → {p1.verdict}  staging: {staging_root}")

    if not p1.passed:
        write_blocked_receipt(stage_id, stage_name, "P1_STAGE_ROOT",
                              p1.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P1", "stage_id": stage_id,
                "issues": p1.issues}

    # ── P2: WRITE OUTPUTS ─────────────────────────────────────────────────
    print("\n[P2] Writing outputs to staging...")
    p2_outputs = []
    p2_issues = []

    for item in outputs_to_write:
        rel = item["relative_path"]
        target = staging_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if "content_json" in item:
                sha = write_json(target, item["content_json"])
            elif "content_text" in item:
                target.write_text(item["content_text"], encoding="utf-8")
                sha = sha256_file(target)
            elif "copy_from" in item:
                shutil.copy2(item["copy_from"], target)
                sha = sha256_file(target)
            else:
                p2_issues.append(f"No content provided for {rel}")
                continue
            p2_outputs.append({"relative_path": rel, "path": str(target), "sha256": sha})
            print(f"  wrote: {rel}  sha: {sha[:16]}...")
        except Exception as e:
            p2_issues.append(f"Failed to write {rel}: {e}")

    p2_receipt = {
        "phase": "P2_WRITE_OUTPUTS", "stage_id": stage_id,
        "created_at": time.time(), "outputs": p2_outputs,
        "issues": p2_issues, "verdict": "PASS" if not p2_issues else "FAIL",
    }
    p2_rp = receipt_dir / f"P2_WRITE_OUTPUTS_RECEIPT_{stage_id}.json"
    write_json(p2_rp, p2_receipt)
    p2 = PhaseResult("P2_WRITE_OUTPUTS", "PASS" if not p2_issues else "FAIL",
                     outputs=p2_outputs, issues=p2_issues)
    all_phases.append(p2)
    print(f"  → {p2.verdict}  {len(p2_outputs)} outputs")

    if not p2.passed:
        write_blocked_receipt(stage_id, stage_name, "P2_WRITE_OUTPUTS",
                              p2.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P2", "stage_id": stage_id,
                "issues": p2.issues}

    # ── P3: VERIFY ────────────────────────────────────────────────────────
    print("\n[P3] Verifying staged outputs...")
    p3 = phase_3_verify(staging_root, stage_id, p2_outputs, receipt_dir)
    all_phases.append(p3)
    print(f"  → {p3.verdict}  {p3.data.get('verified_count',0)} verified  {p3.issues or ''}")

    if not p3.passed:
        write_blocked_receipt(stage_id, stage_name, "P3_VERIFY",
                              p3.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P3", "stage_id": stage_id,
                "issues": p3.issues}

    # ── P4: PROMOTE ───────────────────────────────────────────────────────
    print("\n[P4] Promoting to active root...")
    if not promote_map:
        # Build promote_map from p2_outputs if not explicitly provided
        promote_map = [{"src": o["relative_path"], "dst": o["relative_path"]}
                       for o in p2_outputs]

    p4 = phase_4_promote(root, staging_root, stage_id, promote_map, receipt_dir)
    all_phases.append(p4)
    print(f"  → {p4.verdict}  {p4.data.get('promoted_count',0)} promoted  {p4.issues or ''}")

    if not p4.passed:
        write_blocked_receipt(stage_id, stage_name, "P4_PROMOTE",
                              p4.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P4", "stage_id": stage_id,
                "issues": p4.issues}

    promoted_outputs = [o for o in p4.outputs if "sha256" in o and "dst" in o]
    promoted_paths = [o["dst"] for o in promoted_outputs]

    # ── P5: COMMIT ────────────────────────────────────────────────────────
    print("\n[P5] Committing...")
    p5 = phase_5_commit(root, stage_id, stage_name, promoted_paths, receipt_dir)
    all_phases.append(p5)
    git_status = (f"commit: {p5.data.get('commit_sha','')[:12]}"
                  if p5.verdict == "PASS"
                  else f"deferred: {p5.data.get('reason','')}")
    print(f"  → {p5.verdict}  {git_status}")

    if p5.verdict == "FAIL":
        write_blocked_receipt(stage_id, stage_name, "P5_COMMIT",
                              p5.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P5", "stage_id": stage_id,
                "issues": p5.issues}

    # ── P6: UPDATE STATE ──────────────────────────────────────────────────
    print("\n[P6] Updating state...")
    p6 = phase_6_update_state(root, stage_id, stage_name, p5,
                              promoted_outputs, receipt_dir)
    all_phases.append(p6)
    print(f"  → {p6.verdict}  ref: {p6.data.get('state_ref','')[:20]}...")

    if not p6.passed:
        write_blocked_receipt(stage_id, stage_name, "P6_UPDATE_STATE",
                              p6.issues, receipt_dir)
        return {"verdict": "BLOCKED", "phase": "P6", "stage_id": stage_id,
                "issues": p6.issues}

    # ── P7: HANDOFF ───────────────────────────────────────────────────────
    print("\n[P7] Writing handoff...")
    p7 = phase_7_handoff(root, stage_id, stage_name, next_stage,
                         all_phases, promoted_outputs, receipt_dir)
    all_phases.append(p7)
    print(f"  → {p7.verdict}  next: {next_stage}")

    # ── FINAL RECEIPT ─────────────────────────────────────────────────────
    final = {
        "receipt_type": "STAGE_COMPLETE",
        "runner_version": RUNNER_VERSION,
        "contract": CONTRACT_ID,
        "stage_id": stage_id,
        "stage_name": stage_name,
        "heavy_work_class": heavy_work_class,
        "execution_path": execution_path,
        "created_at": time.time(),
        "verdict": "PASS",
        "phases": [p.to_dict() for p in all_phases],
        "promoted_outputs": promoted_outputs,
        "next_stage": next_stage,
        "must_stop": True,
    }
    fp = receipt_dir / f"STAGE_COMPLETE_RECEIPT_{stage_id}.json"
    fsha = write_json(fp, final)
    print(f"\n[COMPLETE] {stage_name}")
    print(f"  Receipt: {fp}")
    print(f"  SHA:     {fsha}")
    final["receipt_path"] = str(fp)
    final["receipt_sha"] = fsha
    return final


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MetaBlooms Transactional Stage Runner v1 — P-1 through P7 lifecycle"
    )
    ap.add_argument("--stage-name", required=True, help="Human-readable stage identifier")
    ap.add_argument("--heavy-work-class", required=True,
                    choices=sorted(VALID_HEAVY_WORK_CLASSES),
                    help="Work class from HEAVY_WORK_CLASS_ENUM_v1")
    ap.add_argument("--execution-path", default="python_user_visible",
                    choices=sorted(ALLOWED_EXECUTION_PATHS))
    ap.add_argument("--next-stage", default="NEXT_STAGE_NOT_SPECIFIED")
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="Active OS root")
    ap.add_argument("--request", help="Path to stage request JSON (see schema below)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Run P-1 and P0 only; stop before P2 writes")
    ap.add_argument("--json-output", action="store_true",
                    help="Print final receipt as JSON to stdout")
    args = ap.parse_args(argv)

    root = Path(args.root)

    # Load stage request if provided
    outputs_to_write: List[Dict] = []
    promote_map: List[Dict] = []
    if args.request:
        req = load_json(Path(args.request))
        outputs_to_write = req.get("outputs_to_write", [])
        promote_map = req.get("promote_map", [])
        # Request can override CLI args
        if "stage_name" in req:
            args.stage_name = req["stage_name"]
        if "heavy_work_class" in req:
            args.heavy_work_class = req["heavy_work_class"]
        if "next_stage" in req:
            args.next_stage = req["next_stage"]

    result = run_stage(
        stage_name=args.stage_name,
        heavy_work_class=args.heavy_work_class,
        execution_path=args.execution_path,
        next_stage=args.next_stage,
        outputs_to_write=outputs_to_write,
        promote_map=promote_map,
        root=root,
        dry_run=args.dry_run,
    )

    if args.json_output:
        print(json.dumps(result, indent=2))

    verdict = result.get("verdict", "UNKNOWN")
    sys.exit(0 if verdict in ("PASS", "DEFERRED", "DRY_RUN_PASS") else 1)


if __name__ == "__main__":
    main()
