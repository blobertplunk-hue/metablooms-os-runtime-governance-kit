#!/usr/bin/env python3
"""Compatibility wrapper for R1 successor name. Delegates to assert_gate_registry_integrity_v1."""
import runpy, sys
from pathlib import Path
if "site" in sys.modules:
    raise SystemExit("FAIL: validate_gate_registry_v1.py must run under python3 -S; site module is loaded")
script = Path(__file__).with_name("assert_gate_registry_integrity_v1.py")
sys.argv = [str(script)] + sys.argv[1:]
runpy.run_path(str(script), run_name="__main__")
