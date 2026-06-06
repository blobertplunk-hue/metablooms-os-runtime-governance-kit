#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE4_FAILURE_CLUSTERING_AND_REPAIR_ROUTER_BINDING'
def utc(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--write-report', action='store_true')
    args=ap.parse_args(argv); root=Path(args.root).resolve(); issues=[]; checks=[]
    required=['0_kernel/registry/observability/MB_FAILURE_CLUSTER_SCHEMA_v1.json','0_kernel/registry/observability/MB_REPAIR_ROUTER_BINDING_SCHEMA_v1.json','0_kernel/registry/observability/MB_OBSERVABILITY_FAILURE_ROUTER_POLICY_v1.json','0_kernel/scripts/observability_failure_cluster_router_v1.py','runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json','runtime/traces/observability/REPAIR_ROUTER_BINDING_LATEST.json','runtime/state/operator_surface/OPERATOR_FAILURE_ROUTER_SUMMARY_LATEST.json','OPEN_OPERATOR_VISUAL_TRACKER.html']
    for rel in required:
        p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok})
        if not ok: issues.append({'missing_or_empty':rel})
    if not issues:
        report=load(root/'runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json'); binding=load(root/'runtime/traces/observability/REPAIR_ROUTER_BINDING_LATEST.json'); summary=load(root/'runtime/state/operator_surface/OPERATOR_FAILURE_ROUTER_SUMMARY_LATEST.json'); html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
        if report.get('artifact_type')!='MB_FAILURE_CLUSTER_REPORT.v1': issues.append({'bad_artifact_type':'failure_report'})
        if binding.get('artifact_type')!='MB_REPAIR_ROUTER_BINDING.v1': issues.append({'bad_artifact_type':'router_binding'})
        clusters=report.get('clusters') or []; routes=binding.get('routes') or []
        if report.get('summary',{}).get('cluster_count') != len(clusters): issues.append({'cluster_count_mismatch':True})
        if len(routes) != len(clusters): issues.append({'route_cluster_count_mismatch':{'routes':len(routes),'clusters':len(clusters)}})
        if not all(c.get('evidence_records') for c in clusters): issues.append({'cluster_missing_evidence':True})
        stage5_policy_exists=(root/'0_kernel/registry/observability/MB_TRACE_INGESTION_CLASSIFIER_POLICY_v1.json').is_file()
        stage5_validation_pass=False
        stage5_report=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE5_CLASSIFIER_REPAIR_VALIDATION_LATEST.json'
        if stage5_report.is_file():
            try:
                stage5_validation_pass=(load(stage5_report).get('verdict')=='PASS')
            except Exception:
                stage5_validation_pass=False
        if not any(c.get('failure_class')=='derived_packet_missing_status_contract' for c in clusters) and not (stage5_policy_exists and stage5_validation_pass):
            issues.append({'expected_ingestion_classifier_cluster_missing_or_stage5_repair_not_validated':True})
        if 'data-section="failure_cluster_repair_router"' not in html: issues.append({'tracker_missing_failure_router_section':True})
        for phrase in ['Failure clusters → repair routes','Router actions','FAILURE_CLUSTER_REPORT_LATEST.json']:
            if phrase not in html: issues.append({'tracker_missing_phrase':phrase})
        if summary.get('summary',{}).get('cluster_count') != len(clusters): issues.append({'summary_cluster_count_mismatch':True})
    out={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE4_FAILURE_ROUTER_VALIDATION.v1','stage_id':STAGE,'created_utc':utc(),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'issues':issues}
    if args.write_report:
        p=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE4_FAILURE_ROUTER_VALIDATION_LATEST.json'; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(out, indent=2, sort_keys=True)+'\n', encoding='utf-8'); p.with_suffix(p.suffix+'.sha256').write_text(__import__('hashlib').sha256((json.dumps(out, indent=2, sort_keys=True)+'\n').encode()).hexdigest()+'  '+p.name+'\n', encoding='utf-8')
    print(json.dumps(out, indent=2, sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
