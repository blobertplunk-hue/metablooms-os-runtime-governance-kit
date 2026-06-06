#!/usr/bin/env python3
"""Deterministic MetaBlooms full OS archive restore tool.

Canonical guarded restore path for wrapped full OS exports. It blocks nested-wrapper
restore targets and prevents partially extracted roots from replacing the live OS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

SCHEMA = "mb.restore_full_os_archive.receipt.v1"
DEFAULT_WRAPPER = "Metablooms_OS"
REQUIRED_REL = (
    "scripts/mpp/mpp.sh",
    "boot.py",
    "portable_full_os_boot_verify.py",
)
ALLOWED_TOP_LEVEL = {DEFAULT_WRAPPER, "EXPORT_RECEIPT.json", "MANIFEST.json", "MANIFEST.sha256"}


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    Path(str(path) + ".sha256").write_text(hashlib.sha256(text.encode()).hexdigest() + f"  {path.name}\n", encoding="utf-8")


def run(cmd: list[str], timeout: int) -> tuple[int, str, str, bool]:
    try:
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else ((exc.stdout or b"").decode("utf-8", "replace"))
        err = exc.stderr if isinstance(exc.stderr, str) else ((exc.stderr or b"").decode("utf-8", "replace"))
        return 124, out, err, True


def inspect_archive(archive: Path, wrapper: str, timeout: int) -> dict[str, Any]:
    z_rc, _, z_err, z_to = run(["zstd", "-t", str(archive)], timeout)
    t_rc, listing, t_err, t_to = run(["tar", "--use-compress-program=zstd", "-tf", str(archive)], timeout)
    members = listing.splitlines() if t_rc == 0 else []
    normalized = []
    for member in members:
        name = member[2:] if member.startswith("./") else member
        name = name.replace(f"{wrapper}/./", f"{wrapper}/")
        normalized.append(name)
    top_levels = sorted({m.split("/", 1)[0] for m in normalized if m})
    required = {rel: any(m == f"{wrapper}/{rel}" for m in normalized) for rel in REQUIRED_REL}
    errors: list[str] = []
    if z_rc != 0 or z_to:
        errors.append("archive_integrity_failed")
    if t_rc != 0 or t_to:
        errors.append("archive_member_listing_failed")
    if wrapper not in top_levels or any(t not in ALLOWED_TOP_LEVEL for t in top_levels):
        errors.append("archive_wrapper_layout_failed")
    missing = [rel for rel, ok in required.items() if not ok]
    if missing:
        errors.append("required_boot_members_missing:" + ",".join(missing))
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "member_count": len(members),
        "top_levels": top_levels,
        "required_present": required,
        "zstd_rc": z_rc,
        "tar_list_rc": t_rc,
        "zstd_stderr_tail": z_err[-1000:],
        "tar_stderr_tail": t_err[-1000:],
    }


def validate_destination(extract_parent: Path, wrapper: str, allow_nested: bool) -> dict[str, Any]:
    parent = extract_parent.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if parent.name == wrapper and not allow_nested:
        errors.append("DOUBLE_WRAPPER_RISK_EXTRACT_PARENT_IS_WRAPPER_DIR")
        warnings.append(f"Choose the parent of {parent}; the archive already contains {wrapper}/")
    return {
        "status": "PASS" if not errors else "FAIL",
        "extract_parent": str(parent),
        "target_root": str(parent / wrapper),
        "errors": errors,
        "warnings": warnings,
    }


def validate_staged_root(root: Path) -> dict[str, Any]:
    required = {rel: (root / rel).is_file() for rel in REQUIRED_REL}
    errors = []
    if not root.exists():
        errors.append("staged_root_missing")
    missing = [rel for rel, ok in required.items() if not ok]
    if missing:
        errors.append("staged_required_boot_members_missing:" + ",".join(missing))
    mpp = root / "scripts/mpp/mpp.sh"
    if mpp.exists():
        rc, _, err, _ = run(["bash", "-n", str(mpp)], 30)
        if rc != 0:
            errors.append("staged_mpp_shell_syntax_failed:" + err[-500:])
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "required_present": required}


def restore(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    archive = args.archive.resolve()
    receipt: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at_utc": utc(),
        "archive": str(archive),
        "mode": "dry_run" if args.dry_run else "restore",
        "invariants": [
            "restore target is the wrapper parent, not the wrapper root",
            "archive extraction occurs in temporary staging first",
            "live root changes only after staged validation passes",
        ],
    }
    errors: list[str] = []
    if not archive.is_file():
        errors.append("archive_missing")
    if shutil.which("tar") is None or shutil.which("zstd") is None:
        errors.append("required_tool_missing")
    if archive.is_file():
        sidecar = Path(str(archive) + ".sha256")
        observed = sha256_file(archive)
        receipt["archive_sha256"] = observed
        if sidecar.exists() and observed not in sidecar.read_text(encoding="utf-8", errors="replace"):
            errors.append("archive_sidecar_mismatch")
    inspection = inspect_archive(archive, args.wrapper_dir, args.timeout_seconds) if not errors else {"status": "SKIPPED"}
    destination = validate_destination(args.extract_parent, args.wrapper_dir, args.allow_nested)
    receipt["inspection"] = inspection
    receipt["destination_plan"] = destination
    errors.extend(inspection.get("errors", []))
    errors.extend(destination.get("errors", []))
    if errors:
        receipt["decision"] = "FAIL_PRECHECK"
        receipt["errors"] = errors
        return 2, receipt
    if args.dry_run:
        receipt["decision"] = "PASS_DRY_RUN"
        receipt["errors"] = []
        return 0, receipt

    extract_parent = args.extract_parent.resolve()
    extract_parent.mkdir(parents=True, exist_ok=True)
    stage_parent = Path(tempfile.mkdtemp(prefix="mb_restore_stage_", dir=str(extract_parent)))
    rc, _, err, timed_out = run(["tar", "--use-compress-program=zstd", "-xf", str(archive), "-C", str(stage_parent)], args.timeout_seconds)
    staged_root = stage_parent / args.wrapper_dir
    staged = validate_staged_root(staged_root)
    receipt["stage_parent"] = str(stage_parent)
    receipt["extract"] = {"returncode": rc, "timeout": timed_out, "stderr_tail": err[-1000:]}
    receipt["staged_validation"] = staged
    if rc != 0 or staged["status"] != "PASS":
        receipt["decision"] = "FAIL_STAGED_VALIDATION"
        receipt["errors"] = (["extract_failed_or_timed_out"] if rc != 0 else []) + staged.get("errors", [])
        if args.keep_failed_stage:
            receipt["failed_stage_retained"] = str(stage_parent)
        else:
            shutil.rmtree(stage_parent, ignore_errors=True)
            receipt["failed_stage_removed"] = True
        return 2, receipt

    target = extract_parent / args.wrapper_dir
    quarantine = None
    if target.exists():
        quarantine = extract_parent / f".{args.wrapper_dir}_quarantine_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        shutil.move(str(target), str(quarantine))
    shutil.move(str(staged_root), str(target))
    shutil.rmtree(stage_parent, ignore_errors=True)
    receipt["decision"] = "PASS_RESTORED"
    receipt["target_root"] = str(target)
    receipt["quarantine"] = str(quarantine) if quarantine else None
    receipt["errors"] = []
    return 0, receipt


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely restore a wrapped MetaBlooms full OS archive")
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--extract-parent", type=Path, default=Path("/mnt/data"))
    parser.add_argument("--wrapper-dir", default=DEFAULT_WRAPPER)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-nested", action="store_true")
    parser.add_argument("--keep-failed-stage", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    rc, receipt = restore(args)
    write_json(args.receipt, receipt)
    if args.print_summary:
        print(f"RESTORE_FULL_OS_ARCHIVE={receipt.get('decision')} receipt={args.receipt}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
