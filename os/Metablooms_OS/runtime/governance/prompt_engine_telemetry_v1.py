#!/usr/bin/env python3
from __future__ import annotations
import json, hashlib, time
from pathlib import Path

def _hash_obj(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(',',':')).encode()).hexdigest()

def record_prompt_engine_event(root, event):
    root=Path(root)
    log=root/'runtime/state/PROMPT_ENGINE_TELEMETRY_LOG_v1.jsonl'
    log.parent.mkdir(parents=True, exist_ok=True)
    e=dict(event)
    e.setdefault('event_utc', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
    e.setdefault('event_hash', _hash_obj(e))
    with log.open('a', encoding='utf-8') as f:
        f.write(json.dumps(e, sort_keys=True)+'\n')
    return {'decision':'ALLOW','log':log.as_posix(),'event_hash':e['event_hash']}

if __name__=='__main__':
    import sys
    root=sys.argv[1] if len(sys.argv)>1 else Path.cwd()
    print(json.dumps(record_prompt_engine_event(root, {'event_type':'telemetry_self_test','profile':'governed_implementation','validator_decision':'ALLOW'}), indent=2))
