#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import time
from pathlib import Path

TARGET_PATHS = [
    "0_kernel/lib/filesystem_safety_v1.py",
    "0_kernel/lib/execution/bounded_subprocess_wrapper_v1.py",
    "0_kernel/cartridges/inline_project_tracker/TRACKER_STAGE_FINALIZATION_HOOK_v1.py",
    "0_kernel/cartridges/inline_project_tracker/TRACKER_STATE_UPDATER_v1.py",
    "0_kernel/lib/trace_diff_logger_v1.py",
    "0_kernel/lib/archive_method_router_v1.py",
    "0_kernel/validators/validate_bounded_subprocess_callsite_policy_stage4_v1.py",
]
REQUIRED_IMPORT = "atomic_json_compat_v1"
BLOCKED_TEXT_PATTERNS = [
    r"json\.dump\s*\(",
    r"\.write_text\s*\(\s*json\.dumps\s*\(",
    r"open\s*\([^\n]*(?:['\"]w['\"]|['\"]a['\"])",
    r"\.open\s*\([^\n]*(?:['\"]w['\"]|['\"]a['\"])",
]
ALLOWED_WITHIN = {
    "0_kernel/lib/execution/bounded_subprocess_wrapper_v1.py": ["json.dumps(packet", "json.dumps(obj", "json.dumps(errors"],
}

def utc_now():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

def scan(path: Path, rel: str):
    issues=[]
    txt=path.read_text(encoding="utf-8", errors="ignore")
    if REQUIRED_IMPORT not in txt:
        issues.append({"path":rel,"kind":"missing_atomic_json_compat_import","line":0})
    for i,line in enumerate(txt.splitlines(),1):
        s=line.strip()
        # stdout JSON is permitted; direct JSON file writes are not.
        if s.startswith("print(json.dumps") or "= json.dumps(" in s or "json.dumps(" in s and "write_text" not in s and "json.dump(" not in s and "open(" not in s:
            continue
        for pat in BLOCKED_TEXT_PATTERNS:
            if re.search(pat, line):
                # Writer internals are not part of this target list; compat import should now own file writes.
                issues.append({"path":rel,"line":i,"kind":"direct_json_or_file_write_pattern","pattern":pat,"snippet":s[:160]})
    return issues

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="/mnt/data/Metablooms_OS"); ap.add_argument("--json-out")
    a=ap.parse_args(); root=Path(a.root).resolve(); issues=[]; checked=[]
    for rel in TARGET_PATHS:
        p=root/rel
        if not p.exists():
            issues.append({"path":rel,"kind":"missing_target"}); continue
        checked.append(rel); issues.extend(scan(p,rel))
    out={"artifact_type":"ATOMIC_JSON_WRITER_CALLER_RETROFIT_POLICY_STAGE3_v1","created_utc":utc_now(),"root":str(root),"verdict":"PASS" if not issues else "FAIL","checked_count":len(checked),"checked_paths":checked,"issue_count":len(issues),"issues":issues,"policy":"Stage3 high-value retrofitted callers must import atomic_json_compat_v1 and must not retain direct json.dump/open/write_text(json.dumps) file-output patterns."}
    text=json.dumps(out,indent=2,sort_keys=True)+"\n"
    if a.json_out:
        p=Path(a.json_out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(text,encoding="utf-8")
    print(text)
    return 0 if out["verdict"]=="PASS" else 2
if __name__=="__main__":
    raise SystemExit(main())
