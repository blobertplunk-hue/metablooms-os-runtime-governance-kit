#!/usr/bin/env python3
"""MetaBlooms Promotion Authority Repair Inventory Classifier v1.

Stage 4 companion to PROMOTION_AUTHORITY_COHERENCE_GATE_v1.
It inventories current PAC DENY defects and classifies repair actions without
mutating authority pointers, registry entries, or boot guidance.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

SCHEMA = "metablooms.promotion_authority_repair_inventory_classifier.v1"
STAGE = "PROMOTION_AUTHORITY_COHERENCE_GATE_STAGE4_REPAIR_INVENTORY_AND_CLASSIFIER"
STAGE_RE = re.compile(r"\bSTAGE\s*[-_ ]?([0-9]{1,3}[A-Z]?)\b", re.IGNORECASE)
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
)
LIVE_BOOT_FILES = {
    "NEW_CHAT_START_HERE.md",
    "CURRENT_FULL_AUTHORITY_POINTER_v1.json",
    "CURRENT_EXPORT_AUTHORITY_v1.json",
    "0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json",
}
BOOT_LIVE_PATTERNS = (
    "NEW_CHAT_START_HERE.md",
    "CURRENT_*AUTHORITY*.json",
    "0_kernel/boot_contracts/**",
    "0_kernel/registry/current_authority/**",
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def write_sha(path: Path) -> None:
    path.with_name(path.name + ".sha256").write_text(f"{sha256_file(path)}  {path.name}\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def is_controlled_path(rel: str) -> bool:
    return rel in ("NEW_CHAT_START_HERE.md", "CURRENT_FULL_AUTHORITY_POINTER_v1.json", "CURRENT_EXPORT_AUTHORITY_v1.json") or rel.startswith(CONTROLLED_PREFIXES)


def is_live_boot_path(rel: str) -> bool:
    return rel in LIVE_BOOT_FILES or any(fnmatch.fnmatch(rel, pat) for pat in BOOT_LIVE_PATTERNS)


def classify_lifecycle(rel: str) -> str:
    low = rel.lower()
    name = Path(rel).name
    if "__pycache__" in rel or rel.endswith(".pyc"):
        return "generated_non_authoritative"
    if "pre_patch_backups" in low or "backup" in low or "_bak_" in rel or rel.endswith(".bak"):
        return "backup"
    if rel.startswith("runtime/receipts/") or "/receipts/" in low or "/boot_receipts/" in low:
        return "receipt"
    if is_live_boot_path(rel):
        return "active_authority"
    if rel.startswith("0_kernel/registry/current_authority/"):
        return "active_authority"
    if rel.startswith("0_kernel/cartridges/external_review_lenses/"):
        return "active_supporting"
    if rel.startswith(("0_kernel/registry/promotion_authority_coherence/", "0_kernel/schemas/promotion_authority_coherence/")):
        return "active_supporting"
    if rel.startswith(("0_kernel/mpp_v3/", "0_kernel/lib/", "runtime/governance/", "0_kernel/cartridges/", "0_kernel/schemas/", "0_kernel/registry/")):
        return "active_supporting"
    if name.endswith(".sha256"):
        return "active_supporting"
    return "generated_non_authoritative"


def action_for_missing(rel: str, lifecycle: str) -> Tuple[str, str, int]:
    if lifecycle == "generated_non_authoritative":
        return ("exclude_or_quarantine_generated_artifact", "Generated/runtime artifact must not be blessed into controlled registry unless explicitly promoted.", 4)
    if lifecycle == "backup":
        return ("exclude_or_relocate_backup", "Backup artifact should not be current controlled authority.", 4)
    if lifecycle == "receipt":
        return ("classify_as_receipt_or_move_out_of_controlled_registry_scope", "Receipt/history material should be explicit evidence, not active authority.", 3)
    if is_live_boot_path(rel):
        return ("repair_content_then_register_current_hash", "Live boot authority must be patched before registry closure.", 1)
    if rel.endswith(".sha256"):
        return ("validate_parent_then_register_or_regenerate_sidecar", "Sidecar can only be registered after parent artifact is classified and hash-checked.", 2)
    return ("register_candidate_after_owner_and_scope_review", "Likely active supporting governance artifact; register only after validating source and lifecycle.", 2)


def action_for_mismatch(rel: str, lifecycle: str) -> Tuple[str, str, int]:
    if rel == "0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json" or rel.endswith("CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json.sha256"):
        return ("rebuild_registry_index_and_sidecar_after_all_repairs", "Registry self/sidecar hash must be regenerated last to avoid stale self-reference.", 1)
    if is_live_boot_path(rel):
        return ("patch_live_boot_reference_then_update_registered_hash", "Live boot files have stale authority refs; content repair must precede hash reconciliation.", 1)
    if rel.endswith(".sha256"):
        return ("regenerate_sidecar_after_parent_hash_reconciliation", "Sidecar mismatch usually follows parent drift; regenerate after parent decision.", 2)
    if lifecycle in ("generated_non_authoritative", "backup", "receipt"):
        return ("remove_from_active_index_or_mark_non_authoritative", "Registered non-authoritative artifacts create false boot-critical drift.", 2)
    return ("verify_drift_then_update_registered_hash", "Registered active artifact hash differs from disk; inspect drift source before updating.", 2)


def load_registry(root: Path) -> Tuple[Dict[str, Dict[str, Any]], Optional[str]]:
    idx = root / "0_kernel/registry/CONTROLLED_GOVERNANCE_ARTIFACT_INDEX_v1.json"
    if not idx.exists():
        return {}, "controlled_governance_artifact_index_missing"
    try:
        data = load_json(idx)
    except Exception as exc:
        return {}, f"controlled_governance_artifact_index_unreadable:{exc}"
    entries = {}
    for e in data.get("entries", []) if isinstance(data, Mapping) else []:
        if isinstance(e, Mapping) and e.get("path"):
            entries[str(e["path"])] = dict(e)
    return entries, None


def current_authority_token(root: Path) -> Optional[str]:
    blob = ""
    for rel in ("CURRENT_FULL_AUTHORITY_POINTER_v1.json", "0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json"):
        p = root / rel
        if p.exists():
            blob += p.read_text(encoding="utf-8", errors="ignore") + "\n"
    matches = ["STAGE" + m.group(1).upper() for m in STAGE_RE.finditer(blob)]
    if not matches:
        return None
    def key(tok: str) -> Tuple[int, str]:
        m = re.search(r"(\d+)([A-Z]?)", tok)
        return (int(m.group(1)) if m else -1, m.group(2) if m else "")
    return sorted(matches, key=key)[-1]


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


def sidecar_status(root: Path, rel: str) -> Dict[str, Any]:
    status: Dict[str, Any] = {"is_sidecar": rel.endswith(".sha256")}
    if not rel.endswith(".sha256"):
        side = root / (rel + ".sha256")
        status["sidecar_exists"] = side.exists()
        if side.exists():
            status["sidecar_path"] = rel + ".sha256"
        return status
    parent_rel = rel[:-7]
    parent = root / parent_rel
    status["parent_path"] = parent_rel
    status["parent_exists"] = parent.exists()
    try:
        txt = (root / rel).read_text(encoding="utf-8", errors="ignore").strip()
        status["declared_sha256"] = txt.split()[0] if txt else None
    except Exception:
        status["declared_sha256"] = None
    if parent.exists():
        status["actual_parent_sha256"] = sha256_file(parent)
        status["sidecar_matches_parent"] = status.get("declared_sha256") == status["actual_parent_sha256"]
    return status


def classify(root: Path, sample_limit: int = 100) -> Dict[str, Any]:
    registry, registry_error = load_registry(root)
    controlled: List[str] = []
    hashes: Dict[str, str] = {}
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if is_controlled_path(rel):
            controlled.append(rel)
            try:
                hashes[rel] = sha256_file(p)
            except Exception:
                hashes[rel] = "UNREADABLE"
    missing_items = []
    mismatch_items = []
    for rel in sorted(controlled):
        life = classify_lifecycle(rel)
        if life not in ("backup", "receipt", "generated_non_authoritative") and rel not in registry:
            act, reason, priority = action_for_missing(rel, life)
            missing_items.append({
                "path": rel,
                "defect": "controlled_artifact_missing_from_index",
                "lifecycle": life,
                "recommended_action": act,
                "priority": priority,
                "reason": reason,
                "actual_sha256": hashes.get(rel),
                "sidecar_status": sidecar_status(root, rel),
            })
        if rel in registry and hashes.get(rel) != registry[rel].get("sha256"):
            act, reason, priority = action_for_mismatch(rel, life)
            mismatch_items.append({
                "path": rel,
                "defect": "registered_hash_mismatch",
                "lifecycle": life,
                "recommended_action": act,
                "priority": priority,
                "reason": reason,
                "registered_sha256": registry[rel].get("sha256"),
                "actual_sha256": hashes.get(rel),
                "registered_by": registry[rel].get("registered_by"),
                "registered_utc": registry[rel].get("registered_utc"),
                "sidecar_status": sidecar_status(root, rel),
            })
    current = current_authority_token(root)
    stale_items = []
    for p in live_boot_files(root):
        rel = p.relative_to(root).as_posix()
        text = p.read_text(encoding="utf-8", errors="ignore")
        refs = sorted(set("STAGE" + m.group(1).upper() for m in STAGE_RE.finditer(text)))
        stale = [r for r in refs if current and r != current]
        if stale:
            life = classify_lifecycle(rel)
            if rel in ("NEW_CHAT_START_HERE.md", "0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md"):
                action = "patch_live_boot_guidance_to_current_stage18_authority"
                priority = 1
                reason = "Operator-facing boot guidance names older authority and can send new-chat boot down stale paths."
            elif rel.startswith("0_kernel/registry/current_authority/"):
                action = "relocate_or_mark_historical_then_replace_with_current_stage18_packet"
                priority = 1
                reason = "File lives under current_authority but describes an older authority packet."
            else:
                action = "classify_reference_context_before_patch"
                priority = 2
                reason = "Stage reference appears in live boot surface; historical vs current context must be explicit."
            stale_items.append({
                "path": rel,
                "defect": "live_boot_file_names_noncurrent_authority",
                "lifecycle": life,
                "recommended_action": action,
                "priority": priority,
                "reason": reason,
                "current_authority_token": current,
                "stage_references": refs,
                "stale_references": stale,
            })
    all_items = missing_items + mismatch_items + stale_items
    by_action: Dict[str, int] = {}
    by_lifecycle: Dict[str, int] = {}
    by_defect: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
    for item in all_items:
        by_action[item["recommended_action"]] = by_action.get(item["recommended_action"], 0) + 1
        by_lifecycle[item["lifecycle"]] = by_lifecycle.get(item["lifecycle"], 0) + 1
        by_defect[item["defect"]] = by_defect.get(item["defect"], 0) + 1
        by_priority[str(item["priority"])] = by_priority.get(str(item["priority"]), 0) + 1
    priority_order = sorted(all_items, key=lambda x: (x["priority"], x["defect"], x["path"]))
    result: Dict[str, Any] = {
        "schema_version": SCHEMA,
        "stage": STAGE,
        "created_at": utc_now(),
        "mode": "repair_inventory_classifier_report_only",
        "decision": "REPAIR_REQUIRED" if all_items or registry_error else "PASS",
        "mutated_authority": False,
        "root": str(root),
        "registry_error": registry_error,
        "current_authority_token": current,
        "counts": {
            "controlled_files_scanned": len(controlled),
            "registered_entries": len(registry),
            "missing_from_registry": len(missing_items),
            "registered_hash_mismatches": len(mismatch_items),
            "stale_live_authority_refs": len(stale_items),
            "total_repair_items": len(all_items),
        },
        "summary_by_defect": dict(sorted(by_defect.items())),
        "summary_by_lifecycle": dict(sorted(by_lifecycle.items())),
        "summary_by_recommended_action": dict(sorted(by_action.items())),
        "summary_by_priority": dict(sorted(by_priority.items(), key=lambda kv: int(kv[0]))),
        "ordered_repair_queue_sample": priority_order[:sample_limit],
        "full_inventory": {
            "missing_from_registry": missing_items,
            "registered_hash_mismatches": mismatch_items,
            "stale_live_authority_refs": stale_items,
        },
        "next_stage_recommendation": "PROMOTION_AUTHORITY_COHERENCE_GATE_STAGE5_STALE_BOOT_REFERENCE_REPAIR",
        "blocked_actions": [
            "bulk_register_missing_controlled_artifacts",
            "update_registry_hashes_before_stale_boot_reference_repair",
            "promote_full_authority_export_before PAC PASS",
        ],
        "result_hash": "",
    }
    result["result_hash"] = hashlib.sha256(canonical_json({k: v for k, v in result.items() if k != "result_hash"})).hexdigest()
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Classify PAC current OS repair inventory without mutation.")
    ap.add_argument("--root", default="/mnt/data/Metablooms_OS")
    ap.add_argument("--json-out", required=True)
    ap.add_argument("--sample-limit", type=int, default=100)
    args = ap.parse_args(argv)
    result = classify(Path(args.root), args.sample_limit)
    out = Path(args.json_out)
    write_json(out, result)
    write_sha(out)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["decision"] in ("PASS", "REPAIR_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
