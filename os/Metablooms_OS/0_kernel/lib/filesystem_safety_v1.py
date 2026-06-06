#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,shutil,subprocess,tempfile,time,uuid
from pathlib import Path
import sys
_EXECUTION_LIB = Path(__file__).resolve().parent / "execution"
if str(_EXECUTION_LIB) not in sys.path:
    sys.path.insert(0, str(_EXECUTION_LIB))
from bounded_subprocess_compat_v1 import run_compat
_IO_LIB = Path(__file__).resolve().parent / "io"
if str(_IO_LIB) not in sys.path:
    sys.path.insert(0, str(_IO_LIB))
from atomic_json_compat_v1 import write_json_file
SCHEMA_VERSION="FILESYSTEM_SAFETY_v1"
FINALIZATION_IN_PROGRESS=".MB_FINALIZATION_IN_PROGRESS.json"
FINALIZATION_SUCCESS=".MB_FINALIZATION_SUCCESS.json"
PARTIAL_ROOT_LOCK=".MB_PARTIAL_ROOT_LOCK.json"
def utc_now(): return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
def df_record(path:Path):
    target=path if path.exists() else path.parent
    p=run_compat(["df","-P",str(target)],timeout_seconds=10,operation_type="filesystem_df_probe",stage="filesystem_safety_v1")
    if p.returncode!=0: return {"ok":False,"path":str(path),"returncode":p.returncode,"stderr":p.stderr[-1000:]}
    lines=[x for x in p.stdout.splitlines() if x.strip()]
    if len(lines)<2: return {"ok":False,"path":str(path),"stdout":p.stdout}
    parts=lines[-1].split()
    return {"ok":True,"path":str(path),"filesystem":parts[0],"mount_point":parts[5] if len(parts)>5 else None,"raw":lines[-1]}
def dev(path:Path):
    target=path if path.exists() else path.parent
    return os.stat(target).st_dev
def atomic_replace_preflight(tmp_path:Path,dst_path:Path):
    tmp_path=Path(tmp_path); dst_path=Path(dst_path)
    out={"schema_version":SCHEMA_VERSION,"check":"atomic_replace_preflight","tmp_path":str(tmp_path),"dst_path":str(dst_path),"tmp_df":df_record(tmp_path.parent),"dst_df":df_record(dst_path.parent),"tmp_st_dev":dev(tmp_path.parent),"dst_st_dev":dev(dst_path.parent),"created_utc":utc_now()}
    out["same_device"]=out["tmp_st_dev"]==out["dst_st_dev"]; out["same_mount_point"]=out["tmp_df"].get("mount_point")==out["dst_df"].get("mount_point")
    out["verdict"]="ATOMIC_REPLACE_SAFE" if out["same_device"] and out["same_mount_point"] else "ATOMIC_REPLACE_BLOCK"
    return out
def atomic_write_json(path:Path,payload:dict):
    path=Path(path)
    pre={"schema_version":SCHEMA_VERSION,"check":"canonical_atomic_json_writer_v1","path":str(path),"created_utc":utc_now()}
    try:
        decision=write_json_file(path,payload,operation_id="filesystem_safety_atomic_write_json",allowed_roots=["/mnt/data"],create_parent=True)
        pre["writer_decision"]={"status":decision.get("status"),"receipt_path":decision.get("receipt_path"),"target_sha256":decision.get("target_sha256")}
        return {"verdict":"ATOMIC_WRITE_PASS","path":str(path),"preflight":pre}
    except Exception as e:
        pre["writer_error"]=repr(e)
        return {"verdict":"ATOMIC_WRITE_BLOCK","path":str(path),"preflight":pre}
def tree_stats(root:Path):
    files=dirs=bytes_total=0
    for base,dirnames,filenames in os.walk(root):
        dirs+=len(dirnames)
        for n in filenames:
            try:
                st=(Path(base)/n).lstat(); files+=1; bytes_total+=st.st_size
            except FileNotFoundError: pass
    return {"files":files,"dirs":dirs,"bytes":bytes_total}
def write_partial_lock(root:Path,reason:str,extra=None):
    p={"schema_version":SCHEMA_VERSION,"artifact_type":"PARTIAL_ROOT_LOCK","verdict":"PARTIAL_ROOT_BLOCK","reason":reason,"created_utc":utc_now()}
    if extra: p.update(extra)
    return atomic_write_json(Path(root)/PARTIAL_ROOT_LOCK,p)
def mark_finalized(root:Path,source:Path|None=None):
    root=Path(root); payload={"schema_version":SCHEMA_VERSION,"artifact_type":"ROOT_FINALIZATION_SUCCESS","verdict":"ATOMIC_SUCCESS","root":str(root),"source":str(source) if source else None,"stats":tree_stats(root),"created_utc":utc_now(),"invariant":"Root trusted only after this final byte marker exists."}
    atomic_write_json(root/FINALIZATION_IN_PROGRESS,{"verdict":"IN_PROGRESS","root":str(root),"created_utc":utc_now()})
    res=atomic_write_json(root/FINALIZATION_SUCCESS,payload)
    try: (root/FINALIZATION_IN_PROGRESS).unlink()
    except FileNotFoundError: pass
    return {"verdict":"FINALIZATION_MARKED" if res["verdict"]=="ATOMIC_WRITE_PASS" else "FINALIZATION_MARK_BLOCK","write_result":res,"payload":payload}
def validate_finalized_root(root:Path):
    root=Path(root); issues=[]; marker=root/FINALIZATION_SUCCESS
    if (root/PARTIAL_ROOT_LOCK).exists(): issues.append("partial_root_lock_present")
    if (root/FINALIZATION_IN_PROGRESS).exists(): issues.append("finalization_in_progress_marker_present")
    if not marker.exists(): issues.append("finalization_success_marker_missing")
    payload=None
    if marker.exists():
        try: payload=json.loads(marker.read_text(encoding="utf-8"))
        except Exception as e: issues.append({"marker_parse_error":str(e)})
    return {"schema_version":SCHEMA_VERSION,"check":"validate_finalized_root","root":str(root),"verdict":"FINALIZED_ROOT_PASS" if not issues else "FINALIZED_ROOT_BLOCK","issues":issues,"stats":tree_stats(root) if root.exists() else {},"marker":payload,"created_utc":utc_now()}
def safe_copytree_finalize(src:Path,dst:Path):
    src=Path(src); dst=Path(dst); staging=dst.parent/f".{dst.name}.staging.{uuid.uuid4().hex[:12]}"
    pre=atomic_replace_preflight(staging,dst)
    if pre["verdict"]!="ATOMIC_REPLACE_SAFE": return {"verdict":"COPYTREE_FINALIZE_BLOCK","reason":"cross_mount_or_device","preflight":pre}
    try:
        shutil.copytree(src,staging,symlinks=True); before=tree_stats(src); after=tree_stats(staging)
        if before["files"]!=after["files"] or before["bytes"]!=after["bytes"]:
            write_partial_lock(staging,"copytree_stats_mismatch",{"source_stats":before,"staging_stats":after}); return {"verdict":"COPYTREE_FINALIZE_BLOCK","reason":"copytree_stats_mismatch","staging":str(staging)}
        mark=mark_finalized(staging,src)
        if mark["verdict"]!="FINALIZATION_MARKED": write_partial_lock(staging,"finalization_marker_failed"); return {"verdict":"COPYTREE_FINALIZE_BLOCK","reason":"finalization_marker_failed"}
        if dst.exists(): write_partial_lock(staging,"destination_exists_no_atomic_directory_replace"); return {"verdict":"COPYTREE_FINALIZE_BLOCK","reason":"destination_exists_no_atomic_directory_replace","staging":str(staging)}
        os.replace(staging,dst); final=validate_finalized_root(dst)
        return {"verdict":"COPYTREE_FINALIZE_PASS" if final["verdict"]=="FINALIZED_ROOT_PASS" else "COPYTREE_FINALIZE_BLOCK","final_validation":final,"preflight":pre}
    except Exception as e:
        if staging.exists(): write_partial_lock(staging,"copytree_finalize_exception",{"error":repr(e)})
        return {"verdict":"COPYTREE_FINALIZE_BLOCK","reason":"exception","error":repr(e),"staging":str(staging)}
def main(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("preflight"); p.add_argument("--tmp",required=True); p.add_argument("--dst",required=True)
    p=sub.add_parser("mark-finalized"); p.add_argument("--root",required=True); p.add_argument("--source")
    p=sub.add_parser("validate-root"); p.add_argument("--root",required=True)
    p=sub.add_parser("copytree-finalize"); p.add_argument("--src",required=True); p.add_argument("--dst",required=True)
    a=ap.parse_args(argv)
    if a.cmd=="preflight": out=atomic_replace_preflight(Path(a.tmp),Path(a.dst))
    elif a.cmd=="mark-finalized": out=mark_finalized(Path(a.root),Path(a.source) if a.source else None)
    elif a.cmd=="validate-root": out=validate_finalized_root(Path(a.root))
    else: out=safe_copytree_finalize(Path(a.src),Path(a.dst))
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not out.get("verdict","").endswith("BLOCK") else 2
if __name__=="__main__": raise SystemExit(main())
