#!/usr/bin/env python3 -S
### GOVERNANCE HEADER
# artifact_id: usefulness_surface_validator_v1
# purpose: Validates any HTML/schema artifact has a valid usefulness surface
#          declaration before it can be promoted to active/released status.
#          Blocks promotion if fewer than 3 dimensions are covered, or if
#          required dimensions for the artifact type are absent.
# tool_class: python3 -S (stdlib only)
# mutation_scope: read-only (writes validation receipt only)
###

import json, hashlib, os, sys, time
from pathlib import Path

VERSION = "1.0"
MIN_DIMENSIONS_COVERED = 3
DEFAULT_RECEIPT_DIR = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/uss_receipts")

# Dimensions required by artifact type (from schema metablooms_constraint)
REQUIRED_BY_TYPE = {
    "html_activity": ["realtime_feedback", "teacher_telemetry", "misconception_diagnosis"],
    "dashboard":     ["teacher_telemetry"],
    "telemetry_engine": ["misconception_diagnosis", "teacher_telemetry"],
}

ALL_DIMENSION_IDS = [
    "instruction","practice","assessment","realtime_feedback","teacher_telemetry",
    "misconception_diagnosis","adaptive_support","export_reuse","future_improvement"
]


def validate(declaration, receipt_dir=DEFAULT_RECEIPT_DIR):
    """
    Validate a usefulness surface declaration dict.
    Returns receipt dict with verdict PASS/BLOCK.
    """
    blocks = []
    warns = []

    artifact_id   = declaration.get("artifact_id", "UNKNOWN")
    artifact_type = declaration.get("artifact_type", "")
    dimensions    = declaration.get("dimensions_covered", {})

    # C1: required fields present
    for req in ("artifact_id", "artifact_type", "dimensions_covered"):
        if req not in declaration:
            blocks.append(f"Missing required field: '{req}'")

    if blocks:
        return _write_receipt(artifact_id, blocks, warns, {}, receipt_dir)

    # C2: dimensions_covered is a dict
    if not isinstance(dimensions, dict):
        blocks.append(f"dimensions_covered must be a dict, got {type(dimensions).__name__}")
        return _write_receipt(artifact_id, blocks, warns, {}, receipt_dir)

    # C3: count covered dimensions
    covered = [k for k, v in dimensions.items()
               if isinstance(v, dict) and v.get("covered") is True]
    not_applicable = declaration.get("dimensions_not_applicable", [])
    covered_count = len(covered)

    if covered_count < MIN_DIMENSIONS_COVERED:
        blocks.append(
            f"Only {covered_count} dimensions covered — minimum is {MIN_DIMENSIONS_COVERED}. "
            f"Covered: {covered}"
        )

    # C4: check artifact-type required dimensions
    required_dims = REQUIRED_BY_TYPE.get(artifact_type, [])
    for dim in required_dims:
        if dim in not_applicable:
            continue
        dim_entry = dimensions.get(dim, {})
        if not (isinstance(dim_entry, dict) and dim_entry.get("covered") is True):
            blocks.append(
                f"Dimension '{dim}' is required for artifact_type='{artifact_type}' "
                f"but is not marked covered"
            )

    # C5: unknown dimension IDs flagged
    for k in dimensions.keys():
        if k not in ALL_DIMENSION_IDS:
            warns.append(f"Unknown dimension id: '{k}' — not in official taxonomy")

    # C6: covered dimensions should have notes
    for dim_id in covered:
        entry = dimensions.get(dim_id, {})
        note = entry.get("note", "")
        if not note or len(str(note).split()) < 2:
            warns.append(f"Dimension '{dim_id}' is covered but has no meaningful note")

    summary = {
        "covered_dimensions": covered,
        "covered_count": covered_count,
        "not_applicable": not_applicable,
        "required_for_type": required_dims,
    }

    return _write_receipt(artifact_id, blocks, warns, summary, receipt_dir)


def _write_receipt(artifact_id, blocks, warns, summary, receipt_dir):
    verdict = "BLOCK" if blocks else ("WARN" if warns else "PASS")
    receipt = {
        "receipt_type": "USEFULNESS_SURFACE_VALIDATION_RECEIPT",
        "version": VERSION,
        "artifact_id": artifact_id,
        "created_at": time.time(),
        "verdict": verdict,
        "gate_decision": "DENY" if blocks else "ALLOW",
        "block_count": len(blocks),
        "warn_count": len(warns),
        "blocks": blocks,
        "warns": warns,
        "summary": summary,
        "gate_instruction": (
            "ALLOW — artifact has valid usefulness surface declaration"
            if verdict in ("PASS","WARN")
            else "DENY — artifact blocked from promotion. Add usefulness surface declaration."
        ),
    }
    Path(receipt_dir).mkdir(parents=True, exist_ok=True)
    ts = int(time.time()*1000)
    safe = str(artifact_id).replace("/","_")[:24]
    rpath = Path(receipt_dir) / f"USS_VAL_{safe}_{ts}.json"
    tmp = rpath.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt, indent=2))
    os.replace(tmp, rpath)
    receipt["receipt_path"] = str(rpath)
    receipt["receipt_sha"] = hashlib.sha256(rpath.read_bytes()).hexdigest()

    icon = {"PASS":"✓","WARN":"⚠","BLOCK":"✗"}[verdict]
    print(f"  [{icon}] USS gate: {receipt['gate_decision']}  "
          f"covered={summary.get('covered_count',0)}  artifact={artifact_id}")
    if blocks:
        for b in blocks: print(f"    BLOCK: {b[:80]}")
    return receipt


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Usefulness Surface Validator v1")
    ap.add_argument("--declaration", required=True,
                    help="Path to JSON file containing usefulness surface declaration")
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--json-output", action="store_true")
    args = ap.parse_args()

    decl = json.loads(Path(args.declaration).read_text())
    result = validate(decl, Path(args.receipt_dir))
    if args.json_output:
        print(json.dumps(result, indent=2))
    sys.exit(0 if result["gate_decision"] == "ALLOW" else 1)


if __name__ == "__main__":
    main()
