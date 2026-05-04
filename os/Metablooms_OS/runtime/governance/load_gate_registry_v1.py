#!/usr/bin/env python3
"""Load MetaBlooms gate registry v1. Must run under python3 -S."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "runtime/governance/registries/gate_registry_v1.json"

def require_dash_s():
    if "site" in sys.modules:
        raise SystemExit("FAIL: load_gate_registry_v1.py must run under python3 -S; site module is loaded")

def load_registry(path=None):
    require_dash_s()
    p = Path(path) if path else DEFAULT
    data = json.loads(p.read_text())
    gates = {g["gate_id"]: g for g in data.get("gates", [])}
    return data, gates

if __name__ == "__main__":
    data, gates = load_registry(sys.argv[1] if len(sys.argv) > 1 else None)
    print(json.dumps({"registry_id": data.get("registry_id"), "gate_count": len(gates), "enabled_count": sum(1 for g in gates.values() if g.get("enabled"))}, indent=2))
