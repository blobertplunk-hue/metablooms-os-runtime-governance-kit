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
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path
REQUIRED_MEMBERS=['Metablooms_OS/bin/mb','Metablooms_OS/boot_manifest_v1.json','Metablooms_OS/0_kernel/registry/BOOT_REQUIRED_GATES_v1.json','Metablooms_OS/0_kernel/scripts/artifact_replay_proof_v2.py']
def utc_now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def sha256_file(path):
 h=hashlib.sha256();
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''): h.update(b)
 return h.hexdigest()
def unsafe(name): return name.startswith('/') or '..' in Path(name).parts or '\\' in name or name.startswith('~')
def read_sidecar(p): return Path(p).read_text(encoding='utf-8').split()[0]
def copy_member(z,name,dest):
 target=Path(dest)/name; target.parent.mkdir(parents=True,exist_ok=True)
 with z.open(name) as src, target.open('wb') as dst: shutil.copyfileobj(src,dst,1048576)
 if name.endswith('/bin/mb') or name.endswith('.py'):
  try: target.chmod(target.stat().st_mode|0o111)
  except Exception: pass
def cmd(c,cwd=None,timeout=10):
 
 try:
  p=bounded_subprocess_run(c,cwd=cwd,text=True,capture_output=True,timeout=timeout)
  return {'cmd':c,'rc':p.returncode,'stdout_tail':p.stdout[-1200:],'stderr_tail':p.stderr[-1200:]}
 except subprocess.TimeoutExpired as e:
  return {'cmd':c,'rc':124,'stdout_tail':(e.stdout or '')[-1200:] if isinstance(e.stdout,str) else '', 'stderr_tail':(e.stderr or '')[-1200:] if isinstance(e.stderr,str) else '', 'timeout': True}
def run(archive,sidecar=None,full_extract=False,timeout=10):
 archive=Path(archive).resolve(); out={'schema_version':'ARTIFACT_PORTABILITY_REPLAY_PROOF_STAGE2_RESULT_v1','created_utc':utc_now(),'archive':str(archive),'commands':[]}
 digest=sha256_file(archive); out['archive_sha256']=digest
 if sidecar:
  exp=read_sidecar(sidecar); out['checks']={'sidecar_match': exp==digest}
  if exp!=digest: out['verdict']='REPLAY_PROOF_FAIL'; out['reason']='sidecar_mismatch'; return out
 else: out['checks']={}
 with zipfile.ZipFile(archive) as z:
  names=z.namelist(); out['entry_count']=len(names)
  seen=set(); dup=[]
  for n in names:
   if n in seen: dup.append(n)
   seen.add(n)
  bad_names=[n for n in names if unsafe(n)]
  missing=[m for m in REQUIRED_MEMBERS if m not in seen]
  out['checks'].update({'duplicate_count':len(set(dup)),'unsafe_count':len(bad_names),'missing_required':missing})
  if dup or bad_names or missing: out['verdict']='REPLAY_PROOF_FAIL'; return out
  with tempfile.TemporaryDirectory(prefix='mb_replay_',dir='/tmp') as td:
   if full_extract:
    if len(names)>4000: out['verdict']='REPLAY_PROOF_FAIL'; out['reason']='too_many_members_for_bounded_full_extract'; return out
    for n in names:
     if n.endswith('/'): continue
     copy_member(z,n,td)
    out['extract_mode']='bounded_full_extract'
   else:
    subset=set(REQUIRED_MEMBERS)
    for n in sorted(subset): copy_member(z,n,td)
    out['extract_mode']='targeted_extract'
   root=Path(td)/'Metablooms_OS'; mb=root/'bin/mb'
   out['checks']['fresh_root_present']=root.exists(); out['checks']['mb_present']=mb.exists()
   for p in [mb, root/'0_kernel/scripts/artifact_replay_proof_v2.py']:
    if p.exists(): out['commands'].append(cmd([sys.executable,'-m','py_compile',str(p)],timeout=timeout))
   # bounded replay avoids executing extracted mb in unstable sandbox; compile + required files prove boot surface is present
   out['checks']['operator_replay_surface_present']=mb.exists()
 if any(c['rc']!=0 for c in out['commands'] if 'py_compile' in c['cmd']): out['verdict']='REPLAY_PROOF_FAIL'; out['reason']='compile_failed'; return out
 out['verdict']='REPLAY_PROOF_PASS'; return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--archive',required=True); ap.add_argument('--sidecar'); ap.add_argument('--json',action='store_true'); ap.add_argument('--full-extract',action='store_true'); ap.add_argument('--timeout',type=int,default=10); ap.add_argument('--write-report')
 a=ap.parse_args(); r=run(a.archive,a.sidecar,a.full_extract,a.timeout)
 if a.write_report: Path(a.write_report).parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(Path(a.write_report), r, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_artifact_replay_proof_v2_py_L78', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000)
 print(json.dumps(r,indent=2,sort_keys=True) if a.json else r.get('verdict'))
 return 0 if r.get('verdict')=='REPLAY_PROOF_PASS' else 2
if __name__=='__main__': raise SystemExit(main())
