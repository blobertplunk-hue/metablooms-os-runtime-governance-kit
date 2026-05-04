#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,os,time
from pathlib import Path
import sys
_IO_LIB = Path(__file__).resolve().parent / "io"
if str(_IO_LIB) not in sys.path:
    sys.path.insert(0, str(_IO_LIB))
from atomic_json_compat_v1 import write_json_file
SCHEMA_VERSION="TRACE_DIFF_LOGGER_v1"
def utc_now(): return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
def hfile(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""): h.update(b)
    return h.hexdigest()
def manifest(root:Path,max_files=None):
    entries=[]; count=0; size=0
    for base,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in {".git","__pycache__"}]
        for n in sorted(files):
            p=Path(base)/n; rel=str(p.relative_to(root))
            try: st=p.stat(); digest=hfile(p)
            except Exception as e: entries.append({"path":rel,"error":repr(e)}); continue
            entries.append({"path":rel,"sha256":digest,"bytes":st.st_size}); count+=1; size+=st.st_size
            if max_files and count>=max_files: break
        if max_files and count>=max_files: break
    rh=hashlib.sha256("\n".join(f"{e.get('path')} {e.get('sha256','ERR')} {e.get('bytes','?')}" for e in entries).encode()).hexdigest()
    return {"schema_version":SCHEMA_VERSION,"root":str(root),"created_utc":utc_now(),"file_count":count,"bytes":size,"root_hash":rh,"entries":entries,"truncated":bool(max_files and count>=max_files)}
def diff(old,new,max_list):
    oe={e["path"]:e for e in old.get("entries",[])} if old else {}; ne={e["path"]:e for e in new.get("entries",[])}
    added=sorted(set(ne)-set(oe)); removed=sorted(set(oe)-set(ne)); changed=sorted(p for p in set(ne)&set(oe) if ne[p].get("sha256")!=oe[p].get("sha256") or ne[p].get("bytes")!=oe[p].get("bytes"))
    return {"schema_version":SCHEMA_VERSION,"artifact_type":"DIFFERENTIAL_TRACE_SUMMARY","created_utc":utc_now(),"base_root_hash":old.get("root_hash") if old else None,"new_root_hash":new.get("root_hash"),"base_file_count":old.get("file_count") if old else 0,"new_file_count":new.get("file_count"),"base_bytes":old.get("bytes") if old else 0,"new_bytes":new.get("bytes"),"delta_counts":{"added":len(added),"removed":len(removed),"changed":len(changed)},"samples":{"added":added[:max_list],"removed":removed[:max_list],"changed":changed[:max_list]},"omitted_counts":{"added":max(0,len(added)-max_list),"removed":max(0,len(removed)-max_list),"changed":max(0,len(changed)-max_list)},"policy":"Traces emit counts/root hash/bounded samples; full hash manifests remain artifacts."}
def w(path,payload): write_json_file(Path(path), payload, operation_id="trace_diff_logger_write_json", allowed_roots=["/mnt/data"], create_parent=True)
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); ap.add_argument("--baseline"); ap.add_argument("--write-baseline"); ap.add_argument("--write-summary"); ap.add_argument("--max-list",type=int,default=25); ap.add_argument("--max-files",type=int)
    a=ap.parse_args(argv); old=json.loads(Path(a.baseline).read_text()) if a.baseline and Path(a.baseline).exists() else None; new=manifest(Path(a.root),a.max_files); out=diff(old,new,a.max_list)
    if a.write_baseline: w(a.write_baseline,new)
    if a.write_summary: w(a.write_summary,out)
    print(json.dumps(out,indent=2,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
