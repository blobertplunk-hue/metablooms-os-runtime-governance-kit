#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, pathlib, sys

try:
    import jsonschema
except Exception as e:
    jsonschema = None

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA = ROOT / '0_kernel/registry/browser_render_capability/browser_render_capability_resolver_decision_schema_v1.json'
FIXTURE_DIR = ROOT / 'tests/fixtures/browser_render_capability_resolver'
INDEX = FIXTURE_DIR / 'BROWSER_RENDER_CAPABILITY_RESOLVER_FIXTURE_INDEX_v1.json'


def validate_decision(obj, schema):
    required = schema['required']
    missing = [k for k in required if k not in obj]
    if missing:
        return False, f'missing_required:{missing}'
    if jsonschema:
        try:
            jsonschema.validate(obj, schema)
        except Exception as e:
            return False, f'jsonschema:{type(e).__name__}:{e}'
    return True, 'ok'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--decision', required=False)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    schema = json.load(open(SCHEMA))
    index = json.load(open(INDEX))
    results = []
    for name, expected in index['expected_decisions'].items():
        obj = json.load(open(FIXTURE_DIR / name))
        valid, reason = validate_decision(obj, schema)
        results.append({'fixture': name, 'schema_valid': valid, 'expected_decision': expected, 'actual_decision': obj.get('decision'), 'pass': bool(valid and obj.get('decision') == expected), 'reason': reason})
    if args.decision:
        obj = json.load(open(args.decision))
        valid, reason = validate_decision(obj, schema)
        # For the current sandbox, true browser is not required; render proxy is expected to be acceptable if WeasyPrint passes.
        results.append({'fixture': 'actual_local_resolver_decision', 'schema_valid': valid, 'expected_decision': 'ALLOW_RENDER_PROXY_WITH_LIMITATION_OR_ALLOW_BROWSER_SCREENSHOT', 'actual_decision': obj.get('decision'), 'selected_method': obj.get('selected_method'), 'pass': bool(valid and obj.get('decision') in ['ALLOW_RENDER_PROXY_WITH_LIMITATION','ALLOW_BROWSER_SCREENSHOT']), 'reason': reason})
    report = {'verdict': 'PASS' if all(r['pass'] for r in results) else 'FAIL', 'results': results}
    out = pathlib.Path(args.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['verdict'] == 'PASS' else 1
if __name__ == '__main__':
    raise SystemExit(main())
