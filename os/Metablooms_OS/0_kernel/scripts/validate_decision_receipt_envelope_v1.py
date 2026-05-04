#!/usr/bin/env python3
import json, hashlib, os, sys, re
from pathlib import Path

def fail(msg, code=2):
    print(json.dumps({'result':'fail','reason':msg}, indent=2)); sys.exit(code)
if 'site' in sys.modules:
    fail('validator must be launched with python3 -S; site is loaded')
ROOT=Path(os.environ.get('METABLOOMS_ROOT','/mnt/data/Metablooms_OS'))
REQ=['envelope_version','record_kind','record_id','stage_id','created_utc','decision_id','result','summary','source_record','input_artifacts','output_artifacts','evidence_refs','normalization_status']
KINDS={'decision_log','stage_receipt','verify_receipt','handoff','repair_receipt','other_receipt'}
SHA_RE=re.compile(r'^[0-9a-f]{64}$')

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def validate_obj(o):
    errors=[]
    for k in REQ:
        if k not in o: errors.append(f'missing required field {k}')
    if errors: return errors
    if o['envelope_version']!='decision_receipt_envelope_v1': errors.append('bad envelope_version')
    if o['record_kind'] not in KINDS: errors.append('bad record_kind')
    if not str(o.get('decision_id','')).strip(): errors.append('blank decision_id')
    if not str(o.get('result','')).strip(): errors.append('blank result')
    src=o.get('source_record') or {}
    if not SHA_RE.match(str(src.get('sha256',''))): errors.append('bad source_record.sha256')
    p=ROOT/src.get('path','') if src.get('path') else None
    if p and p.exists() and sha(p)!=src.get('sha256'): errors.append('source_record hash mismatch')
    if not isinstance(o.get('input_artifacts'), list): errors.append('input_artifacts not list')
    if not isinstance(o.get('output_artifacts'), list): errors.append('output_artifacts not list')
    if not isinstance(o.get('evidence_refs'), list): errors.append('evidence_refs not list')
    return errors

def main():
    if len(sys.argv)<2: fail('usage: validate_decision_receipt_envelope_v1.py <envelope-or-manifest.json>')
    data=json.load(open(sys.argv[1],encoding='utf-8'))
    items=[]
    if isinstance(data, dict) and data.get('manifest_type')=='DECISION_RECEIPT_CANONICALIZATION_MANIFEST':
        for e in data.get('canonical_records',[]):
            items.append(json.load(open(ROOT/e['path'],encoding='utf-8')))
    else:
        items=[data]
    all_errors=[]; seen=set()
    for i,o in enumerate(items):
        errs=validate_obj(o)
        did=o.get('decision_id')
        if did in seen: errs.append('duplicate decision_id')
        seen.add(did)
        if errs: all_errors.append({'index':i,'record_id':o.get('record_id'),'errors':errs})
    result={'result':'pass' if not all_errors else 'fail','checked':len(items),'errors':all_errors}
    print(json.dumps(result,indent=2,sort_keys=True))
    sys.exit(0 if not all_errors else 1)
if __name__=='__main__': main()
