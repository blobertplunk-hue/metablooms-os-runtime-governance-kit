#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, time
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

def sha256(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
 return h.hexdigest()
def run(cmd, timeout=120):
 st=time.time()
 cp=run_compat(cmd,timeout_seconds=min(int(timeout),30),operation_type="archive_method_router_command",stage="archive_method_router_v1")
 out={'cmd':cmd,'rc':cp.returncode,'stdout':(cp.stdout or '')[-5000:],'stderr':(cp.stderr or '')[-5000:],'elapsed_sec':round(time.time()-st,3)}
 if cp.returncode==124: out['timeout']=True
 if 'METABLOOMS_BOUNDED_SUBPROCESS_RESULT=' in (cp.stderr or ''): out['bounded_wrapper']=True
 return out
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('archive'); ap.add_argument('--sidecar'); ap.add_argument('--root',default='/mnt/data/Metablooms_OS'); ap.add_argument('--mode',choices=['validate','extract'],default='validate'); ap.add_argument('--dest'); ap.add_argument('--timeout-s',type=int,default=120); ap.add_argument('--json-out')
 a=ap.parse_args(); root=Path(a.root); archive=Path(a.archive)
 out={'artifact_type':'ARCHIVE_METHOD_ROUTER_EVIDENCE_v1','created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'archive':str(archive),'mode':a.mode,'checks':[],'attempts':[],'issues':[],'warnings':[]}
 if not archive.exists(): out['issues'].append('archive_missing')
 if a.sidecar:
  side=Path(a.sidecar)
  if not side.exists(): out['issues'].append('sidecar_missing')
  else:
   expected=side.read_text().split()[0]; actual=sha256(archive); ok=expected==actual
   out['checks'].append({'name':'sha256_sidecar','passed':ok,'expected':expected,'actual':actual})
   if not ok: out['issues'].append('sha256_mismatch')
 if not out['issues']:
  uz=shutil.which('unzip')
  if uz:
   r=run([uz,'-tq',str(archive)],a.timeout_s); out['attempts'].append(r); out['checks'].append({'name':'unzip_integrity','passed':r['rc']==0})
  seven=root/'tools/7zip/7zz'
  if seven.exists() and os.access(seven,os.X_OK):
   r=run([str(seven),'t',str(archive)],a.timeout_s); out['attempts'].append(r); out['checks'].append({'name':'7zz_integrity','passed':r['rc']==0})
  else: out['warnings'].append('7zz_missing')
  if a.mode=='extract':
   if not a.dest: out['issues'].append('extract_dest_missing')
   elif not str(Path(a.dest)).startswith('/mnt/data/'): out['issues'].append('extract_dest_outside_mnt_data')
   elif seven.exists() and os.access(seven,os.X_OK):
    Path(a.dest).mkdir(parents=True,exist_ok=True); r=run([str(seven),'x','-y','-o'+a.dest,str(archive)],a.timeout_s); out['attempts'].append(r); out['checks'].append({'name':'7zz_extract','passed':r['rc']==0})
    if r['rc']!=0: out['issues'].append('7zz_extract_failed')
 out['verdict']='PASS' if not out['issues'] and any(c.get('passed') for c in out['checks'] if c['name'].endswith('integrity')) else 'FAIL'
 text=json.dumps(out,indent=2,sort_keys=True)
 if a.json_out: write_json_file(Path(a.json_out), out, operation_id='archive_method_router_json_out', allowed_roots=['/mnt/data'], create_parent=True)
 print(text); return 0 if out['verdict']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
