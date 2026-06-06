#!/usr/bin/env python3

# MetaBlooms Stage4 atomic JSON writer enforcement shim.
from pathlib import Path as _MBAJWPath
import sys as _MBAJWSys
_MBAJW_SELF = _MBAJWPath(__file__).resolve()
for _MBAJW_PARENT in [_MBAJW_SELF] + list(_MBAJW_SELF.parents):
    _MBAJW_IO = _MBAJW_PARENT / "0_kernel" / "lib" / "io"
    if (_MBAJW_IO / "atomic_json_compat_v1.py").exists():
        if str(_MBAJW_IO) not in _MBAJWSys.path:
            _MBAJWSys.path.insert(0, str(_MBAJW_IO))
        break
from atomic_json_compat_v1 import write_json_file as _mb_write_json_file
import json, hashlib, os, sys, uuid
from pathlib import Path
from datetime import datetime, timezone
if 'site' in sys.modules:
    print(json.dumps({'result':'fail','reason':'must run with python3 -S'})); sys.exit(2)
ROOT=Path(os.environ.get('METABLOOMS_ROOT','/mnt/data/Metablooms_OS'))
def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()
def rel(p):
    try: return str(Path(p).relative_to(ROOT))
    except Exception: return str(p)
def load(p): return json.load(open(p,encoding='utf-8'))
def write(p,o):
    p.parent.mkdir(parents=True, exist_ok=True)
    _mb_write_json_file(p, o, operation_id='STAGE4_STANDARDIZE_DECISION_RECEIPT_WRITE', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=False, max_bytes=20000000)
def extract_stage(obj, p):
    return obj.get('stage') or obj.get('stage_id') or Path(p).name.split('_')[0]
def extract_result(obj):
    for k in ('result','status','verdict','decision'):
        v=obj.get(k)
        if isinstance(v,str) and v: return v.lower()
    return 'wrapped'
def extract_created(obj):
    return obj.get('created_utc') or obj.get('timestamp_utc') or datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def envelope(src_path, kind, out_dir):
    obj=load(src_path); s=sha(src_path); st=src_path.stat(); stage=extract_stage(obj,src_path)
    did=obj.get('decision_id') or obj.get('decision_log_id') or f'{stage}-{s[:16]}'
    summary=obj.get('decision') or obj.get('decision_context') or obj.get('summary') or f'Canonical wrapper for {src_path.name}'
    reasons=[]
    for k in ('reasons','rationale','drivers','decision_basis'):
        if isinstance(obj.get(k), list): reasons += [str(x) for x in obj[k]]
    ev=[]
    for k in ('evidence','external_evidence','external_basis','external_pattern_basis'):
        if isinstance(obj.get(k), list):
            for x in obj[k]: ev.append(x if isinstance(x,dict) else {'claim':str(x)})
    outarts=[]
    for k in ('created_artifacts','chosen_outputs','outputs'):
        if isinstance(obj.get(k), list):
            for x in obj[k]: outarts.append({'path': str(x) if not isinstance(x,dict) else x.get('path', str(x))})
    env={
      'envelope_version':'decision_receipt_envelope_v1',
      'record_kind':kind,
      'record_id':src_path.stem,
      'stage_id':stage,
      'gate_id':obj.get('gate_id'),
      'created_utc':extract_created(obj),
      'decision_id':str(did),
      'trace_id':hashlib.sha256((str(did)+s).encode()).hexdigest()[:32],
      'span_id':hashlib.sha256((s+str(did)).encode()).hexdigest()[:16],
      'result':extract_result(obj),
      'summary':str(summary)[:1000],
      'reasons':reasons,
      'source_record':{'path':rel(src_path),'sha256':s,'size_bytes':st.st_size},
      'input_artifacts':[],
      'output_artifacts':outarts,
      'evidence_refs':ev,
      'policy_basis':[{'source':'OPA decision logs','claim':'canonical envelope includes decision_id/input/result/timestamp-style fields for audit'}, {'source':'CloudEvents','claim':'record identity uses stable event-style id/source/type concepts'}],
      'normalization_status':'wrapped_legacy',
      'raw_excerpt':json.dumps(obj,sort_keys=True)[:1500],
      'masked':[], 'erased':[]
    }
    out=out_dir/(src_path.stem+'.canonical.json')
    write(out,env)
    return out

def main():
    ts=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    base=ROOT/'runtime/governance'
    logs=sorted((base/'decision_logs').glob('DECISION_LOG_R*.json'))
    recs=sorted((ROOT/'receipts/refactor_program').glob('R[1-9]*.json'))
    canon=[]
    for p in logs:
        canon.append(envelope(p,'decision_log',base/'decision_logs/canonical'))
    for p in recs:
        name=p.name
        kind='stage_receipt'
        if 'VERIFY' in name: kind='verify_receipt'
        elif 'HANDOFF' in name: kind='handoff'
        elif 'REPAIR' in name: kind='repair_receipt'
        canon.append(envelope(p,kind,base/'receipts/canonical'))
    manifest={'manifest_type':'DECISION_RECEIPT_CANONICALIZATION_MANIFEST','created_utc':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'canonical_records':[{'path':rel(p),'sha256':sha(p)} for p in canon], 'source_counts':{'decision_logs':len(logs),'refactor_receipts':len(recs)}}
    out=ROOT/'runtime/governance/receipts/canonical/DECISION_RECEIPT_CANONICALIZATION_MANIFEST_v1.json'
    write(out,manifest)
    print(json.dumps({'result':'pass','manifest':rel(out),'canonical_records':len(canon)},indent=2))
if __name__=='__main__': main()
