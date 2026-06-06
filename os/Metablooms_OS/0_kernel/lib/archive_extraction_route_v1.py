#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shutil, subprocess, time, zipfile
from pathlib import Path
import sys
_EXECUTION_LIB = Path(__file__).resolve().parent / "execution"
if str(_EXECUTION_LIB) not in sys.path:
    sys.path.insert(0, str(_EXECUTION_LIB))
from bounded_subprocess_compat_v1 import run_compat

SCHEMA_VERSION='ARCHIVE_EXTRACTION_ROUTE_v1'
REQUIRED_ROOT_FILES=['boot_manifest_v1.json','bin/mb','0_kernel/lib/filesystem_safety_v1.py']

def utc_now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())

def load_fs(root:Path):
    import importlib.util
    modpath=root/'0_kernel/lib/filesystem_safety_v1.py'
    spec=importlib.util.spec_from_file_location('filesystem_safety_v1', modpath)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod) # type: ignore
    return mod

def unsafe_member(name:str)->bool:
    return name.startswith('/') or name.startswith('\\\\') or '/../' in ('/'+name) or name.endswith('/..') or '\x00' in name

def zip_preflight(archive:Path):
    issues=[]; info={}
    if not archive.exists():
        return {'verdict':'EXTRACTION_PREFLIGHT_BLOCK','issues':[{'reason':'archive_missing','archive':str(archive)}], 'info':info}
    try:
        with zipfile.ZipFile(archive) as z:
            bad=z.testzip(); names=z.namelist(); info['entries']=len(names); info['zipfile_testzip_bad_member']=bad
            if bad: issues.append({'reason':'zip_integrity_failed','bad_member':bad})
            dup=sorted({n for n in names if names.count(n)>1}); info['duplicate_entry_count']=len(dup)
            crit=[n for n in dup if n.startswith('Metablooms_OS/bin/') or n.startswith('Metablooms_OS/0_kernel/')]
            if crit: issues.append({'reason':'duplicate_critical_entries','entries':crit[:20]})
            unsafe=[n for n in names if unsafe_member(n)]; info['unsafe_entry_count']=len(unsafe)
            if unsafe: issues.append({'reason':'unsafe_archive_paths','entries':unsafe[:20]})
            has_root=any(n.startswith('Metablooms_OS/') for n in names); info['has_metablooms_root']=has_root
            if not has_root: issues.append({'reason':'missing_metablooms_root_prefix'})
    except Exception as e:
        issues.append({'reason':'archive_open_failed','error':repr(e)})
    return {'verdict':'EXTRACTION_PREFLIGHT_PASS' if not issues else 'EXTRACTION_PREFLIGHT_BLOCK','issues':issues,'info':info}

def top_root(staging:Path)->Path:
    candidate=staging/'Metablooms_OS'
    return candidate if candidate.exists() else staging

def extraction_route(archive:Path,dest:Path,replace:bool=False,timeout:int=240):
    started=utc_now(); archive=archive.resolve(); dest=dest.resolve(); dest_parent=dest.parent
    dest_parent.mkdir(parents=True,exist_ok=True)
    pre=zip_preflight(archive)
    if pre['verdict']!='EXTRACTION_PREFLIGHT_PASS':
        return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'preflight','archive':str(archive),'dest':str(dest),'preflight':pre,'created_utc':started}
    # Extract into staging under destination parent, never /tmp, preserving same mount for final directory rename.
    staging=dest_parent/f'.{dest.name}.extracting.{os.getpid()}.{int(time.time())}'
    if staging.exists(): shutil.rmtree(staging)
    staging.mkdir(parents=True)
    fs=None
    try:
        # Need fs module from current runtime if available; otherwise use extracted module after unzip for finalization.
        cmd=['python3','-S','-m','zipfile','-e',str(archive),str(staging)]
        proc=run_compat(cmd, timeout_seconds=min(int(timeout),30), operation_type="archive_extraction_zipfile_command", stage="archive_extraction_route_v1", cwd=str(dest_parent), allowed_roots=[str(dest_parent), "/mnt/data"])
        if proc.returncode!=0:
            return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'extract','archive':str(archive),'dest':str(dest),'staging':str(staging),'returncode':proc.returncode,'stdout_tail':proc.stdout[-1000:],'stderr_tail':proc.stderr[-2000:],'created_utc':started}
        extracted_root=top_root(staging)
        fs=load_fs(extracted_root)
        # Finalization marker is written only after extraction command returns and required files exist.
        missing=[rel for rel in REQUIRED_ROOT_FILES if not (extracted_root/rel).exists()]
        if missing:
            fs.write_partial_lock(extracted_root,'required_root_files_missing_after_extract',{'missing':missing})
            return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'required-files','archive':str(archive),'dest':str(dest),'staging':str(staging),'missing':missing,'created_utc':started}
        mark=fs.mark_finalized(extracted_root, archive)
        if mark.get('verdict')!='FINALIZATION_MARKED':
            fs.write_partial_lock(extracted_root,'finalization_hook_failed',{'mark':mark})
            return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'finalization','archive':str(archive),'dest':str(dest),'staging':str(staging),'mark':mark,'created_utc':started}
        final_pre=fs.atomic_replace_preflight(extracted_root, dest)
        if final_pre.get('verdict')!='ATOMIC_REPLACE_SAFE':
            fs.write_partial_lock(extracted_root,'destination_mount_preflight_failed',{'preflight':final_pre})
            return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'atomic-preflight','archive':str(archive),'dest':str(dest),'staging':str(staging),'preflight':final_pre,'created_utc':started}
        backup=None
        if dest.exists():
            if not replace:
                fs.write_partial_lock(extracted_root,'destination_exists_replace_not_allowed')
                return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'publish','reason':'destination_exists_replace_not_allowed','archive':str(archive),'dest':str(dest),'staging':str(staging),'created_utc':started}
            backup=dest_parent/f'.{dest.name}.previous.{int(time.time())}'
            os.replace(dest, backup)
        # If archive had Metablooms_OS/ root, publish that directory; if not, publish staging.
        os.replace(extracted_root, dest)
        # Remove empty staging shell if different.
        try:
            if staging.exists() and staging != dest:
                shutil.rmtree(staging)
        except Exception:
            pass
        final=fs.validate_finalized_root(dest)
        verdict='EXTRACTION_ROUTE_PASS' if final.get('verdict')=='FINALIZED_ROOT_PASS' else 'EXTRACTION_ROUTE_BLOCK'
        return {'schema_version':SCHEMA_VERSION,'verdict':verdict,'archive':str(archive),'dest':str(dest),'backup':str(backup) if backup else None,'finalization_validation':final,'preflight':pre,'publish_preflight':final_pre,'created_utc':started,'completed_utc':utc_now()}
    except Exception as e:
        if fs and staging.exists():
            try: fs.write_partial_lock(top_root(staging),'extraction_route_exception',{'error':repr(e)})
            except Exception: pass
        return {'schema_version':SCHEMA_VERSION,'verdict':'EXTRACTION_ROUTE_BLOCK','stage':'exception','archive':str(archive),'dest':str(dest),'staging':str(staging),'error':repr(e),'created_utc':started}

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--archive',required=True); ap.add_argument('--dest',required=True); ap.add_argument('--replace',action='store_true'); ap.add_argument('--timeout',type=int,default=240); ap.add_argument('--json',action='store_true')
    a=ap.parse_args(argv); out=extraction_route(Path(a.archive),Path(a.dest),a.replace,a.timeout)
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if out.get('verdict')=='EXTRACTION_ROUTE_PASS' else 21
if __name__=='__main__': raise SystemExit(main())
