#!/usr/bin/env python3 -S
### GOVERNANCE HEADER
# artifact_id: usefulness_surface_validator_v1
# purpose: Enforced gate for validating artifact usefulness declarations before promotion.
# tool_class: python3 -S (stdlib only)
# mutation_scope: writes validation decision receipts only
###
import argparse, hashlib, json, os, sys, time, uuid
from pathlib import Path

VERSION = "1.2-vpq-stage3"
ROOT = Path("/mnt/data/Metablooms_OS")
DEFAULT_RECEIPT_DIR = ROOT / "runtime/governance/decision_logs/usefulness_surface"
MIN_DIMENSIONS_COVERED = 3
REQUIRED_BY_TYPE = {
    "html_activity": ["instruction", "practice", "realtime_feedback", "teacher_telemetry", "misconception_diagnosis", "visual_presentation"],
    "dashboard": ["teacher_telemetry", "assessment", "future_improvement", "visual_presentation"],
    "teacher_tool": ["teacher_telemetry", "assessment", "future_improvement", "visual_presentation"],
    "student_tool": ["instruction", "practice", "realtime_feedback", "visual_presentation"],
    "landing_page": ["instruction", "export_reuse", "future_improvement", "visual_presentation"],
    "operator_tracker": ["assessment", "realtime_feedback", "future_improvement", "visual_presentation"],
    "other_visual_artifact": ["assessment", "export_reuse", "visual_presentation"],
    "telemetry_engine": ["misconception_diagnosis", "teacher_telemetry", "future_improvement"],
    "schema": ["assessment", "export_reuse", "future_improvement"],
    "governance_gate": ["assessment", "realtime_feedback", "future_improvement"],
    "runtime_contract": ["assessment", "export_reuse", "future_improvement"],
}
ALL_DIMENSION_IDS = [
    "instruction", "practice", "assessment", "realtime_feedback", "teacher_telemetry",
    "misconception_diagnosis", "adaptive_support", "export_reuse", "future_improvement", "visual_presentation"
]


def require_dash_s():
    if 'site' in sys.modules:
        raise SystemExit("DENY: usefulness validator must be launched with python3 -S; site module is loaded")


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def validate(declaration, declaration_path=None, receipt_dir=DEFAULT_RECEIPT_DIR):
    blocks, warns = [], []
    artifact_id = declaration.get("artifact_id", "UNKNOWN") if isinstance(declaration, dict) else "UNKNOWN"
    decision_id = str(uuid.uuid4())

    if not isinstance(declaration, dict):
        return write_receipt(artifact_id, decision_id, ["Declaration must be a JSON object"], warns, {}, declaration_path, receipt_dir)

    for req in ("artifact_id", "artifact_type", "dimensions_covered"):
        if req not in declaration:
            blocks.append(f"Missing required field: {req}")

    artifact_type = declaration.get("artifact_type", "")
    dimensions = declaration.get("dimensions_covered", {})
    not_applicable = declaration.get("dimensions_not_applicable", [])
    promotion_context = declaration.get("promotion_context", {})

    if not isinstance(artifact_id, str) or not artifact_id.strip():
        blocks.append("artifact_id must be a non-empty string")
    if not isinstance(artifact_type, str) or not artifact_type.strip():
        blocks.append("artifact_type must be a non-empty string")
    if not isinstance(dimensions, dict):
        blocks.append("dimensions_covered must be an object")
        dimensions = {}
    if not isinstance(not_applicable, list):
        blocks.append("dimensions_not_applicable must be an array")
        not_applicable = []
    if promotion_context and not isinstance(promotion_context, dict):
        blocks.append("promotion_context must be an object when present")
        promotion_context = {}

    covered = []
    for dim_id, entry in dimensions.items():
        if dim_id not in ALL_DIMENSION_IDS:
            warns.append(f"Unknown dimension id: {dim_id}")
        if not isinstance(entry, dict):
            blocks.append(f"Dimension {dim_id} entry must be an object")
            continue
        if entry.get("covered") is True:
            covered.append(dim_id)
            note = str(entry.get("note", "")).strip()
            evidence = entry.get("evidence")
            if len(note.split()) < 4:
                blocks.append(f"Covered dimension {dim_id} requires a specific note of at least 4 words")
            if not isinstance(evidence, list) or not evidence:
                blocks.append(f"Covered dimension {dim_id} requires non-empty evidence list")
        elif entry.get("covered") is not False:
            blocks.append(f"Dimension {dim_id}.covered must be true or false")

    if len(covered) < MIN_DIMENSIONS_COVERED:
        blocks.append(f"Only {len(covered)} dimensions covered; minimum is {MIN_DIMENSIONS_COVERED}")

    required_dims = REQUIRED_BY_TYPE.get(artifact_type, [])
    for dim in required_dims:
        if dim in not_applicable:
            blocks.append(f"Required dimension {dim} cannot be marked not_applicable for artifact_type={artifact_type}")
        elif dim not in covered:
            blocks.append(f"Required dimension {dim} missing for artifact_type={artifact_type}")

    target_path = promotion_context.get("target_artifact_path") if isinstance(promotion_context, dict) else None
    target_sha = promotion_context.get("target_artifact_sha256") if isinstance(promotion_context, dict) else None
    if target_path:
        tp = Path(target_path)
        if not tp.exists() or not tp.is_file():
            blocks.append(f"promotion_context target_artifact_path does not exist as file: {target_path}")
        elif target_sha and sha256_path(tp) != target_sha:
            blocks.append("promotion_context target_artifact_sha256 does not match target_artifact_path")
    elif declaration.get("promotion_required") is True:
        blocks.append("promotion_required=true requires promotion_context.target_artifact_path")

    summary = {
        "artifact_type": artifact_type,
        "covered_dimensions": covered,
        "covered_count": len(covered),
        "required_for_type": required_dims,
        "not_applicable": not_applicable,
    }
    return write_receipt(artifact_id, decision_id, blocks, warns, summary, declaration_path, receipt_dir)


def write_receipt(artifact_id, decision_id, blocks, warns, summary, declaration_path, receipt_dir):
    verdict = "DENY" if blocks else "ALLOW"
    receipt_dir = Path(receipt_dir)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_type": "USEFULNESS_SURFACE_GATE_DECISION",
        "schema_version": VERSION,
        "decision_id": decision_id,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "policy_path": "metablooms/governance/usefulness_surface/allow",
        "artifact_id": artifact_id,
        "result": verdict,
        "block_count": len(blocks),
        "warn_count": len(warns),
        "blocks": blocks,
        "warnings": warns,
        "summary": summary,
        "input_summary": {
            "declaration_path": str(declaration_path) if declaration_path else None,
            "declaration_sha256": sha256_path(Path(declaration_path)) if declaration_path and Path(declaration_path).exists() else None,
        }
    }
    out = receipt_dir / f"USEFULNESS_SURFACE_DECISION_{int(time.time()*1000)}_{decision_id[:8]}.json"
    tmp = out.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(tmp, out)
    receipt["receipt_path"] = str(out)
    receipt["receipt_sha256"] = sha256_path(out)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


def main():
    require_dash_s()
    ap = argparse.ArgumentParser(description="MetaBlooms Usefulness Surface Gate v1")
    ap.add_argument("--declaration", required=True)
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    args = ap.parse_args()
    p = Path(args.declaration)
    declaration = json.loads(p.read_text(encoding="utf-8"))
    result = validate(declaration, p, Path(args.receipt_dir))
    raise SystemExit(0 if result["result"] == "ALLOW" else 1)

if __name__ == "__main__":
    main()
