#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time
from pathlib import Path

REQUIRED = [
    '0_kernel/registry/observability/MB_TRACE_SPAN_EVENT_SCHEMA_v1.json',
    '0_kernel/registry/observability/MB_CAUSAL_STAGE_GRAPH_SCHEMA_v1.json',
    '0_kernel/registry/observability/MB_OBSERVABILITY_BOOT_INGESTION_SPEC_v1.json',
    '0_kernel/scripts/observability_boot_ingest_v1.py',
    '0_kernel/validators/validate_observability_trace_span_ledger_stage2_v1.py',
    'docs/observability/OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE2.md',
    'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl',
    'runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json',
    'runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json',
    'runtime/traces/observability/BOOT_INGESTION_REPORT_LATEST.json'
]
FIELDS = ['schema_version','event_name','trace_id','span_id','parent_span_id','stage_id','event_kind','status','timestamp_utc','source_artifact','input_materials','output_artifacts','attributes']
VALID_STATUS = {'OK','WARN','ERROR','BLOCKED'}
VALID_KINDS = {'boot','stage','validator','receipt','handoff','export','decision','tracker','tool','unknown'}

def utc_now():
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())

def load(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return {'_parse_error': repr(e)}

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--write-report', action='store_true')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    issues = []
    checks = {rel: (root / rel).exists() for rel in REQUIRED}
    for rel, ok in checks.items():
        if not ok:
            issues.append({'missing': rel})
    ledger_path = root / 'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl'
    records = []
    parse_errors = []
    if ledger_path.exists():
        for idx, line in enumerate(ledger_path.read_text(encoding='utf-8').splitlines(), start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception as e:
                parse_errors.append({'line': idx, 'error': repr(e), 'sample': line[:200]})
                continue
            records.append(rec)
            missing = [f for f in FIELDS if f not in rec]
            if missing:
                issues.append({'line': idx, 'missing_fields': missing})
            if rec.get('schema_version') != 'MB_TRACE_SPAN_EVENT.v1':
                issues.append({'line': idx, 'invalid_schema_version': rec.get('schema_version')})
            if rec.get('status') not in VALID_STATUS:
                issues.append({'line': idx, 'invalid_status': rec.get('status')})
            if rec.get('event_kind') not in VALID_KINDS:
                issues.append({'line': idx, 'invalid_event_kind': rec.get('event_kind')})
            if rec.get('status') in {'ERROR','BLOCKED'}:
                attrs = rec.get('attributes') if isinstance(rec.get('attributes'), dict) else {}
                if not any(k in attrs for k in ('error','blocker','reason')):
                    issues.append({'line': idx, 'missing_error_blocker_reason': True})
            if not isinstance(rec.get('input_materials'), list) or not isinstance(rec.get('output_artifacts'), list):
                issues.append({'line': idx, 'materials_or_outputs_not_lists': True})
    if parse_errors:
        issues.append({'parse_errors': parse_errors[:10]})
    if not records:
        issues.append({'empty_ledger': str(ledger_path)})
    span_ids = {r.get('span_id') for r in records if r.get('span_id')}
    for r in records:
        parent = r.get('parent_span_id')
        if parent is not None and parent not in span_ids:
            issues.append({'span_id': r.get('span_id'), 'unknown_parent_span_id': parent})
    index_path = root / 'runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json'
    graph_path = root / 'runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json'
    index = load(index_path) if index_path.exists() else {}
    graph = load(graph_path) if graph_path.exists() else {}
    if index.get('record_count') != len(records):
        issues.append({'index_record_count_mismatch': {'index': index.get('record_count'), 'ledger': len(records)}})
    if graph.get('summary', {}).get('record_count') != len(records):
        issues.append({'graph_record_count_mismatch': {'graph': graph.get('summary', {}).get('record_count'), 'ledger': len(records)}})
    graph_nodes = {n.get('span_id') for n in graph.get('nodes', []) if isinstance(n, dict)} if isinstance(graph, dict) else set()
    if graph_nodes and graph_nodes != span_ids:
        issues.append({'graph_node_span_set_mismatch': {'graph_nodes': len(graph_nodes), 'ledger_spans': len(span_ids)}})
    for e in graph.get('edges', []) if isinstance(graph, dict) else []:
        if e.get('parent_span_id') not in span_ids or e.get('child_span_id') not in span_ids:
            issues.append({'graph_edge_unknown_span': e})
    verdict = 'PASS' if not issues else 'FAIL'
    report = {
        'artifact_type': 'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE2_VALIDATION.v1',
        'created_utc': utc_now(),
        'verdict': verdict,
        'root': str(root),
        'required_checks': checks,
        'record_count': len(records),
        'span_count': len(span_ids),
        'index_record_count': index.get('record_count'),
        'graph_node_count': graph.get('summary', {}).get('node_count') if isinstance(graph, dict) else None,
        'issues': issues
    }
    if args.write_report:
        out = root / 'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE2_VALIDATION_LATEST.json'
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        report['report_path'] = str(out)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if verdict == 'PASS' else 2

if __name__ == '__main__':
    raise SystemExit(main())
