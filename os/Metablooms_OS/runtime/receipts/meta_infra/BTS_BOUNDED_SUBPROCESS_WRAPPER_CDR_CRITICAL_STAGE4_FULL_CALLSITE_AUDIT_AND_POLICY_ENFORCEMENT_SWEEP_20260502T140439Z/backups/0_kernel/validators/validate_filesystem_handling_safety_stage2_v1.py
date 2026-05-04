#!/usr/bin/env python3
from __future__ import annotations
import argparse, collections, json, py_compile, subprocess, tempfile, time, zipfile
from pathlib import Path
SCHEMA_VERSION='FILESYSTEM_HANDLING_SAFETY_STAGE2_VALIDATION_v2_NO_BROAD_EXTRACT'
REQUIRED=['Metablooms_OS/bin/mb','Metablooms_OS/0_kernel/lib/filesystem_safety_v1.py','Metablooms_OS/0_kernel/lib/trace_diff_logger_v1.py','Metablooms_OS/0_kernel/lib/archive_extraction_route_v1.py','Metablooms_OS/0_kernel/security/export_promotion_gate_v1.py','Metablooms_OS/0_kernel/validators/validate_filesystem_handling_safety_stage2_v1.py','Metablooms_OS/0_kernel/registry/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_POLICY_v2.json','Metablooms_OS/runtime/export_promotion/EXPORT_FILESYSTEM_SAFETY_PROOF_LATEST.json','Metablooms_OS/runtime/receipts/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_STAGE2_RECEIPT_LATEST.json','Metablooms_OS/runtime/handoffs/filesystem_handling/FILESYSTEM_HANDLING_SAFETY_STAGE2_HANDOFF_LATEST.json']
def now(): return time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
def run(cmd, timeout=45, cwd=None):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout,cwd=str(cwd) if cwd else None)
    return {'cmd':cmd,'rc':p.returncode,'stdout_tail':p.stdout[-2000:],'stderr_tail':p.stderr[-2000:]}
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--archive'); ap.add_argument('--root'); ap.add_argument('--json',action='store_true')
    args=ap.parse_args(argv); issues=[]; info={}; smokes={}
    if not args.archive and not args.root: args.root=str(Path(__file__).resolve().parents[2])
    if args.archive:
        archive=Path(args.archive)
        if not archive.exists(): issues.append({'reason':'archive_missing','archive':str(archive)})
        else:
            with zipfile.ZipFile(archive) as z:
                names=z.namelist(); c=collections.Counter(names); info['entries']=len(names); bad=z.testzip(); info['zipfile_testzip_bad_member']=bad
                if bad: issues.append({'reason':'zipfile_testzip_bad_member','bad':bad})
                dup=[n for n,v in c.items() if v>1]; info['duplicate_entry_count']=len(dup)
                if dup: issues.append({'reason':'duplicate_entries','sample':dup[:20]})
                missing=[p for p in REQUIRED if p not in c]; info['missing_required']=missing
                if missing: issues.append({'reason':'missing_required','paths':missing})
            with tempfile.TemporaryDirectory(dir='/mnt/data') as td:
                root=Path(td)/'Metablooms_OS'
                with zipfile.ZipFile(archive) as z:
                    for n in z.namelist():
                        if n in REQUIRED or n.startswith('Metablooms_OS/0_kernel/registry/security/') or n.startswith('Metablooms_OS/0_kernel/registry/operator_surface/') or n.startswith('Metablooms_OS/0_kernel/scripts/') or n=='Metablooms_OS/0_kernel/security/security_gate_enforcer_v1.py': z.extract(n,Path(td))
                (root/'boot_manifest_v1.json').write_text('{}\n')
                for rel in ['0_kernel/lib/filesystem_safety_v1.py','0_kernel/lib/trace_diff_logger_v1.py','0_kernel/lib/archive_extraction_route_v1.py','0_kernel/security/export_promotion_gate_v1.py','0_kernel/validators/validate_filesystem_handling_safety_stage2_v1.py']:
                    try: py_compile.compile(str(root/rel),doraise=True)
                    except Exception as e: issues.append({'reason':'python_compile_failure','path':rel,'error':repr(e)})
                tdir=Path(td)/'smoke'; tdir.mkdir(); (tdir/'a.tmp').write_text('{}')
                smokes['atomic_preflight']=run(['python3','-S',str(root/'0_kernel/lib/filesystem_safety_v1.py'),'preflight','--tmp',str(tdir/'a.tmp'),'--dst',str(tdir/'a.json')],30,cwd=root)
                src=tdir/'src'; (src/'bin').mkdir(parents=True); (src/'0_kernel/lib').mkdir(parents=True); (src/'boot_manifest_v1.json').write_text('{}'); (src/'bin/mb').write_text('x'); (src/'0_kernel/lib/filesystem_safety_v1.py').write_text('#x')
                smokes['mark_finalized']=run(['python3','-S',str(root/'0_kernel/lib/filesystem_safety_v1.py'),'mark-finalized','--root',str(src)],30,cwd=root)
                smokes['validate_finalized_root']=run(['python3','-S',str(root/'0_kernel/lib/filesystem_safety_v1.py'),'validate-root','--root',str(src)],30,cwd=root)
                smokes['diff_summary']=run(['python3','-S',str(root/'0_kernel/lib/trace_diff_logger_v1.py'),'--root',str(src),'--max-list','3','--max-files','20'],30,cwd=root)
                smokes['export_promotion_gate']=run(['python3','-S',str(root/'0_kernel/security/export_promotion_gate_v1.py'),'--archive',str(archive),'--json'],45,cwd=root)
                for key, token in [('atomic_preflight','ATOMIC_REPLACE_SAFE'),('mark_finalized','FINALIZATION_MARKED'),('validate_finalized_root','FINALIZED_ROOT_PASS'),('diff_summary','DIFFERENTIAL_TRACE_SUMMARY'),('export_promotion_gate','EXPORT_PROMOTION_PASS')]:
                    if smokes[key]['rc']!=0 or token not in smokes[key]['stdout_tail']: issues.append({'reason':'smoke_failed','smoke':key,'expected_token':token,'result':smokes[key]})
    else:
        root=Path(args.root); missing=[p.replace('Metablooms_OS/','') for p in REQUIRED if not (root/p.replace('Metablooms_OS/','')).exists()]; info['missing_required_from_root']=missing
        if missing: issues.append({'reason':'missing_required_from_root','paths':missing})
    out={'schema_version':SCHEMA_VERSION,'verdict':'PASS' if not issues else 'FAIL','created_utc':now(),'info':info,'smokes':smokes,'issues':issues}
    print(json.dumps(out,indent=2,sort_keys=True)); return 0 if not issues else 2
if __name__=='__main__': raise SystemExit(main())
