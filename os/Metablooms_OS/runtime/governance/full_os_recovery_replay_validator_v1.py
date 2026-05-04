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
import hashlib, json, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path

def sha256_path(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def safe_rel(n:str)->bool:
    parts=Path(n).parts
    return not (n.startswith('/') or '..' in parts or '\\' in n)

def run(cmd, cwd=None, timeout=30):
    cp=bounded_subprocess_run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    return {'cmd':cmd,'returncode':cp.returncode,'stdout':cp.stdout[-4000:], 'stderr':cp.stderr[-4000:]}

def validate(zip_path, sidecar_path=None, required_paths=None, extract_dir=None):
    zip_path=Path(zip_path)
    sidecar_path=Path(sidecar_path) if sidecar_path else Path(str(zip_path)+'.sha256')
    required_paths=required_paths or []
    report={'decision':'DENY','zip':str(zip_path),'sidecar':str(sidecar_path),'checks':{},'validator_runs':{},'errors':[]}
    if not zip_path.exists(): report['errors'].append('zip_missing'); return report
    digest=sha256_path(zip_path)
    report['checks']['zip_sha256']=digest
    if sidecar_path.exists():
        expected=sidecar_path.read_text().strip().split()[0]
        report['checks']['sidecar_expected']=expected
        report['checks']['sidecar_matches']=(expected==digest)
        if expected!=digest: report['errors'].append('sidecar_mismatch')
    else:
        report['errors'].append('sidecar_missing')
    t=time.time(); names=[]; unsafe=[]
    with zipfile.ZipFile(zip_path) as z:
        bad=z.testzip(); infos=z.infolist(); names=[i.filename for i in infos]
        dup=len(names)-len(set(names))
        unsafe=[n for n in names if not safe_rel(n)]
        report['checks'].update({'zip_integrity_bad_member':bad,'entry_count':len(names),'duplicate_member_count':dup,'unsafe_member_count':len(unsafe),'unsafe_members':unsafe[:20]})
        if bad: report['errors'].append('zip_integrity_bad_member:'+str(bad))
        if dup: report['errors'].append('duplicate_members')
        if unsafe: report['errors'].append('unsafe_members')
        tmp = Path(extract_dir) if extract_dir else Path(tempfile.mkdtemp(prefix='metablooms_replay_'))
        if tmp.exists(): shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        for i in infos: z.extract(i, tmp)
    root=tmp/'Metablooms_OS'
    report['checks']['fresh_extract_seconds']=round(time.time()-t,3)
    report['checks']['root_exists']=root.exists()
    if not root.exists(): report['errors'].append('root_missing_after_extract')
    missing=[]
    for rel in required_paths:
        if not (root/rel).exists(): missing.append(rel)
    report['checks']['required_paths_missing']=missing
    if missing: report['errors'].append('required_paths_missing')
    validators=[
      ('boot_loader','runtime/governance/boot_critical_governance_loader_v1.py'),
      ('prompt_cartridge','runtime/cartridges/prompt_governance_v1/validate_prompt_governance_cartridge_v1.py'),
      ('profile_smoke','runtime/cartridges/prompt_governance_v1/validate_prompt_engine_profile_smoke_v1.py'),
      ('banned_patterns','runtime/governance/banned_pattern_enforcer_v1.py'),
      ('scatter','runtime/governance/governance_scatter_prevention_v1.py'),
      ('fresh_chat','runtime/governance/fresh_chat_boot_rehearsal_v1.py'),
      ('new_chat_contract','runtime/governance/new_chat_start_contract_validator_v1.py'),
    ]
    for name, rel in validators:
        p=root/rel
        if p.exists():
            res=run(['python3','-S',str(p),str(root)], timeout=45)
            report['validator_runs'][name]=res
            if res['returncode']!=0: report['errors'].append('validator_failed:'+name)
        else:
            report['validator_runs'][name]={'missing':rel}
            report['errors'].append('validator_missing:'+name)
    report['decision']='ALLOW' if not report['errors'] else 'DENY'
    return report

if __name__=='__main__':
    zp=sys.argv[1]
    sp=sys.argv[2] if len(sys.argv)>2 else None
    req=[
      '0_kernel/registry/BOOT_REQUIRED_GATES_v1.json',
      'runtime/governance/full_os_recovery_replay_validator_v1.py',
      'runtime/governance/safe_walk_v1.py',
      'runtime/governance/banned_pattern_enforcer_v1.py',
      'runtime/cartridges/prompt_governance_v1/CARTRIDGE_MANIFEST.json',
      'runtime/cartridges/prompt_governance_v1/PROMPT_ENGINE_RELIABILITY_REPORT_v1.json',
      '0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md'
    ]
    r=validate(zp,sp,req)
    print(json.dumps(r, indent=2, sort_keys=True))
    raise SystemExit(0 if r['decision']=='ALLOW' else 1)
