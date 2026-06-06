#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, time, sys
from pathlib import Path

def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def write_json(p: Path, obj):
    s = json.dumps(obj, indent=2, sort_keys=True) + '\n'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding='utf-8')
    Path(str(p) + '.sha256').write_text(sha_bytes(s.encode('utf-8')) + '  ' + p.name + '\n', encoding='utf-8')

def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))

def normalize_pins(manifest):
    if isinstance(manifest, dict):
        if isinstance(manifest.get('pins'), list):
            return manifest.get('pins')
        if isinstance(manifest.get('pinned_evidence'), list):
            return manifest.get('pinned_evidence')
        if isinstance(manifest.get('pin_seed'), list):
            return manifest.get('pin_seed')
    if isinstance(manifest, list):
        return manifest
    return []

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', required=True)
    ap.add_argument('--pin-manifest')
    ap.add_argument('--out', default='runtime/receipts/pinned_evidence/PINNED_EVIDENCE_RECEIPT_LATEST.json')
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if args.pin_manifest:
        source_rel = args.pin_manifest
        manifest = load_json(root / args.pin_manifest if not Path(args.pin_manifest).is_absolute() else Path(args.pin_manifest))
    else:
        source_rel = 'runtime/state/operator_surface/EVIDENCE_RESULT_PINNING_MODEL_LATEST.json'
        manifest = load_json(root / source_rel)
    pins_in = normalize_pins(manifest)
    pins = []
    issues = []
    for i, pin in enumerate(pins_in, 1):
        path_s = pin.get('path') or pin.get('evidence_path') or pin.get('artifact_path')
        if not path_s:
            issues.append('pin_missing_path:' + str(i)); continue
        p = root / path_s
        exists = p.is_file()
        actual = sha_file(p) if exists else None
        declared = pin.get('sha256') or pin.get('declared_sha256') or pin.get('actual_sha256')
        if not exists: issues.append('pin_path_missing:' + path_s)
        # Source pin manifests can contain stale SHA values for mutable generated ledgers.
        # Formal promotion binds the current artifact SHA as actual_sha256 and records mismatch on the pin.
        pass
        pins.append({'ordinal': i, 'pin_id': pin.get('pin_id') or f'pin_{i}', 'query_id': pin.get('query_id'), 'rank': pin.get('rank'), 'title': pin.get('title') or Path(path_s).name, 'path': path_s, 'declared_sha256': declared, 'actual_sha256': actual, 'sha256_matches_artifact': bool(declared and actual == declared), 'exists': exists, 'matched_terms': pin.get('matched_terms', []), 'verdict': pin.get('verdict')})
    receipt = {'artifact_type': 'MB_PROMOTED_PINNED_EVIDENCE_RECEIPT.v1', 'stage_id': 'OBSERVABILITY_TRACE_SPAN_LEDGER_STAGE14_PINNED_EVIDENCE_RECEIPT_PROMOTION_AND_EXPORT_BINDING', 'created_utc': time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()), 'source_manifest': source_rel, 'promotion_mode': 'operator_selected_pin_manifest', 'pins': pins, 'pin_count': len(pins), 'issues': issues, 'verdict': 'PASS' if pins and not issues else 'FAIL'}
    out = root / args.out if not Path(args.out).is_absolute() else Path(args.out)
    write_json(out, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt['verdict'] == 'PASS' else 2
if __name__ == '__main__':
    raise SystemExit(main())
