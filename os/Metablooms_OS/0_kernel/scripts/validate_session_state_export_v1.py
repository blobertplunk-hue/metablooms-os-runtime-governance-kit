#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, sys
from pathlib import Path

def fail(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    raise SystemExit(code)

if getattr(sys.flags, "no_site", 0) != 1:
    fail("validate_session_state_export_v1.py requires python3 -S via runtime/governance/python3_S_lane_exec_v1.sh")

ROOT = Path(os.environ.get("METABLOOMS_ROOT", "/mnt/data/Metablooms_OS")).resolve()

def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("export_path")
    args = ap.parse_args()
    p = Path(args.export_path)
    data = json.loads(p.read_text(encoding='utf-8'))
    errors = []
    required = ["schema_id","version","created_utc","authoritative_root","runtime_facts","open_work","deferred_work","recent_receipts","transfer_note","artifact_hashes"]
    for k in required:
        if k not in data:
            errors.append(f"missing top-level field: {k}")
    if data.get("schema_id") != "session_state_export_schema_v1":
        errors.append("schema_id mismatch")
    if data.get("authoritative_root") != "/mnt/data/Metablooms_OS":
        errors.append("authoritative_root mismatch")
    forbidden_tokens = ["claude", "gpt", "openai", "anthropic"]
    def walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                lk = str(k).lower()
                for token in forbidden_tokens:
                    if token in lk:
                        errors.append(f"vendor-specific field name at {path + '/' + str(k)}")
                walk(v, path + "/" + str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, path + f"[{i}]")
    walk(data)
    rf = data.get("runtime_facts", {})
    if rf.get("python_lane") != "runtime/governance/python3_S_lane_exec_v1.sh":
        errors.append("python_lane not bound to python3 -S wrapper")
    ow = data.get("open_work", {})
    if not ow.get("next_stage"):
        errors.append("open_work.next_stage empty")
    if not isinstance(data.get("recent_receipts", []), list) or not data.get("recent_receipts"):
        errors.append("recent_receipts missing or empty")
    for rec in data.get("recent_receipts", []):
        rel = rec.get("path", "")
        digest = rec.get("sha256", "")
        target = ROOT / rel
        if not target.exists():
            errors.append(f"recent receipt path missing: {rel}")
        elif sha256_path(target) != digest:
            errors.append(f"recent receipt hash mismatch: {rel}")
    artifact_hashes = data.get("artifact_hashes", {})
    for rel, digest in artifact_hashes.items():
        target = ROOT / rel
        if not target.exists():
            errors.append(f"artifact hash target missing: {rel}")
        elif sha256_path(target) != digest:
            errors.append(f"artifact hash mismatch: {rel}")
    report = {
        "contract_id": "validate_session_state_export_v1",
        "validated_path": str(p),
        "verdict": "PASS" if not errors else "FAIL",
        "errors": errors,
        "field_count": len(data.keys()) if isinstance(data, dict) else 0
    }
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
