#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, subprocess, sys, time, hashlib
from pathlib import Path
STAGE='OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE7_METHOD_WRAPPER_CALLSITE_RETROFIT_AND_BOOT_SEQUENCE_ENFORCEMENT'
def sha_file(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
    return h.hexdigest()
def load(p:Path): return json.loads(p.read_text(encoding='utf-8'))
def run(cmd, cwd):
    cp=subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, timeout=30)
    try: out=json.loads(cp.stdout)
    except Exception: out={'raw_stdout':cp.stdout,'stderr':cp.stderr}
    return {'cmd':cmd,'returncode':cp.returncode,'stdout':out,'stderr':cp.stderr}
def main(argv=None):
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--json', action='store_true'); args=ap.parse_args(argv)
    root=Path(args.root).resolve(); issues=[]; checks=[]
    required=['0_kernel/registry/observability/MB_BOOT_SEQUENCE_WRAPPER_ENFORCEMENT_v1.json','runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py','runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py.sha256','0_kernel/registry/BOOT_REQUIRED_GATES_v1.json','0_kernel/registry/RUNTIME_STARTER_SMOKE_CONTRACT_v1.json','runtime/governance/new_chat_start_contract_validator_v1.py','0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md','NEW_CHAT_START_HERE.md','CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','OPEN_OPERATOR_VISUAL_TRACKER.html']
    for rel in required:
        p=root/rel; ok=p.is_file() and p.stat().st_size>0; checks.append({'path':rel,'exists_nonempty':ok,'sha256':sha_file(p) if p.exists() and p.is_file() else None})
        if not ok: issues.append('missing_or_empty:'+rel)
    if not issues:
        ptrs=[load(root/r) for r in ['CURRENT_FULL_AUTHORITY_POINTER_v1.json','runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json','0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json']]
        if ptrs[0] != ptrs[1] or ptrs[0] != ptrs[2]: issues.append('authority_pointer_copies_not_identical')
        ptr=ptrs[0]
        if ptr.get('stage_id')!=STAGE or ptr.get('last_stage')!=STAGE: issues.append('pointer_not_stage7')
        if not any('runtime_starter_smoke_contract_wrapper_v1.py' in str(x) for x in ptr.get('required_start_sequence',[])): issues.append('pointer_start_sequence_omits_wrapper')
        if any(str(x).strip()=='Run runtime/governance/runtime_starter_smoke_v1.py.' for x in ptr.get('required_start_sequence',[])): issues.append('pointer_start_sequence_uses_direct_smoke')
        gates=load(root/'0_kernel/registry/BOOT_REQUIRED_GATES_v1.json')
        if 'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py' not in gates.get('required_files',[]): issues.append('boot_required_gates_missing_wrapper')
        if 'runtime_starter_smoke_contract_wrapper_denied' not in gates.get('fail_closed_conditions',[]): issues.append('boot_required_gates_missing_wrapper_deny_condition')
        contract=load(root/'0_kernel/registry/RUNTIME_STARTER_SMOKE_CONTRACT_v1.json')
        if contract.get('operator_entrypoint')!='runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py': issues.append('runtime_contract_operator_entrypoint_not_wrapper')
        for rel in ['0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md','NEW_CHAT_START_HERE.md']:
            txt=(root/rel).read_text(encoding='utf-8')
            if 'runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json' not in txt: issues.append('doc_omits_wrapper:'+rel)
            if 'Run `runtime/governance/runtime_starter_smoke_v1.py`' in txt or 'Run runtime/governance/runtime_starter_smoke_v1.py.' in txt: issues.append('doc_uses_direct_smoke:'+rel)
        html=(root/'OPEN_OPERATOR_VISUAL_TRACKER.html').read_text(encoding='utf-8')
        if 'data-section="boot_sequence_enforcement"' not in html: issues.append('tracker_missing_boot_sequence_enforcement_section')
    wrapper=root/'runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py'
    good=run([sys.executable, str(wrapper),'--root',str(root),'--json'], root)
    bad=run([sys.executable, str(wrapper),str(root),'--json'], root)
    newchat=run([sys.executable, str(root/'runtime/governance/new_chat_start_contract_validator_v1.py'), str(root)], root)
    smoke_checks=[
      {'name':'wrapper_named_root_allows','pass':good['returncode']==0 and good['stdout'].get('decision')=='ALLOW','result':good},
      {'name':'wrapper_positional_root_denies','pass':bad['returncode']!=0 and bad['stdout'].get('decision')=='DENY' and bad['stdout'].get('error_code')=='MB_CLI_CONTRACT_DENY_POSITIONAL_ARGS','result':bad},
      {'name':'new_chat_validator_allows','pass':newchat['returncode']==0 and newchat['stdout'].get('decision')=='ALLOW','result':newchat}]
    for c in smoke_checks:
        if not c['pass']: issues.append('smoke_check_failed:'+c['name'])
    report={'artifact_type':'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE7_BOOT_SEQUENCE_ENFORCEMENT_VALIDATION.v1','stage_id':STAGE,'created_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),'verdict':'PASS' if not issues else 'FAIL','checks':checks,'smoke_checks':smoke_checks,'issues':issues}
    out=root/'runtime/traces/observability/TRACE_SPAN_LEDGER_STAGE7_BOOT_SEQUENCE_ENFORCEMENT_VALIDATION_LATEST.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    text=json.dumps(report, indent=2, sort_keys=True)+'\n'; out.write_text(text, encoding='utf-8'); out.with_suffix(out.suffix+'.sha256').write_text(hashlib.sha256(text.encode()).hexdigest()+'  '+out.name+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['verdict']=='PASS' else 2
if __name__=='__main__': raise SystemExit(main())
