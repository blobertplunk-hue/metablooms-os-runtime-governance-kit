
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
    r = bounded_subprocess_run(cmd, capture_output=True, text=True)
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
    _mb_write_json_file(RECEIPT, receipt, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_ensure_ruff_available_v1_py_L72', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    print(json.dumps(receipt, indent=2))
    return 0 if after["returncode"] == 0 else 1

if __name__ == "__main__":
    raise SystemExit(main())
