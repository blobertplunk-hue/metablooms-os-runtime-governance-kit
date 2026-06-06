#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    tool = root / "tools/metablooms/restore_full_os_archive_v1.py"
    errors: list[str] = []
    if not tool.exists():
        errors.append("restore_tool_missing")
    else:
        compile_proc = subprocess.run([sys.executable, "-m", "py_compile", str(tool)], text=True, capture_output=True)
        if compile_proc.returncode != 0:
            errors.append("restore_tool_py_compile_failed:" + compile_proc.stderr[-500:])

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        fixture = tmp_path / "src"
        (fixture / "scripts/mpp").mkdir(parents=True)
        (fixture / "scripts/mpp/mpp.sh").write_text("#!/usr/bin/env bash\necho ok\n", encoding="utf-8")
        os.chmod(fixture / "scripts/mpp/mpp.sh", 0o755)
        (fixture / "boot.py").write_text("print('boot')\n", encoding="utf-8")
        (fixture / "portable_full_os_boot_verify.py").write_text("print('verify')\n", encoding="utf-8")
        archive = tmp_path / "fixture.tar.zst"
        build = subprocess.run(
            ["bash", "-lc", f"cd {fixture} && tar --create --transform='s,^,Metablooms_OS/,' -f - . | zstd -q -1 -o {archive} -"],
            text=True,
            capture_output=True,
        )
        if build.returncode != 0:
            errors.append("fixture_archive_build_failed:" + build.stderr[-500:])
        elif tool.exists():
            Path(str(archive) + ".sha256").write_text(sha256_file(archive) + "  " + archive.name + "\n", encoding="utf-8")
            bad_receipt = tmp_path / "bad.json"
            bad = subprocess.run(
                [sys.executable, "-S", str(tool), "--archive", str(archive), "--extract-parent", str(tmp_path / "Metablooms_OS"), "--receipt", str(bad_receipt), "--dry-run"],
                text=True,
                capture_output=True,
            )
            if bad.returncode == 0:
                errors.append("double_wrapper_guard_failed_open")
            good_receipt = tmp_path / "good.json"
            good = subprocess.run(
                [sys.executable, "-S", str(tool), "--archive", str(archive), "--extract-parent", str(tmp_path), "--receipt", str(good_receipt), "--dry-run"],
                text=True,
                capture_output=True,
            )
            if good.returncode != 0:
                errors.append("canonical_restore_dry_run_failed:" + good.stderr[-500:])

    receipt = root / "runtime/receipts/deterministic_restore_contract/VALIDATION_RECEIPT_v1.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema": "mb.deterministic_restore_contract.validation.v1",
        "decision": "PASS" if not errors else "FAIL",
        "errors": errors,
    }
    receipt.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(str(receipt) + ".sha256").write_text(sha256_file(receipt) + "  " + receipt.name + "\n", encoding="utf-8")
    print("DETERMINISTIC_RESTORE_CONTRACT_VALIDATION=" + data["decision"] + " receipt=" + str(receipt))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
