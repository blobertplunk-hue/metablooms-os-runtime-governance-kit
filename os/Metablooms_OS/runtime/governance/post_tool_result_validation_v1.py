#!/usr/bin/env python3
"""MetaBlooms post_tool_result_validation_v1.

Validates that a tool result satisfied its declared intent before BTS commits
success. This is a local OS gate: it validates evidence packets for filesystem
writes, ZIP exports/CRC proof, and generic receipt-backed actions.
"""
from __future__ import annotations
import argparse, json, hashlib, os
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict

def utc(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
    return h.hexdigest()
def atomic(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(data, encoding='utf-8')
    os.replace(tmp, path)
def countish(value):
    if value is None: return 0
    if isinstance(value, list): return len(value)
    if isinstance(value, dict): return len(value)
    try: return int(value)
    except Exception: return 0 if not value else 1

def fail(env: Dict[str,Any], code: str, reasons: list[str], out: Path) -> Dict[str,Any]:
    res={
      'schema':'PostToolResultValidationDecision_v1',
      'validation_id':env.get('validation_id','UNKNOWN'),
      'stage_id':env.get('stage_id','UNKNOWN'),
      'tool_id':env.get('tool_id','UNKNOWN'),
      'action_type':env.get('action_type','UNKNOWN'),
      'decision':'DENY_SUCCESS_COMMIT',
      'reason_code':code,
      'reasons':reasons,
      'validated_at_utc':utc(),
      'safe_to_commit_success':False,
      'required_next_action':'repair_result_or_mark_tool_failure',
    }
    atomic(out, json.dumps(res, indent=2, sort_keys=True)+'\n')
    return res
def allow(env: Dict[str,Any], reasons: list[str], out: Path) -> Dict[str,Any]:
    res={
      'schema':'PostToolResultValidationDecision_v1',
      'validation_id':env.get('validation_id','UNKNOWN'),
      'stage_id':env.get('stage_id','UNKNOWN'),
      'tool_id':env.get('tool_id','UNKNOWN'),
      'action_type':env.get('action_type','UNKNOWN'),
      'decision':'ALLOW_SUCCESS_COMMIT',
      'reason_code':'RESULT_MATCHES_INTENT_AND_EVIDENCE',
      'reasons':reasons,
      'validated_at_utc':utc(),
      'safe_to_commit_success':True,
      'required_next_action':'emit_BTS_TOOL_RESULT_success_and_commit',
    }
    atomic(out, json.dumps(res, indent=2, sort_keys=True)+'\n')
    return res

def validate(env: Dict[str,Any], out: Path) -> Dict[str,Any]:
    required=['schema_version','validation_id','stage_id','tool_id','action_type','intent','expected','actual','artifacts','created_at_utc']
    missing=[k for k in required if k not in env]
    if missing: return fail(env,'SCHEMA_REQUIRED_FIELD_MISSING',[f'missing {missing}'],out)
    if env.get('schema_version')!='PostToolResultValidationEnvelope_v1': return fail(env,'UNSUPPORTED_SCHEMA',['schema_version must be PostToolResultValidationEnvelope_v1'],out)
    expected=env.get('expected') or {}; actual=env.get('actual') or {}; artifacts=env.get('artifacts') or {}
    reasons=[]
    # Common artifact path existence checks
    for key in ('primary_path','sidecar_path','receipt_path'):
        p=artifacts.get(key)
        if p:
            pp=Path(p)
            if not pp.exists(): return fail(env,'EXPECTED_ARTIFACT_MISSING',[f'{key} missing: {p}'],out)
            reasons.append(f'{key} exists')
    action=env.get('action_type')
    if action=='filesystem_write':
        target=Path(artifacts.get('primary_path',''))
        if not str(target): return fail(env,'TARGET_PATH_REQUIRED',['filesystem_write requires artifacts.primary_path'],out)
        if not target.exists(): return fail(env,'TARGET_NOT_WRITTEN',[f'target missing: {target}'],out)
        if expected.get('sha256') and sha256_file(target)!=expected.get('sha256'):
            return fail(env,'TARGET_SHA_MISMATCH',['target sha256 does not match expected'],out)
        min_bytes=expected.get('min_bytes',1)
        if target.stat().st_size < min_bytes: return fail(env,'TARGET_TOO_SMALL',[f'target bytes < {min_bytes}'],out)
        reasons += ['filesystem target exists', 'filesystem target size/sha constraints passed']
    elif action in ('node_zip_profile_export','zip_export'):
        zp=Path(artifacts.get('primary_path',''))
        if not zp.exists(): return fail(env,'ZIP_EXPORT_MISSING',[f'zip missing: {zp}'],out)
        if expected.get('sha256') and sha256_file(zp)!=expected.get('sha256'):
            return fail(env,'ZIP_SHA_MISMATCH',['zip sha256 does not match expected'],out)
        if actual.get('crc_verdict') and actual.get('crc_verdict')!='PASS':
            return fail(env,'ZIP_CRC_PROOF_FAILED',[f"crc_verdict={actual.get('crc_verdict')}"],out)
        if countish(actual.get('duplicates',0))!=0: return fail(env,'ZIP_DUPLICATES_PRESENT',[f"duplicates={actual.get('duplicates')}"],out)
        if countish(actual.get('unsafe_paths',0))!=0: return fail(env,'ZIP_UNSAFE_PATHS_PRESENT',[f"unsafe_paths={actual.get('unsafe_paths')}"],out)
        if zp.stat().st_size < expected.get('min_bytes',1): return fail(env,'ZIP_TOO_SMALL',[f'zip bytes too small'],out)
        reasons += ['zip exists', 'zip size/sha constraints passed', 'crc/duplicate/unsafe constraints passed']
    else:
        if expected.get('require_receipt') and not artifacts.get('receipt_path'):
            return fail(env,'RECEIPT_REQUIRED',['expected.require_receipt true but receipt_path missing'],out)
        reasons.append('generic receipt-backed validation passed')
    if actual.get('implementation_reality_verdict') and actual.get('implementation_reality_verdict')!='PASS':
        return fail(env,'IMPLEMENTATION_REALITY_FAILED',[f"implementation_reality_verdict={actual.get('implementation_reality_verdict')}"],out)
    return allow(env,reasons,out)

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('envelope')
    ap.add_argument('--out', required=False)
    ns=ap.parse_args(argv)
    env=json.loads(Path(ns.envelope).read_text())
    out=Path(ns.out or env.get('receipt_path') or Path(ns.envelope).with_suffix('.decision.json'))
    res=validate(env,out)
    print(json.dumps(res, indent=2, sort_keys=True))
    return 0 if res.get('decision')=='ALLOW_SUCCESS_COMMIT' else 20
if __name__=='__main__':
    raise SystemExit(main())
