#!/usr/bin/env python3
from __future__ import annotations
import json, os, pathlib, shutil, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from importlib.machinery import SourceFileLoader
writer_mod = SourceFileLoader('atomic_json_writer_v1', str(ROOT/'0_kernel/lib/io/atomic_json_writer_v1.py')).load_module()
write_atomic_json = writer_mod.write_atomic_json

WORK = ROOT/'runtime/tmp/atomic_json_writer_stage2_executable_harness'
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir(parents=True)
RECEIPTS = WORK/'receipts'; RECEIPTS.mkdir()
ALLOWED = WORK/'allowed'; ALLOWED.mkdir()
OUTSIDE = WORK/'outside'; OUTSIDE.mkdir()

results=[]
def run(name, envelope, expected_status, check=None):
    env = dict(envelope)
    env.setdefault('operation_id', name)
    env.setdefault('allowed_roots', [str(ALLOWED)])
    env.setdefault('receipt_dir', str(RECEIPTS/name))
    pathlib.Path(env['receipt_dir']).mkdir(parents=True, exist_ok=True)
    d = write_atomic_json(env)
    ok = d.get('status') == expected_status
    extra = None
    if ok and check:
        try:
            extra = check(d)
            ok = bool(extra is True or extra is None)
        except Exception as exc:
            ok=False; extra=f'{type(exc).__name__}: {exc}'
    if d.get('ok') is False and not d.get('failure_event_path'):
        ok=False; extra='missing_failure_event_path'
    if d.get('receipt_path') and not pathlib.Path(d['receipt_path']).exists():
        ok=False; extra='missing_decision_receipt'
    results.append({'name':name,'expected':expected_status,'actual':d.get('status'),'pass':ok,'extra':extra,'decision':d})

run('success_create_parent', {
    'target_path': str(ALLOWED/'nested'/'ok.json'), 'payload': {'b':2,'a':1}, 'create_parent': True, 'overwrite_mode':'replace'
}, 'ALLOW_SUCCESS', lambda d: json.loads((ALLOWED/'nested'/'ok.json').read_text()) == {'a':1,'b':2})

existing = ALLOWED/'existing.json'; existing.write_text('{"old":true}\n')
run('success_replace_existing', {
    'target_path': str(existing), 'payload': {'new': True}, 'overwrite_mode':'replace'
}, 'ALLOW_SUCCESS', lambda d: json.loads(existing.read_text()) == {'new': True})

run('deny_path_escape_dotdot', {
    'target_path': str(ALLOWED/'..'/'outside'/'evil.json'), 'payload': {'x':1}, 'create_parent': True
}, 'DENY_PATH_ESCAPE')

run('deny_bad_suffix', {
    'target_path': str(ALLOWED/'bad.txt'), 'payload': {'x':1}
}, 'DENY_SUFFIX')

existing2 = ALLOWED/'deny_exists.json'; existing2.write_text('{"old":true}\n')
run('deny_exists_create_new', {
    'target_path': str(existing2), 'payload': {'new': True}, 'overwrite_mode':'create_new'
}, 'DENY_EXISTS', lambda d: json.loads(existing2.read_text()) == {'old': True})

run('deny_unserializable', {
    'target_path': str(ALLOWED/'badpayload.json'), 'payload': {'s': {1,2,3}}
}, 'DENY_SERIALIZATION')

run('deny_nonfinite_nan', {
    'target_path': str(ALLOWED/'nan.json'), 'payload': {'x': float('nan')}
}, 'DENY_SERIALIZATION')

run('deny_size_limit', {
    'target_path': str(ALLOWED/'huge.json'), 'payload': {'x': 'a'*100}, 'max_bytes': 20
}, 'DENY_SIZE_LIMIT')

# Symlink target and symlink ancestor tests; skip symlink creation only if platform blocks it.
try:
    link_file = ALLOWED/'linkfile.json'
    os.symlink(str(OUTSIDE/'real.json'), str(link_file))
    run('deny_symlink_target', {'target_path': str(link_file), 'payload': {'x':1}}, 'DENY_SYMLINK')
    link_dir = ALLOWED/'linkdir'
    os.symlink(str(OUTSIDE), str(link_dir))
    run('deny_symlink_ancestor', {'target_path': str(link_dir/'x.json'), 'payload': {'x':1}}, 'DENY_SYMLINK')
except (OSError, NotImplementedError) as exc:
    results.append({'name':'symlink_tests_skipped','expected':'SYMLINK_TESTABLE','actual':type(exc).__name__,'pass':True,'extra':str(exc)})

run('deny_missing_parent', {
    'target_path': str(ALLOWED/'missing_parent'/'x.json'), 'payload': {'x': 1}, 'create_parent': False
}, 'DENY_SCHEMA_INVALID')

run('deny_invalid_allowed_roots', {
    'target_path': str(ALLOWED/'x.json'), 'payload': {'x': 1}, 'allowed_roots': []
}, 'DENY_SCHEMA_INVALID')

passed = all(r['pass'] for r in results)
out = {'artifact_type':'AtomicJsonWriterExecutableFixtureResults.v1','passed':passed,'results':results}
print(json.dumps(out, indent=2, sort_keys=True, ensure_ascii=False))
sys.exit(0 if passed else 1)
