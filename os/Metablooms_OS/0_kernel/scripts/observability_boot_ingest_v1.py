#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

STAGE_ID = 'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE2_UNIFIED_EVENT_SCHEMA_AND_BOOT_INGESTION'
EVENT_SCHEMA_VERSION = 'MB_TRACE_SPAN_EVENT.v1'
STATUS_MAP = {
    'PASS': 'OK', 'ALLOW': 'OK', 'DONE': 'OK', 'READY': 'OK', 'SUCCESS': 'OK',
    'FAIL': 'ERROR', 'DENY': 'BLOCKED', 'BLOCK': 'BLOCKED', 'BLOCKED': 'BLOCKED',
    'WARN': 'WARN', 'WARNING': 'WARN'
}

def utc_now() -> str:
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())

def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 512), b''):
            h.update(chunk)
    return h.hexdigest()

def safe_load(path: Path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception as e:
        return {'_parse_error': repr(e)}

EVIDENCE_PACKET_TYPES = {
    'CE_SYNTHESIS.v1',
    'SEE_PACKET.v1',
    'INTERNAL_OS_EVIDENCE.v1',
    'MB_NEXT_BUILD_DECISION.v1',
}

def _normalize_status_token(raw) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().upper()
    if not s:
        return None
    # Exact/prefix status parsing only. Do not substring-match prose; words
    # like "failure clustering" are valid evidence text, not an ERROR status.
    direct = {
        'PASS': 'OK', 'ALLOW': 'OK', 'DONE': 'OK', 'READY': 'OK', 'SUCCESS': 'OK', 'OK': 'OK',
        'FAIL': 'ERROR', 'FAILED': 'ERROR', 'ERROR': 'ERROR',
        'DENY': 'BLOCKED', 'DENIED': 'BLOCKED', 'BLOCK': 'BLOCKED', 'BLOCKED': 'BLOCKED',
        'WARN': 'WARN', 'WARNING': 'WARN', 'MONITOR': 'WARN'
    }
    if s in direct:
        return direct[s]
    for prefix, val in (
        ('PASS_', 'OK'), ('PASS-', 'OK'), ('PASS WITH', 'OK'),
        ('ALLOW_', 'OK'), ('SUCCESS_', 'OK'),
        ('FAIL_', 'ERROR'), ('FAILED_', 'ERROR'), ('ERROR_', 'ERROR'),
        ('DENY_', 'BLOCKED'), ('DENIED_', 'BLOCKED'), ('BLOCKED_', 'BLOCKED'),
        ('WARN_', 'WARN'), ('WARNING_', 'WARN')
    ):
        if s.startswith(prefix):
            return val
    return None

def infer_status(payload) -> str:
    if not isinstance(payload, dict):
        return 'WARN'
    for key in ('verdict', 'status', 'handoff_status'):
        parsed = _normalize_status_token(payload.get(key))
        if parsed:
            return parsed
    # Decision is sometimes a validator decision (ALLOW/DENY), but often a CE
    # prose recommendation. Treat only compact status-like values as status.
    decision = payload.get('decision')
    if isinstance(decision, str) and len(decision.strip().split()) <= 3:
        parsed = _normalize_status_token(decision)
        if parsed:
            return parsed
    artifact_type = str(payload.get('artifact_type') or '')
    explicit_failure_fields = ('error', 'exception', 'traceback', 'blocked_reason', 'failure_reason')
    if artifact_type in EVIDENCE_PACKET_TYPES and not any(payload.get(k) for k in explicit_failure_fields):
        return 'OK'
    if payload.get('issues') or payload.get('failed_checks') or payload.get('parse_error') or payload.get('_parse_error'):
        return 'WARN'
    return 'OK'

def infer_stage(path: Path, payload) -> str:
    if isinstance(payload, dict):
        for key in ('stage_id', 'stage', 'stage_name', 'recommended_next_stage_id', 'next_stage'):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    name = path.stem
    parent = path.parent.name
    return parent if parent and parent not in ('receipts', 'handoffs') else name

def kind_and_event(root: Path, path: Path, payload):
    rel = str(path.relative_to(root))
    low = rel.lower()
    if 'boot_receipts' in low:
        return 'boot', 'metablooms.boot.receipt'
    if '/handoffs/' in low or 'handoff' in path.name.lower():
        return 'handoff', 'metablooms.handoff.ready'
    if 'roadmap' in low or 'decision' in path.name.lower():
        return 'decision', 'metablooms.decision.next_build'
    if 'tracker_state' in low:
        return 'tracker', 'metablooms.tracker.state'
    if 'export' in low:
        return 'export', 'metablooms.export.receipt'
    if 'validator' in low or 'validation' in path.name.lower():
        return 'validator', 'metablooms.validator.result'
    if 'receipt' in path.name.lower() or '/receipts/' in low:
        return 'receipt', 'metablooms.stage.receipt'
    return 'unknown', 'metablooms.stage.artifact'

def timestamp_from_payload(path: Path, payload) -> str:
    if isinstance(payload, dict):
        for key in ('created_utc', 'timestamp_utc', 'last_updated_utc'):
            val = payload.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime(path.stat().st_mtime))

def output_refs(root: Path, payload) -> list[str]:
    out = []
    if isinstance(payload, dict):
        for key in ('receipt_path', 'handoff_path', 'export_path', 'zip_path', 'output', 'output_path', 'tracker_preview_path'):
            val = payload.get(key)
            if isinstance(val, str) and val:
                out.append(val)
        for key in ('outputs', 'output_artifacts'):
            vals = payload.get(key)
            if isinstance(vals, list):
                out.extend(str(v) for v in vals if isinstance(v, (str, int, float)))
    return sorted(set(out))[:40]

def collect_inputs(root: Path, max_files: int):
    patterns = [
        '0_kernel/registry/boot_receipts/**/*.json',
        'runtime/receipts/**/*.json',
        'runtime/handoffs/**/*.json',
        '0_kernel/registry/roadmap/NEXT_BUILD_DECISION_LATEST.json',
        'runtime/state/TRACKER_STATE_v1.json',
    ]
    seen = {}
    for pat in patterns:
        files = [p for p in root.glob(pat) if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for p in files[:max_files]:
            seen[str(p)] = p
    return sorted(seen.values(), key=lambda p: (p.stat().st_mtime, str(p)))

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default='.')
    ap.add_argument('--max-files-per-glob', type=int, default=80)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    out_dir = root / 'runtime/traces/observability'
    out_dir.mkdir(parents=True, exist_ok=True)
    run_ts = utc_now()
    trace_id = sha_text(str(root) + '|' + STAGE_ID + '|' + run_ts)[:32]
    root_span_id = sha_text(trace_id + '|root')[:16]
    root_record = {
        'schema_version': EVENT_SCHEMA_VERSION,
        'event_name': 'metablooms.boot_ingestion.start',
        'trace_id': trace_id,
        'span_id': root_span_id,
        'parent_span_id': None,
        'stage_id': STAGE_ID,
        'event_kind': 'stage',
        'status': 'OK',
        'timestamp_utc': run_ts,
        'source_artifact': '0_kernel/scripts/observability_boot_ingest_v1.py',
        'input_materials': [],
        'output_artifacts': [
            'runtime/traces/observability/TRACE_SPAN_LEDGER_LATEST.jsonl',
            'runtime/traces/observability/TRACE_SPAN_LEDGER_INDEX_LATEST.json',
            'runtime/traces/observability/CAUSAL_STAGE_GRAPH_LATEST.json',
            'runtime/traces/observability/BOOT_INGESTION_REPORT_LATEST.json'
        ],
        'attributes': {'max_files_per_glob': args.max_files_per_glob, 'bounded': True}
    }
    records = [root_record]
    files = collect_inputs(root, args.max_files_per_glob)
    for idx, p in enumerate(files, start=1):
        payload = safe_load(p)
        kind, event_name = kind_and_event(root, p, payload)
        rel = str(p.relative_to(root))
        status = infer_status(payload)
        stage = infer_stage(p, payload)
        span_id = sha_text(trace_id + '|' + rel)[:16]
        attrs = {
            'source_sha256': sha_file(p),
            'source_size_bytes': p.stat().st_size,
            'artifact_type': payload.get('artifact_type') if isinstance(payload, dict) else None,
            'verdict': payload.get('verdict') if isinstance(payload, dict) else None,
            'status_raw': payload.get('status') if isinstance(payload, dict) else None,
        }
        if status in ('ERROR', 'BLOCKED'):
            attrs['reason'] = payload.get('reason') or payload.get('blocker') or payload.get('error') or 'source artifact status indicated non-pass state'
        records.append({
            'schema_version': EVENT_SCHEMA_VERSION,
            'event_name': event_name,
            'trace_id': trace_id,
            'span_id': span_id,
            'parent_span_id': root_span_id,
            'stage_id': stage,
            'event_kind': kind,
            'status': status,
            'timestamp_utc': timestamp_from_payload(p, payload),
            'source_artifact': rel,
            'input_materials': [rel],
            'output_artifacts': output_refs(root, payload),
            'attributes': attrs,
            # Stage 1 compatibility fields:
            'name': event_name,
            'stage_name': stage,
            'event': event_name,
        })
    # Add Stage 1 compatibility fields to root record too.
    records[0]['name'] = records[0]['event_name']
    records[0]['stage_name'] = records[0]['stage_id']
    records[0]['event'] = records[0]['event_name']
    ledger = out_dir / 'TRACE_SPAN_LEDGER_LATEST.jsonl'
    ledger.write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in records), encoding='utf-8')
    by_status, by_kind, by_stage = {}, {}, {}
    for r in records:
        by_status[r['status']] = by_status.get(r['status'], 0) + 1
        by_kind[r['event_kind']] = by_kind.get(r['event_kind'], 0) + 1
        by_stage[r['stage_id']] = by_stage.get(r['stage_id'], 0) + 1
    index = {
        'artifact_type': 'MB_TRACE_SPAN_LEDGER_INDEX.v1',
        'created_utc': run_ts,
        'source_ledger': str(ledger.relative_to(root)),
        'record_count': len(records),
        'trace_id': trace_id,
        'root_span_id': root_span_id,
        'by_status': by_status,
        'by_kind': by_kind,
        'by_stage_top': dict(sorted(by_stage.items(), key=lambda kv: (-kv[1], kv[0]))[:30]),
        'latest_records': [{k: r.get(k) for k in ['timestamp_utc','event_name','stage_id','status','source_artifact','span_id','parent_span_id']} for r in records[-20:]],
        'schema': '0_kernel/registry/observability/MB_TRACE_SPAN_EVENT_SCHEMA_v1.json'
    }
    index_path = out_dir / 'TRACE_SPAN_LEDGER_INDEX_LATEST.json'
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    nodes = [{k: r.get(k) for k in ['span_id','trace_id','stage_id','event_name','event_kind','status','timestamp_utc','source_artifact']} for r in records]
    edges = [{'parent_span_id': r['parent_span_id'], 'child_span_id': r['span_id'], 'relation': 'parent_child'} for r in records if r.get('parent_span_id')]
    graph = {
        'artifact_type': 'MB_CAUSAL_STAGE_GRAPH.v1',
        'created_utc': run_ts,
        'source_ledger': str(ledger.relative_to(root)),
        'schema': '0_kernel/registry/observability/MB_CAUSAL_STAGE_GRAPH_SCHEMA_v1.json',
        'nodes': nodes,
        'edges': edges,
        'summary': {'node_count': len(nodes), 'edge_count': len(edges), 'record_count': len(records), 'by_status': by_status, 'by_kind': by_kind}
    }
    graph_path = out_dir / 'CAUSAL_STAGE_GRAPH_LATEST.json'
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    report = {
        'artifact_type': 'MB_OBSERVABILITY_BOOT_INGESTION_REPORT.v1',
        'created_utc': run_ts,
        'stage_id': STAGE_ID,
        'verdict': 'PASS',
        'root': str(root),
        'input_file_count': len(files),
        'record_count': len(records),
        'outputs': [str(ledger), str(index_path), str(graph_path)],
        'trace_id': trace_id,
        'by_status': by_status,
        'by_kind': by_kind
    }
    report_path = out_dir / 'BOOT_INGESTION_REPORT_LATEST.json'
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print('PASS', report_path)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
