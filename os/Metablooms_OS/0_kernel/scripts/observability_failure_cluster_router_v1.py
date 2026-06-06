#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, html, json, os, time
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE4_FAILURE_CLUSTERING_AND_REPAIR_ROUTER_BINDING'
def utc(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def sha_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
    return h.hexdigest()
def write_text(p:Path, txt:str):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp=p.with_name(p.name+f'.tmp.{os.getpid()}')
    tmp.write_text(txt, encoding='utf-8')
    os.replace(tmp,p)
    p.with_suffix(p.suffix+'.sha256').write_text(hashlib.sha256(txt.encode()).hexdigest()+'  '+p.name+'\n', encoding='utf-8')
def write_json(p:Path, obj): write_text(p, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)+'\n')
def ledger_records(p:Path):
    out=[]
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.strip(): out.append(json.loads(line))
    return out
def failure_class(r):
    src=str(r.get('source_artifact','')); st=str(r.get('stage_id','')); attrs=r.get('attributes') or {}
    if 'new_chat_start_contract_validator' in src or 'NEW_CHAT_START_CONTRACT' in json.dumps(attrs): return 'authority_pointer_contract_mismatch'
    if 'STAGE3_AUTHORITY_POINTER_CONTRACT_RECONCILIATION' in src or 'STAGE3_AUTHORITY_POINTER_CONTRACT_RECONCILIATION' in st: return 'cli_invocation_or_amended_receipt_superseded'
    if src.endswith('/CE_SYNTHESIS.json') and attrs.get('artifact_type')=='CE_SYNTHESIS.v1': return 'derived_packet_missing_status_contract'
    return 'unknown_non_ok_trace_record'
def status_for(cls, root):
    if cls=='authority_pointer_contract_mismatch': return 'RESOLVED_REFERENCE' if (root/'runtime/receipts/authority_reconciliation').exists() else 'ACTIVE'
    if cls=='cli_invocation_or_amended_receipt_superseded': return 'SUPPRESSED_BY_LATER_PASS'
    if cls=='derived_packet_missing_status_contract': return 'MONITOR'
    return 'ACTIVE'
def severity(cls, status):
    if status=='ACTIVE': return 'high'
    if cls=='derived_packet_missing_status_contract': return 'medium'
    return 'low'
def route(cls):
    mapping={
      'authority_pointer_contract_mismatch':('route_authority_reconciliation_recheck','AUTHORITY_RECONCILIATION_RECHECK','Verify current authority pointer copies, contract phrases, and new-chat validator before boot-critical execution.'),
      'cli_invocation_or_amended_receipt_superseded':('route_method_reliability_cli_shape','METHOD_RELIABILITY_LEDGER','Preserve amended pass; store wrong CLI invocation as reliability lesson and avoid blocking current execution.'),
      'derived_packet_missing_status_contract':('route_trace_ingestion_classifier_repair','TRACE_INGESTION_CLASSIFIER_REPAIR','Update future trace ingestion to classify CE/SEE synthesis packets as evidence unless explicit failure fields exist.'),
      'unknown_non_ok_trace_record':('route_manual_governance_review','MANUAL_GOVERNANCE_REVIEW','Hold if active; attach source artifact to a bounded review stage.')
    }
    return mapping.get(cls, mapping['unknown_non_ok_trace_record'])
def build(root:Path):
    obs=root/'runtime/traces/observability'; state=root/'runtime/state/operator_surface'
    ledger=obs/'TRACE_SPAN_LEDGER_LATEST.jsonl'; index=obs/'TRACE_SPAN_LEDGER_INDEX_LATEST.json'; graph=obs/'CAUSAL_STAGE_GRAPH_LATEST.json'
    records=ledger_records(ledger)
    non_ok=[r for r in records if str(r.get('status','')).upper() not in ('OK','PASS','ALLOW','')]
    buckets={}
    for r in non_ok: buckets.setdefault(failure_class(r),[]).append(r)
    clusters=[]; routes=[]
    for i,(cls,rs) in enumerate(sorted(buckets.items()),1):
        rid,target,action=route(cls); stat=status_for(cls, root)
        evid=[{k:r.get(k) for k in ['timestamp_utc','event_name','event_kind','status','stage_id','source_artifact','span_id']} for r in rs]
        clusters.append({'cluster_id':f'failure_cluster_{i:03d}','failure_class':cls,'status':stat,'severity':severity(cls,stat),'record_count':len(rs),'route_id':rid,'first_seen_utc':min(str(r.get('timestamp_utc','')) for r in rs),'last_seen_utc':max(str(r.get('timestamp_utc','')) for r in rs),'evidence_records':evid})
        routes.append({'route_id':rid,'failure_class':cls,'action':action,'target_workflow':target,'status':'ROUTED' if stat=='ACTIVE' else stat,'evidence_binding':[e.get('source_artifact') for e in evid if e.get('source_artifact')], 'cluster_record_count':len(rs)})
    report={'artifact_type':'MB_FAILURE_CLUSTER_REPORT.v1','stage_id':STAGE,'created_utc':utc(),'source_inputs':{'ledger':str(ledger.relative_to(root)),'ledger_sha256':sha_file(ledger),'index':str(index.relative_to(root)),'index_sha256':sha_file(index),'causal_graph':str(graph.relative_to(root)),'causal_graph_sha256':sha_file(graph)},'summary':{'record_count':len(records),'non_ok_record_count':len(non_ok),'cluster_count':len(clusters),'active_cluster_count':sum(1 for c in clusters if c['status']=='ACTIVE'),'monitor_cluster_count':sum(1 for c in clusters if c['status']=='MONITOR'),'resolved_or_suppressed_cluster_count':sum(1 for c in clusters if c['status'] in ('RESOLVED_REFERENCE','SUPPRESSED_BY_LATER_PASS'))},'clusters':clusters}
    binding={'artifact_type':'MB_REPAIR_ROUTER_BINDING.v1','stage_id':STAGE,'created_utc':utc(),'router_policy':{'policy_artifact':'0_kernel/registry/observability/MB_OBSERVABILITY_FAILURE_ROUTER_POLICY_v1.json','policy_sha256':sha_file(root/'0_kernel/registry/observability/MB_OBSERVABILITY_FAILURE_ROUTER_POLICY_v1.json')},'routes':routes}
    summary={'artifact_type':'MB_OPERATOR_FAILURE_ROUTER_SUMMARY.v1','stage_id':STAGE,'created_utc':utc(),'summary':report['summary'],'top_clusters':clusters[:6],'routes':routes[:6]}
    write_json(obs/'FAILURE_CLUSTER_REPORT_LATEST.json', report)
    write_json(obs/'REPAIR_ROUTER_BINDING_LATEST.json', binding)
    write_json(state/'OPERATOR_FAILURE_ROUTER_SUMMARY_LATEST.json', summary)
    tracker=root/'OPEN_OPERATOR_VISUAL_TRACKER.html'; html_txt=tracker.read_text(encoding='utf-8')
    cards=''.join(f'<article class="route-card {c["status"].lower()}"><h3>{html.escape(c["failure_class"])}</h3><p><b>{html.escape(c["status"])}</b> · {html.escape(c["severity"])} · {c["record_count"]} record(s)</p><p>Route: <code>{html.escape(c["route_id"])}</code></p></article>' for c in clusters) or '<p class="oktext">No failure clusters found.</p>'
    route_list=''.join(f'<li><b>{html.escape(r["target_workflow"])}</b><br>{html.escape(r["action"])}</li>' for r in routes) or '<li>No routes generated.</li>'
    s=report['summary']
    section=f'<section class="grid" style="margin-top:14px" data-section="failure_cluster_repair_router"><section class="panel"><h2>Failure clusters → repair routes</h2><div class="chips"><span class="chip">clusters <b>{len(clusters)}</b></span><span class="chip">active <b>{s["active_cluster_count"]}</b></span><span class="chip">monitor <b>{s["monitor_cluster_count"]}</b></span><span class="chip">resolved/suppressed <b>{s["resolved_or_suppressed_cluster_count"]}</b></span></div><div class="route-grid">{cards}</div></section><aside class="panel"><h2>Router actions</h2><ul class="evidence">{route_list}</ul><p>Source: <code>runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json</code></p></aside></section>'
    extra_css='.route-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:12px}.route-card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:12px}.route-card h3{margin:.1rem 0 .35rem;font-size:.98rem}.route-card.active{border-color:rgba(251,113,133,.7)}.route-card.monitor{border-color:rgba(251,191,36,.55)}.route-card.resolved_reference,.route-card.suppressed_by_later_pass{border-color:rgba(34,197,94,.45)}@media(max-width:760px){.route-grid{grid-template-columns:1fr}}'
    if 'data-section="failure_cluster_repair_router"' not in html_txt:
        html_txt=html_txt.replace('</style>', extra_css+'</style>')
        html_txt=html_txt.replace('<p class="footer">Generated by', section+'<p class="footer">Generated by')
    write_text(tracker, html_txt)
    build_report={'artifact_type':'MB_FAILURE_CLUSTER_ROUTER_BUILD_REPORT.v1','stage_id':STAGE,'created_utc':utc(),'verdict':'PASS','outputs':['runtime/traces/observability/FAILURE_CLUSTER_REPORT_LATEST.json','runtime/traces/observability/REPAIR_ROUTER_BINDING_LATEST.json','runtime/state/operator_surface/OPERATOR_FAILURE_ROUTER_SUMMARY_LATEST.json','OPEN_OPERATOR_VISUAL_TRACKER.html'],'summary':report['summary']}
    write_json(obs/'FAILURE_CLUSTER_ROUTER_BUILD_REPORT_LATEST.json', build_report)
    print(json.dumps(build_report, indent=2, sort_keys=True))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); args=ap.parse_args(); build(Path(args.root).resolve())
if __name__=='__main__': main()
