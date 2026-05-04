#!/usr/bin/env python3
from __future__ import annotations
import ast, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "0_kernel/registry/tool_governance/ATOMIC_APPEND_LOG_WRITER_CALLSITE_POLICY_STAGE5_v1.json"
EXCLUDE_PARTS = ("runtime/receipts/", "runtime/stage_bundles/", "runtime/tmp/", "__pycache__", ".stage3_append_bak_", ".stage4_bak_", ".stage5_append_bak_")
WARNING_EXEMPT = {"runtime/governance/legacy_archives/claude_memory_sync_writer_v1.py": "legacy_archive_exempt"}
CANONICAL_FILES = {
    "0_kernel/lib/io/atomic_append_log_writer_v1.py",
    "0_kernel/lib/io/atomic_append_log_compat_v1.py",
    "0_kernel/validators/validate_atomic_append_log_writer_callsite_policy_stage3_v1.py",
    "0_kernel/validators/validate_atomic_append_log_writer_callsite_policy_stage4_v1.py",
    "0_kernel/validators/validate_atomic_append_log_writer_callsite_policy_stage5_v1.py",
}
def _is_append_open_call(n: ast.Call) -> bool:
    func=n.func
    name=func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ""
    if name != "open": return False
    if len(n.args) >= 2 and isinstance(n.args[1], ast.Constant) and isinstance(n.args[1].value, str) and "a" in n.args[1].value: return True
    for kw in n.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str) and "a" in kw.value.value: return True
    return False
def scan():
    rows=[]
    files=list((ROOT/"0_kernel").rglob("*.py"))+list((ROOT/"runtime").rglob("*.py"))+list((ROOT/"tests").rglob("*.py"))
    for p in files:
        rel=str(p.relative_to(ROOT))
        if any(part in rel for part in EXCLUDE_PARTS): continue
        try: tree=ast.parse(p.read_text(encoding="utf-8"))
        except Exception as exc:
            rows.append({"file":rel,"line":0,"classification":"parse_error","detail":str(exc)}); continue
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call) or not _is_append_open_call(n): continue
            if rel in CANONICAL_FILES: classification="canonical_append_writer_internal"
            elif rel in WARNING_EXEMPT: classification=WARNING_EXEMPT[rel]
            else: classification="blocking_direct_append_open"
            rows.append({"file":rel,"line":n.lineno,"classification":classification,"detail":"direct append-open call"})
    return rows
def main():
    policy=json.loads(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    rows=scan(); blocking=[r for r in rows if r.get("classification") in {"blocking_direct_append_open","parse_error"}]
    warnings=[r for r in rows if r not in blocking]
    out={"artifact_type":"AtomicAppendLogWriterCallsitePolicyStage5Result.v1","created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),"policy_path":str(POLICY.relative_to(ROOT)) if POLICY.exists() else None,"canonical_writer":policy.get("canonical_writer"),"compat_adapter":policy.get("compat_adapter"),"remaining_direct_append_open_count":len(rows),"blocking_count":len(blocking),"warning_count":len(warnings),"remaining":rows,"verdict":"PASS" if not blocking else "FAIL"}
    print(json.dumps(out, indent=2, sort_keys=True)); return 0 if out["verdict"] == "PASS" else 2
if __name__ == "__main__": raise SystemExit(main())
