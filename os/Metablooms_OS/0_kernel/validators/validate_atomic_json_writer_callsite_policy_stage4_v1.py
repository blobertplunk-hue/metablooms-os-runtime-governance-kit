#!/usr/bin/env python3
from __future__ import annotations

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
import ast,json,pathlib,argparse,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
EXEMPT=('runtime/','tests/evals/','0_kernel/vendor/','0_kernel/registry/failure_learning/','0_kernel/lib/io/atomic_json_writer_v1.py','0_kernel/lib/io/atomic_json_compat_v1.py')
def ex(rel):
    s=str(rel).replace('\\','/'); return any(s.startswith(x) for x in EXEMPT)
def is_jd(n): return isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='dumps' and isinstance(n.func.value,ast.Name) and n.func.value.id=='json'
def has_jd(n): return any(is_jd(x) for x in ast.walk(n))
def scan():
    blocking=[]; warnings=[]
    for p in ROOT.rglob('*.py'):
        rel=p.relative_to(ROOT)
        if ex(rel): continue
        try: txt=p.read_text('utf-8'); tree=ast.parse(txt)
        except Exception as e: warnings.append({'file':str(rel),'kind':'parse_error','error':str(e)}); continue
        for n in ast.walk(tree):
            if isinstance(n,ast.Call):
                src=ast.get_source_segment(txt,n) or ''
                fn=n.func
                if isinstance(fn,ast.Attribute) and fn.attr=='write_text' and n.args and has_jd(n.args[0]) and '_mb_write_json_file' not in src:
                    blocking.append({'file':str(rel),'line':n.lineno,'kind':'write_text_json_dumps','src':src[:220]})
                if isinstance(fn,ast.Attribute) and fn.attr=='dump' and isinstance(fn.value,ast.Name) and fn.value.id=='json':
                    blocking.append({'file':str(rel),'line':n.lineno,'kind':'json_dump_direct','src':src[:220]})
                if isinstance(fn,ast.Attribute) and fn.attr=='open' and n.args and isinstance(n.args[0],ast.Constant) and isinstance(n.args[0].value,str) and 'a' in n.args[0].value:
                    warnings.append({'file':str(rel),'line':n.lineno,'kind':'append_stream_deferred','src':src[:160]})
    return {'artifact_type':'AtomicJsonWriterCallsitePolicyStage4Result.v1','created_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'verdict':'PASS' if not blocking else 'FAIL','blocking_count':len(blocking),'warning_count':len(warnings),'blocking':blocking[:200],'warnings':warnings[:200]}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--json',action='store_true'); ap.add_argument('--json-out'); a=ap.parse_args(); out=scan()
    if a.json_out:
        q=pathlib.Path(a.json_out); q.parent.mkdir(parents=True,exist_ok=True); _mb_write_json_file(q, out, operation_id='STAGE4_POLICY_GATE_JSON_OUT', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=True, ensure_ascii=False, max_bytes=20000000)
    print(json.dumps(out,indent=2,sort_keys=True) if a.json else out['verdict']); return 0 if out['verdict']=='PASS' else 17
if __name__=='__main__': raise SystemExit(main())
