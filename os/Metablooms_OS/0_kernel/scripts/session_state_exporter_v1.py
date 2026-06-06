#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

def fail(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)

if getattr(sys.flags, "no_site", 0) != 1:
    fail("session_state_exporter_v1.py requires python3 -S via runtime/governance/python3_S_lane_exec_v1.sh")

ROOT = Path(os.environ.get("METABLOOMS_ROOT", "/mnt/data/Metablooms_OS")).resolve()
DEFAULT_OUT = ROOT / "runtime/governance/state_exports/SESSION_STATE_EXPORT_LATEST_v1.json"

def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))

def latest_refactor_handoff(receipts_dir: Path) -> Path | None:
    handoffs = sorted(receipts_dir.glob("R*_HANDOFF_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return handoffs[0] if handoffs else None

def recent_receipts(receipts_dir: Path, limit: int = 8):
    files = sorted(receipts_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]
    out = []
    for p in files:
        out.append({"path": str(p.relative_to(ROOT)), "sha256": sha256_path(p)})
    return out

def gather_active_contracts():
    contracts_dir = ROOT / "runtime/governance/contracts"
    if not contracts_dir.exists():
        return []
    return sorted(str(p.relative_to(ROOT)) for p in contracts_dir.glob("*.json"))

def gather_active_invariants():
    results = []
    for candidate in [ROOT / "governance/invariants", ROOT / "runtime/governance/invariants"]:
        if candidate.exists():
            results.extend(sorted(str(p.relative_to(ROOT)) for p in candidate.glob("*.json")))
    return results

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    receipts_dir = ROOT / "receipts/refactor_program"
    pointer_path = ROOT / "0_kernel/state/CURRENT_WORKING_BASELINE_POINTER_v1.json"
    risk_register = ROOT / "runtime/governance/risk/refactor_program_risk_register_v1.json"
    handoff_path = latest_refactor_handoff(receipts_dir)

    pointer = read_json(pointer_path) if pointer_path.exists() else {}
    next_stage = "UNKNOWN"
    next_actions = []
    blockers = []
    if handoff_path:
        handoff = read_json(handoff_path)
        next_stage = handoff.get("next_stage", "UNKNOWN")
        next_actions = handoff.get("next_actions", [])
        blockers = handoff.get("blockers", [])

    export = {
        "schema_id": "session_state_export_schema_v1",
        "version": "1.0",
        "created_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "authoritative_root": "/mnt/data/Metablooms_OS",
        "runtime_facts": {
            "baseline_pointer": str(pointer_path.relative_to(ROOT)),
            "current_stage_hint": next_stage,
            "active_contracts": gather_active_contracts(),
            "active_invariants": gather_active_invariants(),
            "python_lane": "runtime/governance/python3_S_lane_exec_v1.sh",
            "risk_register": str(risk_register.relative_to(ROOT)) if risk_register.exists() else ""
        },
        "open_work": {
            "next_stage": next_stage,
            "next_actions": next_actions or ["Resume from latest refactor handoff receipt."],
            "blockers": blockers
        },
        "deferred_work": [
            "Promote gate registry replacement in R5.",
            "Bind evidence-bound external reuse scan gate in R6.",
            "Promote usefulness validator into registered gate in R7.",
            "Unify python health governance into registry-backed lane in R8.",
            "Convert telemetry assets into cartridge-grade contract in R9."
        ],
        "recent_receipts": recent_receipts(receipts_dir),
        "transfer_note": "Portable session-state export for governed continuation. Use the latest handoff, keep the python3 -S lane, and resume at the declared next stage only after validating this export.",
        "artifact_hashes": {}
    }

    tmp_text = json.dumps(export, indent=2, sort_keys=False) + "\n"
    out_path.write_text(tmp_text, encoding='utf-8')

    tracked = [
        ROOT / "runtime/governance/schemas/session_state_export_schema_v1.json",
        ROOT / "0_kernel/scripts/session_state_exporter_v1.py",
        ROOT / "0_kernel/scripts/validate_session_state_export_v1.py",
        out_path,
    ]
    export["artifact_hashes"] = {str(p.relative_to(ROOT)): sha256_path(p) for p in tracked if p.exists()}
    _mb_write_json_file(out_path, export, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_session_state_exporter_v1_py_L114', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
