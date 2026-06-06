#!/usr/bin/env python3
"""Contract wrapper for runtime_starter_smoke_v1.
Prevents the observed wrong CLI shape: passing the root as a positional argument.
Only --root <path> or --zip <path> are accepted. The wrapper invokes the
underlying gate with the correct named option and emits a method-reliability
friendly JSON result.
"""
from __future__ import annotations
import argparse, importlib.util, json, pathlib, sys, time

def _load_underlying():
    here = pathlib.Path(__file__).resolve()
    target = here.with_name('runtime_starter_smoke_v1.py')
    spec = importlib.util.spec_from_file_location('runtime_starter_smoke_v1', target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load {target}')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _deny(code: str, message: str, unknown=None) -> int:
    print(json.dumps({
        'artifact_type':'MB_RUNTIME_STARTER_SMOKE_CONTRACT_WRAPPER_RESULT.v1',
        'created_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
        'decision':'DENY','error_code':code,'message':message,'unknown_args':unknown or [],
        'allowed_shapes':['--root <path>','--zip <path>']
    }, indent=2, sort_keys=True))
    return 2

def main(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument('--root')
    parser.add_argument('--zip')
    parser.add_argument('--json', action='store_true')
    args, unknown = parser.parse_known_args(argv)
    if unknown:
        return _deny('MB_CLI_CONTRACT_DENY_POSITIONAL_ARGS','Positional or unknown arguments are forbidden. Use --root <path> or --zip <path>.', unknown)
    if bool(args.root) == bool(args.zip):
        return _deny('MB_CLI_CONTRACT_DENY_EXACTLY_ONE_TARGET','Provide exactly one target: --root or --zip.')
    mod = _load_underlying()
    if args.root:
        res = mod.validate_root(args.root)
        target_shape='--root'
    else:
        res = mod.validate_zip(args.zip)
        target_shape='--zip'
    out = {
        'artifact_type':'MB_RUNTIME_STARTER_SMOKE_CONTRACT_WRAPPER_RESULT.v1',
        'created_utc':time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()),
        'decision':res.get('decision','DENY'),
        'target_shape':target_shape,
        'underlying_gate':'runtime/governance/runtime_starter_smoke_v1.py',
        'underlying_result':res,
        'method_reliability_lesson':'METHOD_RUNTIME_STARTER_SMOKE_CLI_SHAPE_v1'
    }
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out['decision']=='ALLOW' else 2
if __name__ == '__main__':
    raise SystemExit(main())
