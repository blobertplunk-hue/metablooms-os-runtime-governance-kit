#!/usr/bin/env python3
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_TOP = [
    "contract_id",
    "authoritative_root",
    "accepted_source_tracks",
    "required_handoff_artifacts",
    "compatibility_rules",
    "stale_after_utc",
    "supersedes",
]
EXPECTED_ROOT = "/mnt/data/Metablooms_OS"
EXPECTED_STATUS = "archive_only_after_r3"


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("contract_path")
    ap.add_argument("--root", default=EXPECTED_ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    contract_path = Path(args.contract_path)
    root = Path(args.root)
    errors = []
    checks = []
    if not contract_path.is_file():
        errors.append(f"missing_contract:{contract_path}")
        result = {"ok": False, "errors": errors, "checks": checks}
        print(json.dumps(result, indent=2) if args.json else result)
        return 2

    data = json.loads(contract_path.read_text())

    for key in REQUIRED_TOP:
        ok = key in data
        checks.append({"check": f"required_top:{key}", "ok": ok})
        if not ok:
            errors.append(f"missing_field:{key}")

    if data.get("contract_id") != "unified_runtime_compatibility_contract_v1":
        errors.append("bad_contract_id")
    checks.append({"check": "contract_id", "ok": data.get("contract_id") == "unified_runtime_compatibility_contract_v1"})

    root_ok = data.get("authoritative_root") == str(root) == EXPECTED_ROOT and root.is_dir()
    checks.append({"check": "authoritative_root", "ok": root_ok})
    if not root_ok:
        errors.append("bad_authoritative_root")

    tracks = data.get("accepted_source_tracks", [])
    track_ids = {t.get("track_id") for t in tracks if isinstance(t, dict)}
    tracks_ok = {"GW", "OS"}.issubset(track_ids)
    checks.append({"check": "accepted_source_tracks", "ok": tracks_ok})
    if not tracks_ok:
        errors.append("missing_required_tracks")

    handoff_ok = True
    for item in data.get("required_handoff_artifacts", []):
        rel = item.get("path")
        req = item.get("required", True)
        exists = (root / rel).exists() if rel else False
        checks.append({"check": f"handoff:{rel}", "ok": (exists or not req)})
        if req and not exists:
            errors.append(f"missing_handoff:{rel}")
            handoff_ok = False
    if not data.get("required_handoff_artifacts"):
        handoff_ok = False
        errors.append("no_handoff_artifacts")

    try:
        stale_ok = parse_ts(data["stale_after_utc"]) > datetime.now(timezone.utc)
    except Exception:
        stale_ok = False
    checks.append({"check": "stale_after_utc_future", "ok": stale_ok})
    if not stale_ok:
        errors.append("stale_or_invalid_stale_after")

    supersedes = data.get("supersedes", [])
    sup_ok = all(x in supersedes for x in [
        "1_governance/workflow_v6/CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json",
        "1_governance/workflow_v6/CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.redirect.json",
    ])
    checks.append({"check": "supersedes", "ok": sup_ok})
    if not sup_ok:
        errors.append("bad_supersedes")

    redirect_path = root / "1_governance/workflow_v6/CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.redirect.json"
    redirect_ok = False
    if redirect_path.is_file():
        try:
            redirect = json.loads(redirect_path.read_text())
            redirect_ok = redirect.get("machine_use_status") == EXPECTED_STATUS and redirect.get("successor_contract") == "runtime/governance/contracts/unified_runtime_compatibility_contract_v1.json"
        except Exception:
            redirect_ok = False
    checks.append({"check": "cross_link_redirect_status", "ok": redirect_ok})
    if not redirect_ok:
        errors.append("cross_link_redirect_not_demoted")

    rules = data.get("compatibility_rules", [])
    rules_ok = isinstance(rules, list) and len(rules) >= 5 and all(isinstance(r, dict) and r.get("rule_id") and r.get("condition") for r in rules)
    checks.append({"check": "compatibility_rules", "ok": rules_ok})
    if not rules_ok:
        errors.append("invalid_compatibility_rules")

    ok = not errors
    result = {
        "ok": ok,
        "contract_path": str(contract_path),
        "root": str(root),
        "errors": errors,
        "checks": checks,
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("PASS" if ok else "FAIL")
        print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
