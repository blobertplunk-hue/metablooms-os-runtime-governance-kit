#!/usr/bin/env python3
from __future__ import annotations

# MetaBlooms Stage4 bounded subprocess enforcement shim.
from pathlib import Path as _MBPath
import sys as _MBSys
_MB_SELF = _MBPath(__file__).resolve()
for _MB_PARENT in [_MB_SELF] + list(_MB_SELF.parents):
    _MB_EXEC_LIB = _MB_PARENT / "0_kernel" / "lib" / "execution"
    if (_MB_EXEC_LIB / "bounded_subprocess_compat_v1.py").exists():
        if str(_MB_EXEC_LIB) not in _MBSys.path:
            _MBSys.path.insert(0, str(_MB_EXEC_LIB))
        break
from bounded_subprocess_compat_v1 import run as bounded_subprocess_run
import json,subprocess,tempfile,py_compile
from pathlib import Path
def find_root():
    here=Path(__file__).resolve()
    for p in [here.parent,*here.parents]:
        if (p/"boot_manifest_v1.json").exists() and (p/"0_kernel").exists(): return p
    return Path.cwd()
def run(cmd,cwd,timeout=45):
    p=bounded_subprocess_run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    try: payload=json.loads(p.stdout.strip())
    except Exception: payload={"stdout_tail":p.stdout[-2000:],"stderr_tail":p.stderr[-2000:]}
    return {"rc":p.returncode,"payload":payload}
def main():
    root=find_root(); issues=[]; checks={}
    fs=root/"0_kernel/lib/filesystem_safety_v1.py"; diff=root/"0_kernel/lib/trace_diff_logger_v1.py"
    for p in [fs,diff]:
        if not p.exists(): issues.append(f"missing:{p.relative_to(root)}")
        else:
            try: py_compile.compile(str(p),doraise=True); checks[str(p.relative_to(root))]="compile_pass"
            except Exception as e: issues.append({"compile_failure":str(p.relative_to(root)),"error":repr(e)})
    with tempfile.TemporaryDirectory(dir=str(root/"runtime")) as td0:
        td=Path(td0); src=td/"src"; src.mkdir(); (src/"a.txt").write_text("alpha")
        tmp=td/".atomic.tmp"; dst=td/"atomic.json"; tmp.write_text("x")
        checks["atomic_preflight"]=run(["python3","-S",str(fs),"preflight","--tmp",str(tmp),"--dst",str(dst)],root)
        if checks["atomic_preflight"]["payload"].get("verdict")!="ATOMIC_REPLACE_SAFE": issues.append("atomic_preflight_failed")
        checks["mark_finalized"]=run(["python3","-S",str(fs),"mark-finalized","--root",str(src)],root)
        checks["validate_finalized"]=run(["python3","-S",str(fs),"validate-root","--root",str(src)],root)
        if checks["validate_finalized"]["payload"].get("verdict")!="FINALIZED_ROOT_PASS": issues.append("finalized_root_validation_failed")
        base=td/"base.json"; checks["diff_initial"]=run(["python3","-S",str(diff),"--root",str(src),"--write-baseline",str(base),"--max-list","2"],root)
        (src/"a.txt").write_text("beta"); (src/"b.txt").write_text("new")
        checks["diff_delta"]=run(["python3","-S",str(diff),"--root",str(src),"--baseline",str(base),"--max-list","2"],root)
        dc=checks["diff_delta"]["payload"].get("delta_counts",{})
        if dc.get("added",0)<1 or dc.get("changed",0)<1: issues.append("diff_delta_failed")
    pol=root/"0_kernel/registry/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_POLICY_v1.json"
    if not pol.exists(): issues.append("filesystem_policy_missing")
    out={"schema_version":"FILESYSTEM_HANDLING_SAFETY_VALIDATION_v1","verdict":"PASS" if not issues else "FAIL","issues":issues,"checks":checks,"root":str(root)}
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=="__main__": raise SystemExit(main())
