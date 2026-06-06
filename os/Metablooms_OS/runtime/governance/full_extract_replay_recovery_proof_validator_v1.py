#!/usr/bin/env python3
"""Full extract replay recovery proof validator v1.
Uses zipfile under python3 -S to avoid shell unzip timeout/deadlock. It validates every member by read replay, rejects duplicate/unsafe members, and materializes boot-critical files to prove extraction semantics without forcing host filesystem watchers across the full tree.
"""
from __future__ import annotations
import argparse, collections, hashlib, json, os, pathlib, shutil, sys, tempfile, time, zipfile
PREFIX='Metablooms_OS/'
REQUIRED=[
 '0_kernel/registry/BOOT_REQUIRED_GATES_v1.json',
 '0_kernel/registry/FULL_EXTRACT_REPLAY_RECOVERY_PROOF_CONTRACT_v1.json',
 'runtime/governance/full_extract_replay_recovery_proof_validator_v1.py',
 'runtime/governance/prompt_route_preexecution_enforcer_v1.py',
 'runtime/governance/task_start_hook_v1.py',
 'runtime/cartridges/prompt_governance_v1/CARTRIDGE_MANIFEST.json',
 'runtime/cartridges/prompt_governance_v1/validate_prompt_route_preexecution_enforcer_v1.py'
]
def sha_file(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()
def scan(names):
 counts=collections.Counter(names)
 dups=[n for n,v in counts.items() if v>1]
 unsafe=[n for n in names if n.startswith('/') or '\\' in n or '..' in pathlib.PurePosixPath(n).parts]
 return dups, unsafe
def validate(zippath, sidecar=None, target_dir=None, materialize_all=False):
 started=time.time(); zippath=pathlib.Path(zippath); sidecar=pathlib.Path(sidecar) if sidecar else pathlib.Path(str(zippath)+'.sha256')
 report={'validator':'full_extract_replay_recovery_proof_validator_v1','zip':str(zippath),'sidecar':str(sidecar),'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
 if not zippath.exists(): report.update(decision='DENY',reason='zip_missing'); return report
 if not sidecar.exists(): report.update(decision='DENY',reason='sidecar_missing'); return report
 actual=sha_file(zippath); expected=sidecar.read_text().split()[0]
 report['checksum']={'actual':actual,'expected':expected,'match':actual==expected}
 if actual!=expected: report.update(decision='DENY',reason='checksum_mismatch'); return report
 target=pathlib.Path(target_dir) if target_dir else pathlib.Path(tempfile.mkdtemp(prefix='mb_recovery_targeted_'))
 shutil.rmtree(target, ignore_errors=True); target.mkdir(parents=True, exist_ok=True)
 total=0; files=0; materialized=[]; missing=[]
 with zipfile.ZipFile(zippath) as z:
  names=z.namelist(); dups,unsafe=scan(names); bad=z.testzip()
  report['archive']={'member_count':len(names),'duplicates':len(dups),'unsafe_paths':len(unsafe),'testzip':bad}
  if dups or unsafe or bad is not None: report.update(decision='DENY',reason='archive_preflight_failed'); return report
  name_set=set(names)
  for rel in REQUIRED:
   if PREFIX+rel not in name_set: missing.append(rel)
  if missing: report['required_files']={'missing':missing}; report.update(decision='DENY',reason='missing_required_file'); return report
  base=target.resolve()
  for info in z.infolist():
   if info.filename.endswith('/'): continue
   with z.open(info) as src:
    data=src.read()
   total += len(data); files += 1
   rel=info.filename[len(PREFIX):] if info.filename.startswith(PREFIX) else info.filename
   if materialize_all or rel in REQUIRED:
    out=(target/info.filename).resolve()
    if not str(out).startswith(str(base)+os.sep): report.update(decision='DENY',reason='path_escape',path=info.filename); return report
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(data); materialized.append(info.filename)
 report['member_read_replay']={'files_read':files,'bytes_read':total}
 report['materialized_extract']={'target':str(target),'files_written':len(materialized),'mode':'all' if materialize_all else 'boot_critical_targeted'}
 report['elapsed_seconds']=round(time.time()-started,3)
 report['decision']='ALLOW'
 return report
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('zip'); ap.add_argument('--sidecar'); ap.add_argument('--target-dir'); ap.add_argument('--materialize-all', action='store_true')
 a=ap.parse_args(); r=validate(a.zip,a.sidecar,a.target_dir,a.materialize_all); print(json.dumps(r,indent=2,sort_keys=True)); sys.exit(0 if r.get('decision')=='ALLOW' else 2)
