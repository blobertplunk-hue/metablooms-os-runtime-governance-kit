#!/usr/bin/env python3
"""MetaBlooms sandbox router policy evaluator.
Stdlib-only; intended to be invoked with python3 -S.
Usage: python3 -S sandbox_router_policy_loader_v1.py <task> <method>
"""
import json, os, sys
ROOT = os.environ.get('METABLOOMS_ROOT','/mnt/data/Metablooms_OS')
CANDIDATES = [
    '0_kernel/registry/sandbox_capability_router/SANDBOX_CAPABILITY_ROUTER_CARTRIDGE_LATEST.json',
    '0_kernel/registry/sandbox_capability_router/SANDBOX_ROUTER_ENFORCEMENT_WIRING_LATEST.json',
]
TASK = sys.argv[1] if len(sys.argv) > 1 else 'boot_probe'
METHOD = sys.argv[2] if len(sys.argv) > 2 else 'auto'

def load_router():
    errors=[]
    for rel in CANDIDATES:
        p=os.path.join(ROOT, rel)
        try:
            if os.path.exists(p):
                with open(p, encoding='utf-8') as f:
                    return p, json.load(f)
        except Exception as e:
            errors.append({'path':p,'error':str(e)})
    raise RuntimeError('router_not_found '+json.dumps(errors, sort_keys=True))

def decide(router):
    routes = router.get('routes') or {}
    route = routes.get(TASK)
    if not route:
        return {'allowed':False,'decision':'DENY','reason':'unknown_task','task':TASK,'method':METHOD}
    hay = (TASK + ' ' + METHOD).lower()
    hits=[]
    for rule in router.get('global_denylist') or []:
        applies_to = [str(x).lower() for x in rule.get('applies_to') or []]
        patterns = [str(x).lower() for x in rule.get('patterns') or []]
        applies = TASK.lower() in applies_to or any(x and x in hay for x in applies_to)
        hit = any(p and p in hay for p in patterns)
        if applies and hit:
            hits.append(rule.get('id','unknown_deny_rule'))
    if hits:
        return {'allowed':False,'decision':'DENY','reason':'denylist_hit','deny_hits':hits,'task':TASK,'method':METHOD}
    preferred = route.get('preferred') or []
    fallback = route.get('fallback') or []
    allowed = METHOD == 'auto' or METHOD == 'policy_deny' or METHOD in preferred or METHOD in fallback
    return {
        'allowed': bool(allowed),
        'decision': 'ALLOW' if allowed else 'DENY',
        'reason': 'route_allowed' if allowed else 'method_not_in_route',
        'task': TASK,
        'method': METHOD,
        'required_gates': route.get('required_gates') or [],
        'preferred': preferred,
        'fallback': fallback,
    }

def main():
    try:
        p, router = load_router()
        out = decide(router)
        out['router_path']=p
        out['evaluator']='python3-S-policy-evaluator'
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0 if out.get('allowed') else 7
    except Exception as e:
        print(json.dumps({'allowed':False,'decision':'DENY','reason':str(e),'task':TASK,'method':METHOD,'evaluator':'python3-S-policy-evaluator'}, indent=2, sort_keys=True))
        return 9
if __name__ == '__main__':
    sys.exit(main())
