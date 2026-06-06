#!/usr/bin/env python3
import argparse, json, hashlib, zipfile, time
from pathlib import Path

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def load_member_json(z,name): return json.loads(z.read(name).decode('utf-8'))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--zip', dest='zip_path', required=True)
    ap.add_argument('--out', required=True)
    args=ap.parse_args()
    root=Path(args.root); zp=Path(args.zip_path); out=Path(args.out)
    issues=[]; replay=[]
    receipt='Metablooms_OS/runtime/receipts/pinned_evidence/PINNED_EVIDENCE_RECEIPT_LATEST.json'
    binding='Metablooms_OS/runtime/traces/observability/PINNED_EVIDENCE_EXPORT_BINDING_LATEST.json'
    with zipfile.ZipFile(zp) as z:
        names=set(z.namelist())
        if receipt not in names: issues.append({'code':'missing_promoted_receipt','path':receipt})
        if binding not in names: issues.append({'code':'missing_export_binding','path':binding})
        rec=load_member_json(z,receipt) if receipt in names else {'pins':[]}
        bind=load_member_json(z,binding) if binding in names else {'bound_evidence_paths':[],'bound_evidence_sha256':{}}
        expected=[]
        for p in bind.get('bound_evidence_paths',[]):
            expected.append(p)
        for pin in rec.get('pins',[]):
            if pin.get('path') and pin['path'] not in expected:
                expected.append(pin['path'])
        for rel in expected:
            member='Metablooms_OS/'+rel
            item={'path':rel,'zip_member':member,'exists_in_zip':member in names}
            if member not in names:
                item['verdict']='FAIL'; issues.append({'code':'missing_bound_artifact','path':rel}); replay.append(item); continue
            actual=sha_bytes(z.read(member)); item['zip_member_sha256']=actual
            declared=bind.get('bound_evidence_sha256',{}).get(rel)
            pin=next((p for p in rec.get('pins',[]) if p.get('path')==rel),{})
            item['binding_declared_sha256']=declared
            item['receipt_actual_sha256']=pin.get('actual_sha256')
            mutable=rel.endswith('TRACE_SPAN_LEDGER_LATEST.jsonl') or rel.endswith('TRACE_SPAN_LEDGER_INDEX_LATEST.json') or rel.endswith('SEARCHABLE_EVIDENCE_INDEX_LATEST.json')
            if declared and declared==actual:
                item['verdict']='PASS_EXACT'
            elif mutable:
                item['verdict']='PASS_REPLAYED_CURRENT_MUTABLE_GENERATED_ARTIFACT'
                item['note']='Generated evidence changed after prior binding; actual export member digest is recorded for audit replay.'
            else:
                item['verdict']='FAIL'
                issues.append({'code':'sha_mismatch_bound_artifact','path':rel,'declared':declared,'actual':actual})
            replay.append(item)
    report={'artifact_type':'MB_PROMOTED_EVIDENCE_RECOVERY_REPLAY.v1','stage_id':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE15_PROMOTED_EVIDENCE_RECOVERY_REPLAY_AND_AUDIT_QUERY_PACKS','created_utc':time.strftime('%Y%m%dT%H%M%SZ',time.gmtime()),'export_zip':str(zp),'export_zip_sha256':hashlib.sha256(zp.read_bytes()).hexdigest(),'promoted_receipt_member':receipt,'export_binding_member':binding,'replayed_artifacts':replay,'issues':issues,'verdict':'PASS' if not issues else 'FAIL'}
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'verdict':report['verdict'],'issues':len(issues),'replayed_artifacts':len(replay)},sort_keys=True))
    raise SystemExit(0 if not issues else 1)
if __name__=='__main__': main()
