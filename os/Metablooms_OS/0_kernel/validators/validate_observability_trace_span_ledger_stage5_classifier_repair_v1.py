#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.util, json, time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE5_TRACE_INGESTION_CLASSIFIER_REPAIR_AND_REGRESSION_FIXTURES'
def utc(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def load(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def sha_text(txt:str): return hashlib.sha256(txt.encode('utf-8')).hexdigest()
def load_ingest(root:Path):
    p=root/'0_kernel/scripts/observability_boot_ingest_v1.py'
    spec=importlib.util.spec_from_file_location('observability_boot_ingest_v1', p)
    mod=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def ledger_records(path:Path):
    out=[]
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.strip(): out.append(json.loads(line))
    return out

def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--write-report', action='store_true')
    args=ap.parse_args(argv); root=Path(args.root).resolve(); issues=[]; checks=[]
    required=[
      '0_kernel/scripts/observability_boot_ingest_v1.py',
      '0_kernel/registry/observability/MB_TRACE_INGESTION_CLASSIFIER_POLICY_v1.json',
      'runtime/fixtures/observability/trace_ingestion_classifier_stage5/SHA256SUMS.txt',
      'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl',
      'runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json',
      'runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json',
      'runtime/traces/observability/REPAIR_ROUTER_BINDING_LATEST.json'
    ]
    for rel in required:
        p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok})
        if not ok: issues.append({'missing_or_empty':rel})
    fixture_results=[]
    if not issues:
        mod=load_ingest(root)
        fixdir=root/'runtime/fixtures/observability/trace_ingestion_classifier_stage5'
        for fp in sorted(fixdir.glob('*.json')):
            payload=load(fp); expected=payload.get('expected_trace_status'); actual=mod.infer_status(payload)
            fixture_results.append({'fixture':str(fp.relative_to(root)),'expected':expected,'actual':actual,'pass':expected==actual})
            if actual != expected: issues.append({'fixture_status_mismatch':fixture_results[-1]})
        src=(root/'0_kernel/scripts/observability_boot_ingest_v1.py').read_text(encoding='utf-8')
        forbidden='if key in s:'
        if forbidden in src: issues.append({'forbidden_substring_status_matcher_present':forbidden})
        ledger=ledger_records(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl')
        ce_bad=[]
        see_bad=[]
        for r in ledger:
            attrs=r.get('attributes') or {}
            at=attrs.get('artifact_type')
            src_art=str(r.get('source_artifact',''))
            if at=='CE_SYNTHESIS.v1' and r.get('status')!='OK': ce_bad.append({'source_artifact':src_art,'status':r.get('status')})
            if at=='SEE_PACKET.v1' and r.get('status')!='OK': see_bad.append({'source_artifact':src_art,'status':r.get('status')})
        if ce_bad: issues.append({'ce_synthesis_not_ok':ce_bad[:10]})
        if see_bad: issues.append({'see_packet_not_ok':see_bad[:10]})
        index=load(root/'runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json')
        if index.get('record_count') != len(ledger): issues.append({'index_record_count_mismatch':{'index':index.get('record_count'),'ledger':len(ledger)}})
        report=load(root/'runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json')
        classes=[c.get('failure_class') for c in report.get('clusters',[])]
        if 'derived_packet_missing_status_contract' in classes: issues.append({'stale_derived_packet_cluster_present':True})
        binding=load(root/'runtime/traces/observability/REPAIR_ROUTER_BINDING_LATEST.json')
        routes=[r.get('target_workflow') for r in binding.get('routes',[])]
        if 'TRACE_INGESTION_CLASSIFIER_REPAIR' in routes: issues.append({'stale_classifier_repair_route_present':True})
    out={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE5_CLASSIFIER_REPAIR_VALIDATION.v1','stage_id':STAGE,'created_utc':utc(),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'fixture_results':fixture_results,'issues':issues}
    if args.write_report:
        p=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE5_CLASSIFIER_REPAIR_VALIDATION_LATEST.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        txt=json.dumps(out, indent=2, sort_keys=True)+'\n'; p.write_text(txt, encoding='utf-8')
        p.with_suffix(p.suffix+'.sha256').write_text(sha_text(txt)+'  '+p.name+'\n', encoding='utf-8')
    print(json.dumps(out, indent=2, sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
