#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, time
from pathlib import Path
from typing import Any
SCHEMA_VERSION="MB_CHECKPOINT_RECORD_v1"
def utc_now(): return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
def stable_json(obj:Any)->str: return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)
def safe_segment(value:str)->str:
    out=[]
    for ch in value:
        out.append(ch if (ch.isalnum() or ch in ('-','_','.')) else '_')
    return ''.join(out).strip('._') or 'thread'
def default_thread_id(stage_name:str)->str: return 'stage::'+safe_segment(stage_name)
def checkpoint_id(payload:dict)->str: return hashlib.sha256(stable_json(payload).encode()).hexdigest()[:24]
def atomic_write_json(path:Path,payload:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_name(path.name+'.tmp')
    _mb_write_json_file(tmp, payload, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_checkpoint_manager_v1_py_L18', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=True, max_bytes=20000000); os.replace(tmp,path)
def checkpoint_dir(root:Path,thread_id:str)->Path: return root/'runtime'/'checkpoints'/safe_segment(thread_id)
def create_checkpoint(root:Path,stage_name:str,state:dict|None=None,*,thread_id:str|None=None,parent_checkpoint_id:str|None=None,interrupt_payload:dict|None=None,status:str|None=None)->dict:
    now=utc_now(); tid=thread_id or default_thread_id(stage_name)
    rec={'schema_version':SCHEMA_VERSION,'stage_name':stage_name,'thread_id':tid,'checkpoint_ns':'','parent_checkpoint_id':parent_checkpoint_id,'created_utc':now,'status':status or ('INTERRUPTED' if interrupt_payload is not None else 'CHECKPOINTED'),'state':state or {},'interrupt':interrupt_payload,'resume':None,'next':([] if interrupt_payload is None else ['AWAIT_HUMAN_RESUME']),'metadata':{'source':'metablooms_checkpoint_manager_v1','step':0 if not parent_checkpoint_id else 1,'writes':{'checkpoint':True,'interrupt':interrupt_payload is not None}}}
    cid=checkpoint_id(rec); rec['checkpoint_id']=cid; cdir=checkpoint_dir(root,tid)
    atomic_write_json(cdir/f'{cid}.json',rec); atomic_write_json(cdir/'THREAD_LATEST.json',rec)
    idx_path=root/'runtime'/'checkpoints'/'CHECKPOINT_THREAD_INDEX_LATEST.json'
    idx={'schema_version':'MB_CHECKPOINT_THREAD_INDEX_v1','threads':{},'updated_utc':now}
    if idx_path.exists():
        try: idx=json.loads(idx_path.read_text(encoding='utf-8'))
        except Exception: pass
    idx.setdefault('threads',{})[tid]={'stage_name':stage_name,'latest_checkpoint_id':cid,'status':rec['status'],'updated_utc':now,'path':str((cdir/'THREAD_LATEST.json').relative_to(root))}; idx['updated_utc']=now
    atomic_write_json(idx_path,idx); return rec
def latest_checkpoint(root:Path,thread_id:str)->dict:
    p=checkpoint_dir(root,thread_id)/'THREAD_LATEST.json'
    if not p.exists(): raise FileNotFoundError(f'CHECKPOINT_THREAD_NOT_FOUND:{thread_id}')
    return json.loads(p.read_text(encoding='utf-8'))
def resume_checkpoint(root:Path,thread_id:str,resume_payload:dict|None=None)->dict:
    latest=latest_checkpoint(root,thread_id)
    if latest.get('status')!='INTERRUPTED': raise RuntimeError('CHECKPOINT_NOT_INTERRUPTED')
    state=dict(latest.get('state') or {}); state['resume_payload']=resume_payload or {}
    rec=create_checkpoint(root,latest['stage_name'],state,thread_id=thread_id,parent_checkpoint_id=latest.get('checkpoint_id'),status='RESUMED')
    rec['resume']=resume_payload or {}
    atomic_write_json(checkpoint_dir(root,thread_id)/'THREAD_LATEST.json',rec)
    return rec
def list_threads(root:Path)->dict:
    p=root/'runtime'/'checkpoints'/'CHECKPOINT_THREAD_INDEX_LATEST.json'
    if not p.exists(): return {'schema_version':'MB_CHECKPOINT_THREAD_INDEX_v1','threads':{},'updated_utc':utc_now()}
    return json.loads(p.read_text(encoding='utf-8'))
def find_root()->Path:
    env=os.environ.get('METABLOOMS_ROOT')
    if env: return Path(env)
    here=Path(__file__).resolve()
    for p in [here.parent,*here.parents]:
        if (p/'boot_manifest_v1.json').exists() and (p/'0_kernel').exists(): return p
    cwd=Path.cwd()
    if (cwd/'boot_manifest_v1.json').exists(): return cwd
    raise SystemExit('METABLOOMS_ROOT_NOT_FOUND')
def main(argv=None)->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--stage'); ap.add_argument('--thread-id'); ap.add_argument('--state-json',default='{}'); ap.add_argument('--interrupt-json'); ap.add_argument('--resume',action='store_true'); ap.add_argument('--resume-json',default='{}'); ap.add_argument('--list',action='store_true')
    ns=ap.parse_args(argv); root=find_root()
    if ns.list: print(json.dumps({'verdict':'CHECKPOINT_THREADS',**list_threads(root)},indent=2,sort_keys=True)); return 0
    if ns.resume:
        if not ns.thread_id: raise SystemExit('--thread-id required for --resume')
        print(json.dumps({'verdict':'CHECKPOINT_RESUMED','checkpoint':resume_checkpoint(root,ns.thread_id,json.loads(ns.resume_json))},indent=2,sort_keys=True)); return 0
    if not ns.stage: raise SystemExit('--stage required unless --list or --resume')
    interrupt=json.loads(ns.interrupt_json) if ns.interrupt_json else None
    print(json.dumps({'verdict':'CHECKPOINT_WRITTEN','checkpoint':create_checkpoint(root,ns.stage,json.loads(ns.state_json),thread_id=ns.thread_id,interrupt_payload=interrupt)},indent=2,sort_keys=True)); return 0
if __name__=='__main__': raise SystemExit(main())
