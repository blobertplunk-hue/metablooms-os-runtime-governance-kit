#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path

def sha256(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
 return h.hexdigest()
def run(cmd, timeout=120):
 st=time.time()
 try:
  cp=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
  return {'cmd':cmd,'rc':cp.returncode,'stdout':cp.stdout[-5000:],'stderr':cp.stderr[-5000:],'elapsed_sec':round(time.time()-st,3)}
 except subprocess.TimeoutExpired as e:
  return {'cmd':cmd,'rc':124,'stdout':(e.stdout or '')[-5000:] if isinstance(e.stdout,str) else '', 'stderr':(e.stderr or '')[-5000:] if isinstance(e.stderr,str) else '', 'elapsed_sec':round(time.time()-st,3),'timeout':True}
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
 if a.json_out: Path(a.json_out).write_text(text+'\n',encoding='utf-8')
 print(text); return 0 if out['verdict']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
