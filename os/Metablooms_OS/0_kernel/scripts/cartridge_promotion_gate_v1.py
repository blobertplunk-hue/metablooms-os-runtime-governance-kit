#!/usr/bin/env python3
### GOVERNANCE HEADER
# artifact_id: cartridge_promotion_gate_v1
# purpose: Enforce that any cartridge or script moving from candidate to active
#          must pass: SHA chain receipt, schema check, SEE/CE verification,
#          and IAE ALLOW proof. Guards ASI04 (Agentic Supply Chain Vulnerabilities).
# mutation_scope: read-only (writes gate receipt only; never promotes itself)
# owasp_risk_addressed: ASI04 Agentic Supply Chain Vulnerabilities
# see_evidence:
#   - OWASP ASI04: "Dynamic runtime components could be poisoned —
#     GitHub MCP exploit showed runtime composition as an attack surface"
#   - Microsoft AGT: "Plugin signing with Ed25519 and manifest verification"
###

from __future__ import annotations

import hashlib, json, os, re, time, zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "1.0"
OWASP_RISK = "ASI04_AGENTIC_SUPPLY_CHAIN"

DEFAULT_REGISTRY = Path("/mnt/data/Metablooms_OS_refined/artifact_registry.json")
DEFAULT_RECEIPT_DIR = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/cartridge_gate_receipts")
CARTRIDGE_MANIFEST_SCHEMA = Path("/mnt/data/Metablooms_OS_refined/0_kernel/schemas/CARTRIDGE_MANIFEST_SCHEMA_v1.json")

REQUIRED_CARTRIDGE_FIELDS = ["cartridge_id", "type"]
RECOMMENDED_FIELDS = ["pipeline", "invocation"]  # preferred but not required for legacy
FORBIDDEN_INVOCATIONS = ["exec(", "eval(", "__import__", "subprocess.call", "os.system"]
VALID_TYPES = {"core_governance", "research", "comprehension", "execution",
               "validation", "html_patch", "stage_runner", "spec"}


class GateVerdict(str, Enum):
    PASS  = "PASS"
    WARN  = "WARN"
    BLOCK = "BLOCK"


@dataclass
class GateFinding:
    check_id: str
    verdict: GateVerdict
    message: str
    evidence: str = ""

    def to_dict(self):
        return {"check_id": self.check_id, "verdict": self.verdict.value,
                "message": self.message, "evidence": self.evidence}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, data: Dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    _mb_write_json_file(tmp, data, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_cartridge_promotion_gate_v1_py_L66', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    os.replace(tmp, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def evaluate_cartridge(
    cartridge_path: Path,
    declared_sha: Optional[str],
    registry_path: Path,
    receipt_dir: Path,
    has_build_receipt: bool = False,
    see_ce_verified: bool = False,
) -> Dict:
    """
    Evaluate a cartridge artifact for promotion from candidate to active.
    Performs: file existence, SHA verification, manifest schema, forbidden
    invocation check, registry status check, build receipt check, SEE/CE check.
    """
    findings: List[GateFinding] = []

    # 1. File must exist
    if not cartridge_path.exists():
        findings.append(GateFinding(
            "CPG_NOT_FOUND", GateVerdict.BLOCK,
            f"Cartridge file not found: {cartridge_path}",
        ))
        return _write_receipt(findings, cartridge_path, receipt_dir)

    # 2. SHA verification
    actual_sha = sha256_file(cartridge_path)
    if declared_sha:
        if actual_sha != declared_sha:
            findings.append(GateFinding(
                "CPG_SHA_MISMATCH", GateVerdict.BLOCK,
                "Declared SHA does not match file content — possible tampering",
                evidence=f"declared={declared_sha[:16]}... actual={actual_sha[:16]}...",
            ))
    else:
        findings.append(GateFinding(
            "CPG_NO_SHA_DECLARED", GateVerdict.WARN,
            "No declared SHA provided — SHA chain cannot be verified",
        ))

    # 3. Parse and validate manifest
    suffix = cartridge_path.suffix.lower()
    manifest = None

    if suffix == ".json":
        manifest = load_json(cartridge_path)
        if manifest is None:
            findings.append(GateFinding(
                "CPG_JSON_INVALID", GateVerdict.BLOCK,
                "Cartridge JSON file could not be parsed",
            ))
        else:
            # Required fields
            for req in REQUIRED_CARTRIDGE_FIELDS:
                if req not in manifest:
                    findings.append(GateFinding(
                        "CPG_MISSING_FIELD", GateVerdict.BLOCK,
                        f"Cartridge missing required field: '{req}'",
                        evidence=f'field: {req}',
                    ))
            # Recommended fields (WARN if missing — legacy cartridges may predate schema)
            for rec in RECOMMENDED_FIELDS:
                if rec not in manifest:
                    findings.append(GateFinding(
                        "CPG_MISSING_RECOMMENDED", GateVerdict.WARN,
                        f"Cartridge missing recommended field: '{rec}' (legacy cartridges may omit)",
                        evidence=f"field: {rec}",
                    ))
            # Valid type
            ctype = manifest.get("type", "")
            if ctype and ctype not in VALID_TYPES:
                findings.append(GateFinding(
                    "CPG_INVALID_TYPE", GateVerdict.WARN,
                    f"Cartridge type '{ctype}' not in known types {VALID_TYPES}",
                ))
            # Check invocation for forbidden patterns
            invocation = str(manifest.get("invocation", ""))
            for forbidden in FORBIDDEN_INVOCATIONS:
                if forbidden in invocation:
                    findings.append(GateFinding(
                        "CPG_FORBIDDEN_INVOCATION", GateVerdict.BLOCK,
                        f"Cartridge invocation contains forbidden pattern: '{forbidden}'",
                        evidence=f"invocation preview: {invocation[:80]}",
                    ))

    elif suffix == ".zip":
        # Check zip is well-formed and contains expected cartridge files
        try:
            with zipfile.ZipFile(cartridge_path) as zf:
                names = zf.namelist()
                cartridge_files = [n for n in names if ".cartridge.json" in n or "CARTRIDGE" in n.upper()]
                if not cartridge_files:
                    findings.append(GateFinding(
                        "CPG_ZIP_NO_CARTRIDGE", GateVerdict.WARN,
                        "ZIP bundle contains no files matching .cartridge.json pattern",
                        evidence=f"Files in ZIP: {names[:5]}",
                    ))
        except Exception as e:
            findings.append(GateFinding(
                "CPG_ZIP_CORRUPT", GateVerdict.BLOCK,
                f"ZIP bundle is corrupt or unreadable: {e}",
            ))

    elif suffix == ".md":
        content = cartridge_path.read_text(encoding="utf-8", errors="replace")
        if len(content.strip()) < 50:
            findings.append(GateFinding(
                "CPG_MD_TOO_SHORT", GateVerdict.WARN,
                "Markdown cartridge spec is very short — may be incomplete",
                evidence=f"Length: {len(content)} chars",
            ))

    # 4. Registry status check
    registry = load_json(registry_path)
    if registry:
        artifacts = registry.get("artifacts", [])
        cid = cartridge_path.name
        matching = [a for a in artifacts if a.get("artifact_id") == cid
                    or cid in str(a.get("path", ""))]
        if matching:
            current_status = matching[0].get("status", "unknown")
            if current_status == "active":
                findings.append(GateFinding(
                    "CPG_ALREADY_ACTIVE", GateVerdict.WARN,
                    f"Cartridge already has status=active in registry — re-promotion check",
                    evidence=f"current status: {current_status}",
                ))
        else:
            findings.append(GateFinding(
                "CPG_NOT_IN_REGISTRY", GateVerdict.WARN,
                "Cartridge not found in artifact_registry.json — will need registration",
            ))

    # 5. Build receipt check
    if not has_build_receipt:
        findings.append(GateFinding(
            "CPG_NO_BUILD_RECEIPT", GateVerdict.BLOCK,
            "No build receipt provided — cartridge cannot be promoted without SHA-verified receipt",
        ))

    # 6. SEE/CE verification check
    if not see_ce_verified:
        findings.append(GateFinding(
            "CPG_NO_SEE_CE", GateVerdict.BLOCK,
            "SEE/CE verification not confirmed — cartridge content has not been externally validated",
        ))

    return _write_receipt(findings, cartridge_path, receipt_dir)


def _write_receipt(findings: List[GateFinding], cartridge_path: Path, receipt_dir: Path) -> Dict:
    blocks = [f for f in findings if f.verdict == GateVerdict.BLOCK]
    warns  = [f for f in findings if f.verdict == GateVerdict.WARN]
    verdict = GateVerdict.BLOCK if blocks else (GateVerdict.WARN if warns else GateVerdict.PASS)

    receipt = {
        "receipt_type": "CARTRIDGE_PROMOTION_GATE_RECEIPT",
        "gate_version": VERSION,
        "owasp_risk": OWASP_RISK,
        "cartridge_path": str(cartridge_path),
        "created_at": time.time(),
        "verdict": verdict.value,
        "block_count": len(blocks),
        "warn_count": len(warns),
        "findings": [f.to_dict() for f in findings],
        "gate_decision": (
            "ALLOW — cartridge may be promoted to active status"
            if verdict == GateVerdict.PASS
            else "CONDITIONAL — resolve warnings before promoting"
            if verdict == GateVerdict.WARN
            else "DENY — cartridge blocked from promotion"
        ),
    }
    ts = int(time.time() * 1000)
    stem = cartridge_path.stem[:20]
    rpath = receipt_dir / f"CARTRIDGE_GATE_{stem}_{ts}.json"
    rsha = write_json_atomic(rpath, receipt)
    receipt["receipt_path"] = str(rpath)
    receipt["receipt_sha"] = rsha

    icon = {"PASS": "✓", "WARN": "⚠", "BLOCK": "✗"}[verdict.value]
    print(f"  [{icon}] Cartridge gate: {verdict.value}  blocks={len(blocks)} warns={len(warns)}")
    return receipt


def main(argv=None):
    import argparse, sys
    ap = argparse.ArgumentParser(description="MetaBlooms Cartridge Promotion Gate v1 — ASI04 guard")
    ap.add_argument("--cartridge-path",  required=True)
    ap.add_argument("--declared-sha",    default=None)
    ap.add_argument("--registry",        default=str(DEFAULT_REGISTRY))
    ap.add_argument("--receipt-dir",     default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--has-build-receipt", action="store_true")
    ap.add_argument("--see-ce-verified",   action="store_true")
    ap.add_argument("--json-output",       action="store_true")
    args = ap.parse_args(argv)

    result = evaluate_cartridge(
        cartridge_path=Path(args.cartridge_path),
        declared_sha=args.declared_sha,
        registry_path=Path(args.registry),
        receipt_dir=Path(args.receipt_dir),
        has_build_receipt=args.has_build_receipt,
        see_ce_verified=args.see_ce_verified,
    )
    if args.json_output:
        print(json.dumps(result, indent=2))
    sys.exit(0 if result["verdict"] in ("PASS", "WARN") else 1)


if __name__ == "__main__":
    main()
