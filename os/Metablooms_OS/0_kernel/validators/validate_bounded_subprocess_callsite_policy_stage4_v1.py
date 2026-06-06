#!/usr/bin/env python3
"""MetaBlooms Stage4 bounded subprocess callsite policy gate.

Blocks direct subprocess/os command invocation in live governance code unless the
file is the bounded subprocess primitive/compat adapter itself. Test/eval,
legacy, vendor, receipt, bundle, and failure-learning snapshot code is reported
but not blocking in this Stage4 gate.
"""
from __future__ import annotations
import ast, argparse, json, time
from pathlib import Path
import sys
_IO_LIB = Path(__file__).resolve().parents[1] / "lib" / "io"
if str(_IO_LIB) not in sys.path:
    sys.path.insert(0, str(_IO_LIB))
from atomic_json_compat_v1 import write_json_file

LIVE_PREFIXES = ("0_kernel/", "runtime/governance/")
EXEMPT_EXACT = {
    "0_kernel/lib/execution/bounded_subprocess_wrapper_v1.py",
    "0_kernel/lib/execution/bounded_subprocess_compat_v1.py",
}
EXEMPT_PARTS = (
    "/0_kernel/vendor/",
    "/0_kernel/registry/failure_learning/",
    "/runtime/governance/legacy_archives/",
    "/runtime/receipts/",
    "/runtime/stage_bundles/",
    "/receipts/",
    "/_registry_backups/",
)
TEST_PREFIXES = ("tests/", "runtime/evals/")
DANGEROUS_ATTRS = {"run", "Popen", "call", "check_call", "check_output"}
OS_ATTRS = {"system", "popen"}

def utc_now() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

def classify(rel: str) -> str:
    s = "/" + rel
    if rel in EXEMPT_EXACT:
        return "bounded_wrapper_internal_exempt"
    if any(part in s for part in EXEMPT_PARTS):
        return "snapshot_vendor_legacy_or_artifact_exempt"
    if rel.startswith(TEST_PREFIXES) or "/tests/" in s:
        return "test_eval_fixture_warn"
    if rel.startswith(LIVE_PREFIXES):
        return "live_governance_code"
    return "other_warn"

def scan_file(path: Path, root: Path):
    rel = path.relative_to(root).as_posix()
    zone = classify(rel)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
    except SyntaxError as exc:
        return [{"path": rel, "line": getattr(exc, "lineno", 0), "zone": zone, "kind": "syntax_error", "blocking": zone == "live_governance_code", "detail": str(exc)}]
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                if f.value.id == "subprocess" and f.attr in DANGEROUS_ATTRS:
                    hits.append({"path": rel, "line": getattr(node, "lineno", 0), "zone": zone, "kind": f"subprocess.{f.attr}", "blocking": zone == "live_governance_code"})
                if f.value.id == "os" and f.attr in OS_ATTRS:
                    hits.append({"path": rel, "line": getattr(node, "lineno", 0), "zone": zone, "kind": f"os.{f.attr}", "blocking": zone == "live_governance_code"})
    return hits

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="/mnt/data/Metablooms_OS")
    ap.add_argument("--json-out")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    hits = []
    for p in sorted(root.rglob("*.py")):
        hits.extend(scan_file(p, root))
    blocking = [h for h in hits if h.get("blocking")]
    summary = {}
    for h in hits:
        summary[h["zone"]] = summary.get(h["zone"], 0) + 1
    out = {
        "artifact_type": "METABLOOMS_BOUNDED_SUBPROCESS_CALLSITE_POLICY_GATE_STAGE4_v1",
        "created_utc": utc_now(),
        "root": str(root),
        "verdict": "PASS" if not blocking else "FAIL",
        "blocking_count": len(blocking),
        "summary_by_zone": summary,
        "blocking_hits": blocking,
        "all_hits": hits,
        "policy": "Direct subprocess/os command invocation is blocked in live governance code outside bounded wrapper internals; non-live snapshots/tests/vendor are warnings for later stages.",
    }
    text = json.dumps(out, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        write_json_file(Path(args.json_out), out, operation_id="bounded_subprocess_policy_gate_json_out", allowed_roots=["/mnt/data"], create_parent=True)
    print(text)
    return 0 if out["verdict"] == "PASS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
