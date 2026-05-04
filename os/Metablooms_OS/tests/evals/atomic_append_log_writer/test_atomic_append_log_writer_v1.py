#!/usr/bin/env python3
from __future__ import annotations
import json, math, os, shutil, sys, tempfile
from pathlib import Path
from multiprocessing import Process

ROOT = Path('/mnt/data/Metablooms_OS')
sys.path.insert(0, str(ROOT))
from importlib import import_module
writer = import_module('0_kernel.lib.io.atomic_append_log_writer_v1')


def rec(i=1, severity='info', payload=None):
    return {
        'schema_version': 'MetaBloomsLogRecord.v1',
        'event_id': f'event-{i}',
        'timestamp_utc': '2026-05-02T15:10:00Z',
        'source': 'atomic_append_log_writer_fixture',
        'event_type': 'fixture',
        'severity': severity,
        'payload': {'i': i} if payload is None else payload,
    }


def env(base, name='events.log.jsonl', record=None, **kw):
    receipt = base / 'receipts'
    return {
        'schema_version': 'AtomicAppendLogEnvelope.v1',
        'operation_id': kw.pop('operation_id', 'appendop01'),
        'log_path': str(base / name),
        'allowed_roots': [str(base)],
        'record': rec() if record is None else record,
        'durability_mode': kw.pop('durability_mode', 'sync_always'),
        'max_record_bytes': kw.pop('max_record_bytes', 4096),
        'max_file_bytes': kw.pop('max_file_bytes', 1048576),
        'create_parent': kw.pop('create_parent', True),
        'receipt_dir': str(receipt),
        **kw,
    }


def parse_lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line]


def worker(base, idx):
    e = env(Path(base), name='stress.events.jsonl', record=rec(idx), operation_id=f'stress-{idx:03d}', durability_mode='sync_on_critical')
    d = writer.append_governed_jsonl_record(e)
    if not d.get('ok'):
        raise SystemExit(1)


def main():
    work = Path(tempfile.mkdtemp(prefix='mb_append_fixture_', dir='/mnt/data'))
    results=[]
    try:
        # positive: single append
        d=writer.append_governed_jsonl_record(env(work, operation_id='append001'))
        results.append({'id':'append_single_jsonl_record','status':d['status'],'pass':d['status']=='ALLOW_APPENDED' and (work/'events.log.jsonl').exists()})
        # positive: order preservation
        writer.append_governed_jsonl_record(env(work, name='order.log.jsonl', record=rec(1), operation_id='order001'))
        writer.append_governed_jsonl_record(env(work, name='order.log.jsonl', record=rec(2), operation_id='order002'))
        lines=parse_lines(work/'order.log.jsonl')
        results.append({'id':'append_two_records_preserves_order','status':'ALLOW_APPENDED_AND_TWO_VALID_LINES','pass':[x['event_id'] for x in lines]==['event-1','event-2']})
        # create parent
        d=writer.append_governed_jsonl_record(env(work/'nestedroot', name='a/b/create.log.jsonl', operation_id='create001'))
        results.append({'id':'create_parent_when_authorized','status':d['status'],'pass':d['status']=='ALLOW_APPENDED'})
        # unicode roundtrip
        d=writer.append_governed_jsonl_record(env(work, name='unicode.log.jsonl', record=rec(3, payload={'text':'niño 🌱 line\\nescaped'}), operation_id='unicode001'))
        lines=parse_lines(work/'unicode.log.jsonl')
        results.append({'id':'unicode_payload_roundtrip','status':d['status'],'pass':lines[0]['payload']['text']=='niño 🌱 line\\nescaped'})
        # fsync critical
        d=writer.append_governed_jsonl_record(env(work, name='critical.log.jsonl', record=rec(4, severity='critical'), operation_id='fsync001', durability_mode='sync_on_critical'))
        results.append({'id':'critical_fsync_path','status':d['status'],'pass':d['status']=='ALLOW_APPENDED' and d['fsync_file'] is True})
        # negatives
        d=writer.append_governed_jsonl_record(env(work, name='../escape.log.jsonl', operation_id='escape001'))
        results.append({'id':'deny_path_escape_dotdot','status':d['status'],'pass':d['status']=='DENY_PATH_DENIED'})
        d=writer.append_governed_jsonl_record(env(work, name='bad.txt', operation_id='suffix001'))
        results.append({'id':'deny_unsafe_suffix','status':d['status'],'pass':d['status']=='DENY_UNSAFE_SUFFIX'})
        d=writer.append_governed_jsonl_record(env(work, record='raw string', operation_id='raw001'))
        results.append({'id':'deny_raw_string_record','status':d['status'],'pass':d['status']=='DENY_RECORD_INVALID'})
        d=writer.append_governed_jsonl_record(env(work, record=rec(5, payload={'x': math.nan}), operation_id='nan001'))
        results.append({'id':'deny_non_finite_json','status':d['status'],'pass':d['status']=='DENY_RECORD_INVALID'})
        d=writer.append_governed_jsonl_record(env(work, record=rec(6, payload={'blob':'x'*5000}), operation_id='large001', max_record_bytes=256))
        results.append({'id':'deny_record_too_large','status':d['status'],'pass':d['status']=='DENY_RECORD_TOO_LARGE'})
        d=writer.append_governed_jsonl_record(env(work, operation_id='policy001', durability_mode='sync_never_with_exception'))
        results.append({'id':'deny_no_fsync_without_exception_for_governance','status':d['status'],'pass':d['status']=='DENY_POLICY_DENIED'})
        # symlink target and ancestor
        target = work/'real.log.jsonl'; link = work/'link.log.jsonl'; link.symlink_to(target)
        d=writer.append_governed_jsonl_record(env(work, name='link.log.jsonl', operation_id='slink001'))
        results.append({'id':'deny_symlink_target','status':d['status'],'pass':d['status']=='DENY_SYMLINK_DENIED'})
        realdir=work/'realdir'; realdir.mkdir(exist_ok=True); linkdir=work/'linkdir'; linkdir.symlink_to(realdir, target_is_directory=True)
        d=writer.append_governed_jsonl_record(env(work, name='linkdir/inside.log.jsonl', operation_id='slink002'))
        results.append({'id':'deny_symlink_ancestor','status':d['status'],'pass':d['status']=='DENY_SYMLINK_DENIED'})
        # multiprocessing stress
        procs=[Process(target=worker,args=(str(work),i)) for i in range(20)]
        for p in procs: p.start()
        for p in procs: p.join()
        lines=parse_lines(work/'stress.events.jsonl')
        results.append({'id':'multi_process_append_no_corrupt_lines','status':'ALL_LINES_PARSE_AND_COUNT_MATCHES','pass':len(lines)==20 and all(isinstance(x,dict) for x in lines) and all(p.exitcode==0 for p in procs)})
        print(json.dumps({'ok': all(r['pass'] for r in results), 'results': results, 'workdir': str(work)}, indent=2))
        return 0 if all(r['pass'] for r in results) else 1
    finally:
        pass

if __name__ == '__main__':
    raise SystemExit(main())
