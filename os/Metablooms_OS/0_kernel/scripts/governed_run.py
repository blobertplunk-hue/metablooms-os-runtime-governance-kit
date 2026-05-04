
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
# purpose: Enforce SQG validation and controlled execution of scripts and registry mutations
# mutation_scope: indirect (delegates to mutation engine)
# invariants_enforced: SQG_validation_required, no_direct_mutation, engine_only_mutation, fail_closed_execution
# risk_level: control-plane
###

import os, subprocess, json, sys, argparse

ROOT = "/mnt/data/Metablooms_OS_refined"
VALIDATOR = os.path.join(ROOT, "0_kernel/scripts/validate_script_v2.py")
ENGINE = os.path.join(ROOT, "0_kernel/scripts/registry_mutation_engine_v2_lite_final.py")
PYTHON_LANE = os.path.join(ROOT, "runtime/governance/python3_S_lane_exec_v1.sh")


def python_lane_cmd(*args):
    return [PYTHON_LANE, *args]

def run(cmd):
    r = bounded_subprocess_run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()

def validate(script_path):
    code, out, err = run(python_lane_cmd(VALIDATOR, script_path))
    return code == 0, out, err

def detect_mode(script_path):
    with open(script_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().lower()

    if "mutation_scope" in text and "artifact_registry" in text:
        return "mutation"
    return "read-only"

def run_read_only(script_path):
    return run(python_lane_cmd(script_path))

def run_mutation(request_path, dry_run):
    cmd = python_lane_cmd(ENGINE, "--request", request_path)
    if dry_run:
        cmd.append("--dry-run")
    return run(cmd)

def main():
    parser = argparse.ArgumentParser(description="Governed execution wrapper")
    parser.add_argument("--script", help="Script to validate and run")
    parser.add_argument("--request", help="Mutation request JSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.script and not args.request:
        print("ERROR: must provide --script or --request")
        sys.exit(1)

    if args.script:
        ok, out, err = validate(args.script)

        print("=== VALIDATION ===")
        print(out or err)

        if not ok:
            print("FAIL-CLOSED: script rejected by SQG")
            sys.exit(1)

        mode = detect_mode(args.script)

        print(f"MODE: {mode}")

        if mode == "read-only":
            code, out, err = run_read_only(args.script)
            print(out or err)
            sys.exit(code)
        else:
            print("FAIL-CLOSED: mutation scripts must use request-based engine")
            sys.exit(1)

    if args.request:
        print("=== EXECUTING MUTATION VIA ENGINE ===")

        code, out, err = run_mutation(args.request, args.dry_run)

        print(out or err)
        sys.exit(code)

if __name__ == "__main__":
    main()
