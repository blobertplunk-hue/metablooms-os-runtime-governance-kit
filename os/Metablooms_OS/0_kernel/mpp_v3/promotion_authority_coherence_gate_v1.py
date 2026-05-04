#!/usr/bin/env python3
"""MetaBlooms Promotion Authority Coherence Gate v1.

Local, dependency-free gate used to prevent boot/export promotion when authority
pointers, controlled artifact indexes, validator invocation contracts, receipts,
and export manifests disagree.  Stage 2 implements fixture-regression mode and a
report-only current OS scan; later stages may bind this as a hard promotion gate.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fnmatch
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

GATE_ID = "PROMOTION_AUTHORITY_COHERENCE_GATE_v1"
RESULT_SCHEMA = "metablooms.promotion_authority_coherence_gate.result.v1"
STAGE = "PROMOTION_AUTHORITY_COHERENCE_GATE_STAGE2_IMPLEMENTATION_AND_LOCAL_FIXTURE_RUN"

CHECKS = [
    ("PAC-001", "controlled_artifact_closure"),
    ("PAC-002", "stale_authority_sweep"),
    ("PAC-003", "pointer_equivalence"),
    ("PAC-004", "validator_cli_contract_map"),
    ("PAC-005", "fresh_chat_replay"),
    ("PAC-006", "export_self_consistency"),
    ("PAC-007", "promotion_receipt_binding"),
]
CONTROLLED_PREFIXES = (
    "0_kernel/boot_contracts/",
    "0_kernel/cartridges/",
    "0_kernel/chat_governance/",
    "0_kernel/docs/",
    "0_kernel/lib/",
    "0_kernel/mpp_v3/",
    "0_kernel/pipeline/",
    "0_kernel/registry/",
    "0_kernel/schemas/",
    "runtime/governance/",
    "runtime/cartridges/",
)
SELF_HASH_ANCHORS = (
    "0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json",
    "0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json.sha256",
)
BOOT_LIVE_PATTERNS = (
    "NEW_CHAT_START_HERE.md",
    "CURRENT_*AUTHORITY*.json",
    "0_kernel/boot_contracts/**",
    "0_kernel/registry/current_authority/**",
)
STAGE_RE = re.compile(r"\bSTAGE\s*[-_ ]?([0-9]{1,3}[A-Z]?)\b", re.IGNORECASE)


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def finish_result(result: Dict[str, Any]) -> Dict[str, Any]:
    result.setdefault("schema_version", RESULT_SCHEMA)
    result.setdefault("gate_id", GATE_ID)
    result.setdefault("created_at", utc_now())
    result["result_hash"] = sha256_bytes(canonical_json({k: v for k, v in result.items() if k != "result_hash"}))
    return result


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(encoded, encoding="utf-8")
    os.replace(tmp, path)


def write_sha_sidecar(path: Path) -> None:
    path.with_name(path.name + ".sha256").write_text(f"{sha256_file(path)}  {path.name}\n", encoding="utf-8")


def check_result(check_id: str, name: str, defects: Sequence[str], evidence: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "check_id": check_id,
        "name": name,
        "decision": "DENY" if defects else "PASS",
        "defects": list(defects),
        "evidence": dict(evidence),
    }


def evaluate_fixture(fixture: Mapping[str, Any]) -> Dict[str, Any]:
    setup = fixture.get("setup", {}) if isinstance(fixture.get("setup", {}), Mapping) else {}
    checks: List[Dict[str, Any]] = []
    all_defects: List[str] = []

    inv = set(setup.get("controlled_inventory", []) or [])
    reg = set(setup.get("registry_entries", []) or [])
    missing = sorted(inv - reg)
    defects = ["controlled_artifact_missing_from_index"] if missing else []
    all_defects.extend(defects)
    checks.append(check_result("PAC-001", "controlled_artifact_closure", defects, {"missing_from_registry": missing, "inventory_count": len(inv), "registry_count": len(reg)}))

    text = str(setup.get("live_start_file_text", ""))
    current = str(setup.get("current_authority", "")).upper().replace(" ", "")
    refs = ["STAGE" + m.group(1).upper() for m in STAGE_RE.finditer(text)]
    stale = [r for r in refs if current and r != current]
    defects = ["live_boot_file_names_noncurrent_authority"] if stale else []
    all_defects.extend(defects)
    checks.append(check_result("PAC-002", "stale_authority_sweep", defects, {"current_authority": current or None, "stage_references": refs, "stale_references": stale}))

    pointer_eq = setup.get("pointer_copies_equivalent", True)
    defects = ["pointer_copies_not_byte_equivalent_json"] if pointer_eq is False else []
    all_defects.extend(defects)
    checks.append(check_result("PAC-003", "pointer_equivalence", defects, {"pointer_copies_equivalent": pointer_eq}))

    declared = setup.get("declared_shape")
    actual = setup.get("actual_supported_shape")
    defects = ["declared_shape_fails_smoke"] if declared and actual and declared != actual else []
    all_defects.extend(defects)
    checks.append(check_result("PAC-004", "validator_cli_contract_map", defects, {"validator": setup.get("validator"), "declared_shape": declared, "actual_supported_shape": actual}))

    replay = setup.get("fresh_chat_replay", "PASS")
    defects = ["fresh_chat_boot_rehearsal_denied"] if replay != "PASS" else []
    all_defects.extend(defects)
    checks.append(check_result("PAC-005", "fresh_chat_replay", defects, {"fresh_chat_replay": replay}))

    manifest_outputs = set(setup.get("manifest_outputs", []) or [])
    zip_members = set(setup.get("zip_members", []) or [])
    missing_members = sorted(manifest_outputs - zip_members)
    zsc = setup.get("zip_self_consistency", "PASS")
    defects = []
    if missing_members:
        defects.append("manifest_declares_missing_member")
    if zsc != "PASS":
        defects.append("zip_test_fails")
    all_defects.extend(defects)
    checks.append(check_result("PAC-006", "export_self_consistency", defects, {"missing_members": missing_members, "zip_self_consistency": zsc}))

    receipt_success = setup.get("promotion_receipt_status") == "SUCCESS"
    gate_hash = setup.get("gate_result_hash")
    defects = ["receipt_claims_success_without_all_gate_evidence"] if receipt_success and not gate_hash else []
    all_defects.extend(defects)
    checks.append(check_result("PAC-007", "promotion_receipt_binding", defects, {"promotion_receipt_status": setup.get("promotion_receipt_status"), "gate_result_hash_present": bool(gate_hash)}))

    decision = "DENY" if all_defects else "PASS"
    expected = fixture.get("expected_decision")
    return finish_result({
        "mode": "fixture",
        "stage": STAGE,
        "fixture_id": fixture.get("fixture_id"),
        "title": fixture.get("title"),
        "decision": decision,
        "expected_decision": expected,
        "matches_expected": decision == expected,
        "defects": sorted(set(all_defects)),
        "declared_fixture_defects": fixture.get("defects", []),
        "checks": checks,
        "evidence": {"fixture_schema_version": fixture.get("schema_version")},
    })


def run_fixtures(fixtures_dir: Path, out_dir: Optional[Path]) -> Dict[str, Any]:
    fixture_paths = sorted(fixtures_dir.glob("PAC-FIX-*.json"))
    results: List[Dict[str, Any]] = []
    for path in fixture_paths:
        result = evaluate_fixture(load_json(path))
        result["fixture_path"] = str(path)
        results.append(result)
        if out_dir:
            out_path = out_dir / f"{result['fixture_id']}_RESULT.json"
            write_json(out_path, result)
            write_sha_sidecar(out_path)
    failures = [r for r in results if not r.get("matches_expected")]
    ledger = finish_result({
        "mode": "fixture_ledger",
        "stage": STAGE,
        "decision": "PASS" if not failures and results else "DENY",
        "fixture_count": len(results),
        "passed_fixture_count": len(results) - len(failures),
        "failed_fixture_count": len(failures),
        "fixture_results": [{"fixture_id": r.get("fixture_id"), "decision": r.get("decision"), "expected_decision": r.get("expected_decision"), "matches_expected": r.get("matches_expected"), "result_hash": r.get("result_hash")} for r in results],
        "checks": [],
        "evidence": {"fixtures_dir": str(fixtures_dir)},
    })
    if out_dir:
        ledger_path = out_dir / "FIXTURE_RESULT_LEDGER.json"
        write_json(ledger_path, ledger)
        write_sha_sidecar(ledger_path)
    return ledger


def is_controlled_path(rel: str) -> bool:
    return rel in ("NEW_CHAT_START_HERE.md", "CURRENT_FULL_AUTHORITY_POINTER_v1.json", "CURRENT_EXPORT_AUTHORITY_v1.json") or rel.startswith(CONTROLLED_PREFIXES)


def classify_lifecycle(rel: str) -> str:
    low = rel.lower()
    if rel in SELF_HASH_ANCHORS:
        return "self_hash_anchor"
    if rel.endswith(".pyc") or "/__pycache__/" in rel:
        return "generated_non_authoritative"
    if "/legacy_archives/" in rel or "/legacy_quarantine/" in rel:
        return "historical"
    if "pre_patch_backups" in low or "backup" in low or "_bak_" in rel or rel.endswith(".bak"):
        return "backup"
    if rel.startswith(("runtime/receipts/", "runtime/handoffs/", "runtime/stage_bundles/")):
        return "receipt"
    if any(fnmatch.fnmatch(rel, p) for p in BOOT_LIVE_PATTERNS):
        return "active_authority"
    if rel.startswith(("0_kernel/registry/", "0_kernel/cartridges/", "runtime/governance/")):
        return "active_supporting"
    if is_controlled_path(rel):
        return "active_supporting"
    return "generated_non_authoritative"


def load_registry(root: Path) -> Tuple[Dict[str, str], Optional[str]]:
    path = root / "0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json"
    if not path.exists():
        return {}, "controlled_governance_artifact_index_missing"
    try:
        data = load_json(path)
        entries = data.get("entries", []) if isinstance(data, Mapping) else []
        return {str(e.get("path")): str(e.get("sha256")) for e in entries if isinstance(e, Mapping) and e.get("path") and e.get("sha256")}, None
    except Exception as exc:  # pragma: no cover - defensive path
        return {}, f"controlled_governance_artifact_index_unreadable:{exc}"


def current_authority_token(root: Path) -> Optional[str]:
    candidates = [root / "CURRENT_FULL_AUTHORITY_POINTER_v1.json", root / "0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json"]
    blob = ""
    for p in candidates:
        if p.exists():
            try:
                blob += p.read_text(encoding="utf-8", errors="ignore") + "\n"
            except Exception:
                pass
    matches = ["STAGE" + m.group(1).upper() for m in STAGE_RE.finditer(blob)]
    if matches:
        # Choose the highest numeric stage reference seen in the live pointer text.
        def key(tok: str) -> Tuple[int, str]:
            m = re.search(r"(\d+)([A-Z]?)", tok)
            return (int(m.group(1)) if m else -1, m.group(2) if m else "")
        return sorted(matches, key=key)[-1]
    return None


def live_boot_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for rel in ("NEW_CHAT_START_HERE.md", "CURRENT_FULL_AUTHORITY_POINTER_v1.json", "CURRENT_EXPORT_AUTHORITY_v1.json"):
        p = root / rel
        if p.exists():
            files.append(p)
    for base in (root / "0_kernel/boot_contracts", root / "0_kernel/registry/current_authority"):
        if base.exists():
            files.extend([p for p in base.rglob("*") if p.is_file()])
    return sorted(set(files))


def scan_current_os(root: Path, sample_limit: int = 50) -> Dict[str, Any]:
    if not root.exists():
        return finish_result({
            "mode": "current_os_report_only",
            "stage": STAGE,
            "decision": "BLOCKED",
            "defects": ["canonical_working_root_missing"],
            "checks": [],
            "evidence": {"root": str(root)},
        })
    registry, registry_error = load_registry(root)
    controlled: List[str] = []
    hashes: Dict[str, str] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if is_controlled_path(rel):
            controlled.append(rel)
            try:
                hashes[rel] = sha256_file(path)
            except Exception:
                hashes[rel] = "UNREADABLE"
    active_lifecycles = {"active_authority", "active_supporting"}
    missing = sorted([p for p in controlled if classify_lifecycle(p) in active_lifecycles and p not in registry])
    mismatches = sorted([p for p in controlled if classify_lifecycle(p) in active_lifecycles and p in registry and hashes.get(p) != registry.get(p)])
    registered_noncurrent = sorted([p for p in registry if p not in hashes or classify_lifecycle(p) not in active_lifecycles])
    pac001_defects: List[str] = []
    if registry_error:
        pac001_defects.append(registry_error)
    if missing:
        pac001_defects.append("controlled_artifact_missing_from_index")
    if mismatches:
        pac001_defects.append("registered_hash_mismatch")
    if registered_noncurrent:
        pac001_defects.append("registered_noncurrent_controlled_artifact")

    current = current_authority_token(root)
    stale_refs: List[Dict[str, Any]] = []
    for p in live_boot_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        refs = ["STAGE" + m.group(1).upper() for m in STAGE_RE.finditer(text)]
        stale = [r for r in refs if current and r != current]
        if stale:
            stale_refs.append({"path": p.relative_to(root).as_posix(), "stage_references": sorted(set(refs)), "stale_references": sorted(set(stale))})
    pac002_defects = ["live_boot_file_names_noncurrent_authority"] if stale_refs else []

    checks = [
        check_result("PAC-001", "controlled_artifact_closure", pac001_defects, {
            "controlled_count": len(controlled),
            "registered_count": len(registry),
            "missing_from_registry_count": len(missing),
            "registered_hash_mismatch_count": len(mismatches),
            "registered_noncurrent_count": len(registered_noncurrent),
            "missing_from_registry_sample": missing[:sample_limit],
            "hash_mismatch_sample": mismatches[:sample_limit],
            "registered_noncurrent_sample": registered_noncurrent[:sample_limit],
        }),
        check_result("PAC-002", "stale_authority_sweep", pac002_defects, {
            "current_authority_token": current,
            "stale_reference_count": len(stale_refs),
            "stale_reference_sample": stale_refs[:sample_limit],
        }),
        check_result("PAC-003", "pointer_equivalence", [], {"status": "not_evaluated_in_report_only_stage2"}),
        check_result("PAC-004", "validator_cli_contract_map", [], {"status": "not_evaluated_in_report_only_stage2"}),
        check_result("PAC-005", "fresh_chat_replay", [], {"status": "not_evaluated_in_report_only_stage2"}),
        check_result("PAC-006", "export_self_consistency", [], {"status": "not_evaluated_in_report_only_stage2"}),
        check_result("PAC-007", "promotion_receipt_binding", [], {"status": "not_evaluated_in_report_only_stage2"}),
    ]
    defects = sorted(set(d for c in checks for d in c.get("defects", [])))
    return finish_result({
        "mode": "current_os_report_only",
        "stage": STAGE,
        "decision": "DENY" if defects else "PASS",
        "report_only": True,
        "defects": defects,
        "checks": checks,
        "evidence": {"root": str(root), "sample_limit": sample_limit},
    })


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run MetaBlooms promotion authority coherence gate.")
    parser.add_argument("--root", default="/mnt/data/Metablooms_OS", help="Canonical MetaBlooms OS root.")
    parser.add_argument("--fixture", help="Run one fixture JSON file.")
    parser.add_argument("--fixtures-dir", help="Run all PAC-FIX-*.json fixtures in this directory.")
    parser.add_argument("--report-current", action="store_true", help="Run report-only current OS scan.")
    parser.add_argument("--out-dir", help="Directory for individual fixture outputs and ledgers.")
    parser.add_argument("--json-out", help="Write the selected result JSON to this path.")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir) if args.out_dir else None
    result: Dict[str, Any]
    if args.fixture:
        result = evaluate_fixture(load_json(Path(args.fixture)))
    elif args.fixtures_dir:
        result = run_fixtures(Path(args.fixtures_dir), out_dir)
    elif args.report_current:
        result = scan_current_os(Path(args.root))
    else:
        parser.error("choose --fixture, --fixtures-dir, or --report-current")

    if args.json_out:
        out = Path(args.json_out)
        write_json(out, result)
        write_sha_sidecar(out)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("decision") == "PASS" or result.get("mode") == "current_os_report_only" else 1


if __name__ == "__main__":
    raise SystemExit(main())
