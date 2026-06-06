#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, os, re, sys
from pathlib import Path
from datetime import datetime, timezone

SCHEMA='MetaBloomsDurableCheckpointRecord_v1'
VALID_STATUS={'CHECKPOINTED','INTERRUPTED','RESUMED','COMPLETED','FAILED_CLOSED'}
SAFE_RE=re.compile(r'^[A-Za-z0-9_.:-]{1,120}$')

def utc(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def safe_thread(t:str)->str:
    if not isinstance(t,str) or not SAFE_RE.match(t):
        raise ValueError('unsafe_thread_id')
    return t.replace(':','__')
def stable_hash(obj):
    data=json.dumps(obj, sort_keys=True, separators=(',',':')).encode('utf-8')
    return hashlib.sha256(data).hexdigest()
def atomic_json(path:Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    os.replace(tmp,path)
    h=hashlib.sha256(path.read_bytes()).hexdigest()
    path.with_name(path.name+'.sha256').write_text(f'{h}  {path.name}\n', encoding='utf-8')
    return h
def load_json(path:Path): return json.loads(path.read_text(encoding='utf-8'))
def ckpt_dir(root:Path, thread_id:str)->Path: return root/'runtime'/'checkpoints'/safe_thread(thread_id)
def build_record(stage_id, thread_id, checkpoint_id, parent_checkpoint_id, status, state, interrupt, resume, next_value, metadata):
    if status not in VALID_STATUS: raise ValueError('invalid_status')
    rec={'schema':SCHEMA,'stage_id':stage_id,'thread_id':thread_id,'checkpoint_id':checkpoint_id,'parent_checkpoint_id':parent_checkpoint_id,'status':status,'state':state or {},'interrupt':interrupt,'resume':resume,'next':next_value,'metadata':metadata or {},'created_at_utc':utc()}
    rec['record_sha256']=stable_hash(rec)
    return rec
def validate_record(rec):
    required=['schema','stage_id','thread_id','checkpoint_id','parent_checkpoint_id','status','state','interrupt','resume','next','metadata','created_at_utc','record_sha256']
    missing=[k for k in required if k not in rec]
    errors=[]
    if missing: errors.append('missing:'+','.join(missing))
    if rec.get('schema')!=SCHEMA: errors.append('invalid_schema')
    if rec.get('status') not in VALID_STATUS: errors.append('invalid_status')
    if not isinstance(rec.get('state'),dict): errors.append('state_not_object')
    if rec.get('resume') is not None and not isinstance(rec.get('resume'),dict): errors.append('resume_not_object')
    if rec.get('interrupt') is not None and not isinstance(rec.get('interrupt'),dict): errors.append('interrupt_not_object')
    copy=dict(rec); got=copy.pop('record_sha256',None)
    if got!=stable_hash(copy): errors.append('record_sha256_mismatch')
    try: safe_thread(rec.get('thread_id'))
    except Exception: errors.append('unsafe_thread_id')
    return errors
def write_checkpoint(args):
    root=Path(args.root); state=json.loads(args.state_json); interrupt=json.loads(args.interrupt_json) if args.interrupt_json else None
    resume=json.loads(args.resume_json) if args.resume_json else None; metadata=json.loads(args.metadata_json) if args.metadata_json else {}
    rec=build_record(args.stage_id,args.thread_id,args.checkpoint_id,args.parent_checkpoint_id,args.status,state,interrupt,resume,args.next,metadata)
    d=ckpt_dir(root,args.thread_id); path=d/(args.checkpoint_id+'.json')
    h=atomic_json(path,rec)
    atomic_json(d/'THREAD_LATEST.json', {'schema':'MetaBloomsCheckpointThreadLatest_v1','thread_id':args.thread_id,'checkpoint_id':args.checkpoint_id,'path':str(path),'record_sha256':rec['record_sha256'],'file_sha256':h,'updated_at_utc':utc()})
    index=root/'runtime'/'checkpoints'/'CHECKPOINT_THREAD_INDEX_LATEST.json'
    idx={'schema':'MetaBloomsCheckpointThreadIndex_v1','threads':{},'updated_at_utc':utc()}
    if index.exists():
        try: idx=load_json(index)
        except Exception: pass
    idx.setdefault('threads',{})[args.thread_id]={'latest_checkpoint_id':args.checkpoint_id,'latest_path':str(path),'status':args.status,'updated_at_utc':utc()}
    atomic_json(index,idx)
    return {'decision':'ALLOW','action':'write_checkpoint','path':str(path),'record_sha256':rec['record_sha256'],'file_sha256':h}
def resume_checkpoint(args):
    root=Path(args.root); packet=load_json(Path(args.resume_packet))
    thread_id=packet.get('thread_id'); checkpoint_id=packet.get('checkpoint_id'); payload=packet.get('resume_payload')
    if not isinstance(payload,dict): return {'decision':'DENY','reason':'resume_payload_not_object'}
    path=ckpt_dir(root,thread_id)/(checkpoint_id+'.json')
    if not path.exists(): return {'decision':'DENY','reason':'checkpoint_not_found','path':str(path)}
    parent=load_json(path); errors=validate_record(parent)
    if errors: return {'decision':'DENY','reason':'parent_checkpoint_invalid','errors':errors}
    if parent.get('status')!='INTERRUPTED': return {'decision':'DENY','reason':'checkpoint_not_interrupted','status':parent.get('status')}
    if parent.get('thread_id')!=thread_id: return {'decision':'DENY','reason':'thread_id_mismatch'}
    child_id=packet.get('new_checkpoint_id') or (checkpoint_id+'__RESUMED')
    rec=build_record(parent['stage_id'],thread_id,child_id,checkpoint_id,'RESUMED',parent.get('state',{}),parent.get('interrupt'),payload,packet.get('next','continue'),{'resumed_from':checkpoint_id,'decision':packet.get('decision','approve'),'parent_record_sha256':parent.get('record_sha256')})
    d=ckpt_dir(root,thread_id); child_path=d/(child_id+'.json'); h=atomic_json(child_path,rec)
    atomic_json(d/'THREAD_LATEST.json', {'schema':'MetaBloomsCheckpointThreadLatest_v1','thread_id':thread_id,'checkpoint_id':child_id,'path':str(child_path),'record_sha256':rec['record_sha256'],'file_sha256':h,'updated_at_utc':utc()})
    index=root/'runtime'/'checkpoints'/'CHECKPOINT_THREAD_INDEX_LATEST.json'
    idx=load_json(index) if index.exists() else {'schema':'MetaBloomsCheckpointThreadIndex_v1','threads':{}}
    idx.setdefault('threads',{})[thread_id]={'latest_checkpoint_id':child_id,'latest_path':str(child_path),'status':'RESUMED','updated_at_utc':utc()}
    idx['updated_at_utc']=utc(); atomic_json(index,idx)
    return {'decision':'ALLOW','action':'resume_checkpoint','parent_path':str(path),'child_path':str(child_path),'child_record_sha256':rec['record_sha256'],'child_file_sha256':h}
def validate_cmd(args):
    rec=load_json(Path(args.record)); errors=validate_record(rec)
    return {'decision':'ALLOW' if not errors else 'DENY','errors':errors,'record':args.record}
def main(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd', required=True)
    w=sub.add_parser('write'); w.add_argument('--root',required=True); w.add_argument('--stage-id',required=True); w.add_argument('--thread-id',required=True); w.add_argument('--checkpoint-id',required=True); w.add_argument('--parent-checkpoint-id'); w.add_argument('--status',required=True); w.add_argument('--state-json',default='{}'); w.add_argument('--interrupt-json'); w.add_argument('--resume-json'); w.add_argument('--next'); w.add_argument('--metadata-json',default='{}')
    r=sub.add_parser('resume'); r.add_argument('--root',required=True); r.add_argument('--resume-packet',required=True)
    v=sub.add_parser('validate'); v.add_argument('record')
    args=ap.parse_args(argv)
    try:
        out=write_checkpoint(args) if args.cmd=='write' else resume_checkpoint(args) if args.cmd=='resume' else validate_cmd(args)
    except Exception as e:
        out={'decision':'DENY','reason':type(e).__name__,'detail':str(e)}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out.get('decision')=='ALLOW' else 20
if __name__=='__main__': raise SystemExit(main())
