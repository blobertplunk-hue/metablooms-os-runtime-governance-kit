### GOVERNANCE HEADER
# purpose: Ensure Ruff is available for governed Python linting/formatting.
# mutation_scope: vendor dependency bootstrap only
# invariants_enforced: lint_tool_probe_required, ruff_required_for_python_script_changes, vendor_path_preferred, post_install_cli_verification_required
# risk_level: mutation-safe
###

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/mnt/data/Metablooms_OS_refined")
VENDOR_PY = ROOT / "0_kernel" / "vendor" / "python"
RUFF = ROOT / "0_kernel" / "vendor" / "bin" / "ruff"
RECEIPT = ROOT / "0_kernel" / "registry" / "RUFF_BOOTSTRAP_RECEIPT_latest.json"

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {"cmd": [str(x) for x in cmd], "returncode": r.returncode, "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}

def install_ruff():
    VENDOR_PY.mkdir(parents=True, exist_ok=True)
    return run([sys.executable, "-m", "pip", "install", "--target", str(VENDOR_PY), "ruff"])

def verify_ruff():
    if RUFF.exists():
        return run([str(RUFF), "--version"])
    return {"returncode": 1, "stdout": "", "stderr": f"missing ruff wrapper: {RUFF}"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install-if-missing", action="store_true")
    args = parser.parse_args()

    before = verify_ruff()
    install = None
    if before["returncode"] != 0 and args.install_if_missing:
        install = install_ruff()
    after = verify_ruff()

    receipt = {
        "version": "1.0",
        "created_at": time.time(),
        "status": "PASS" if after["returncode"] == 0 else "FAIL",
        "vendor_python": str(VENDOR_PY),
        "ruff_wrapper": str(RUFF),
        "before": before,
        "install_attempted": install is not None,
        "install_result": install,
        "after": after,
        "usage_contract": {
            "preferred_for": "Python linting and formatting before committing generated or modified scripts",
            "commands": ["ruff check <paths>", "ruff format <paths>"],
            "fallback": "Python syntax compile + pytest where Ruff unavailable"
        }
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if after["returncode"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
