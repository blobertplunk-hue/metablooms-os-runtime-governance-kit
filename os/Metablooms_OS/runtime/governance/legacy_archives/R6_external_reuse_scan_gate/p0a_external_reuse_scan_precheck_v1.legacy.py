#!/usr/bin/env python3 -S
### GOVERNANCE HEADER
# artifact_id: p0a_external_reuse_scan_precheck_v1
# purpose: Phase gate that runs before any stage creates or modifies an in-scope
#          asset (schema, component, tool, HTML engine). Fails closed if the
#          stage lacks external scan evidence and a valid reuse decision.
#          Implements COOL_5 P0A_EXTERNAL_REUSE_SCAN_PRECHECK.
# tool_class: python3 -S (stdlib only — no site packages)
# mutation_scope: read-only (writes gate receipt only)
# see_evidence:
#   - "A repeatable decision process for where new capabilities belong in the stack"
#     (Kellton Build vs Buy 2026) — adopt/adapt/compose/build_new/defer ladder
#   - "Governance frameworks embedded from day one deliver better compliance than
#     those added after deployment" (TechTarget 2026)
#   - "Companies with governance tools get 12x more AI projects into production"
#     (Microsoft/Databricks 2026)
###

import json, hashlib, os, sys, time
from pathlib import Path

VERSION = "1.0"
AMENDMENT = "COOL_5_P0A_EXTERNAL_REUSE_SCAN_PRECHECK"

VALID_DECISIONS = ["adopt_existing", "adapt_existing", "compose_existing",
                   "build_new_with_evidence", "defer_or_block"]

IN_SCOPE_ASSET_TYPES = [
    "schema", "validator", "component", "html_engine", "telemetry",
    "dashboard", "cartridge", "workflow", "runner_phase", "gate"
]

DEFAULT_RECEIPT_DIR = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/p0a_receipts")


def sha256(s):
    return hashlib.sha256(s.encode()).hexdigest()


def write_receipt(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(request, receipt_dir):
    """
    request keys:
      stage_name        — name of the stage being evaluated
      asset_type        — one of IN_SCOPE_ASSET_TYPES
      asset_name        — name of artifact being built/modified
      scan_evidence     — list of {source, finding, query} dicts (empty = no scan done)
      reuse_decision    — one of VALID_DECISIONS
      reuse_rationale   — text explaining why this decision was made
      candidate_refs    — list of external refs considered (can be empty if adopt)
    """
    blocks = []
    warns = []

    asset_type = request.get("asset_type", "")
    asset_name = request.get("asset_name", "")
    scan_evidence = request.get("scan_evidence", [])
    decision = request.get("reuse_decision", "")
    rationale = request.get("reuse_rationale", "")
    candidates = request.get("candidate_refs", [])

    # C1: asset type must be in-scope
    if asset_type and asset_type not in IN_SCOPE_ASSET_TYPES:
        warns.append(f"asset_type '{asset_type}' not in known in-scope types — may not need P0A check")

    # C2: scan evidence required for non-adopt decisions
    if decision in ("build_new_with_evidence", "adapt_existing", "compose_existing"):
        if not scan_evidence or len(scan_evidence) < 2:
            blocks.append(
                f"Decision '{decision}' requires ≥2 scan evidence items — "
                f"found {len(scan_evidence)}. Run SEE search first."
            )
        # Each evidence item needs at least a source and finding
        for i, ev in enumerate(scan_evidence):
            if not ev.get("source") or not ev.get("finding"):
                blocks.append(f"scan_evidence[{i}] missing 'source' or 'finding' field")

    # C3: adopt_existing requires at least one candidate_ref
    if decision == "adopt_existing" and not candidates:
        blocks.append("adopt_existing decision requires ≥1 candidate_ref identifying what is being adopted")

    # C4: reuse_decision must be valid
    if not decision:
        blocks.append("reuse_decision is required — choose from: " + ", ".join(VALID_DECISIONS))
    elif decision not in VALID_DECISIONS:
        blocks.append(f"reuse_decision '{decision}' not valid — must be one of: {VALID_DECISIONS}")

    # C5: defer_or_block always blocks
    if decision == "defer_or_block":
        blocks.append(
            f"reuse_decision is 'defer_or_block' — stage '{asset_name}' must not proceed. "
            "Resolve deferral reason before continuing."
        )

    # C6: rationale must be substantive
    if len(str(rationale).split()) < 5:
        warns.append(f"reuse_rationale is very short ({len(str(rationale).split())} words) — add more detail")

    verdict = "BLOCK" if blocks else ("WARN" if warns else "PASS")
    gate_decision = "DENY" if blocks else "ALLOW"

    receipt = {
        "receipt_type": "P0A_EXTERNAL_REUSE_SCAN_PRECHECK_RECEIPT",
        "version": VERSION,
        "amendment": AMENDMENT,
        "created_at": time.time(),
        "stage_name": request.get("stage_name", "UNKNOWN"),
        "asset_type": asset_type,
        "asset_name": asset_name,
        "reuse_decision": decision,
        "reuse_rationale": rationale,
        "scan_evidence_count": len(scan_evidence),
        "candidate_refs_count": len(candidates),
        "verdict": verdict,
        "gate_decision": gate_decision,
        "blocks": blocks,
        "warns": warns,
        "gate_instruction": (
            "ALLOW — stage may proceed to implementation"
            if gate_decision == "ALLOW"
            else "DENY — stage blocked. Provide scan evidence and valid reuse decision."
        ),
    }

    ts = int(time.time() * 1000)
    safe_name = asset_name.replace("/", "_")[:30] if asset_name else "UNKNOWN"
    rpath = receipt_dir / f"P0A_{safe_name}_{ts}.json"
    rsha = write_receipt(rpath, receipt)
    receipt["receipt_path"] = str(rpath)
    receipt["receipt_sha"] = rsha

    icon = {"PASS": "✓", "WARN": "⚠", "BLOCK": "✗"}[verdict]
    print(f"  [{icon}] P0A gate: {gate_decision}  asset={asset_name}  decision={decision}")
    if blocks:
        for b in blocks:
            print(f"    BLOCK: {b[:80]}")
    return receipt


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P0A External Reuse Scan Precheck v1")
    ap.add_argument("--request", required=True, help="Path to JSON request file")
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--json-output", action="store_true")
    args = ap.parse_args()

    req = json.loads(Path(args.request).read_text())
    result = evaluate(req, Path(args.receipt_dir))

    if args.json_output:
        print(json.dumps(result, indent=2))
    sys.exit(0 if result["gate_decision"] == "ALLOW" else 1)


if __name__ == "__main__":
    main()
