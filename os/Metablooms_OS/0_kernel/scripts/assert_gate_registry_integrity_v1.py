#!/usr/bin/env python3
"""Assert MetaBlooms gate registry integrity. Must run under python3 -S."""
import json, sys, hashlib, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "runtime/governance/registries/gate_registry_v1.json"

def sha256_path(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(65536), b''):
            h.update(b)
    return h.hexdigest()

def fail(msg, report):
    report.setdefault("errors", []).append(msg)

def validate(path=None):
    if "site" in sys.modules:
        return {"decision":"fail","errors":["validator must run under python3 -S; site module is loaded"]}
    p=Path(path) if path else DEFAULT
    report={"validator":"assert_gate_registry_integrity_v1","created_utc":datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z'),"registry_path":str(p),"decision":"pass","errors":[],"warnings":[]}
    if not p.exists():
        return {**report,"decision":"fail","errors":[f"registry missing: {p}"]}
    data=json.loads(p.read_text())
    report["registry_sha256"]=sha256_path(p)
    required=["registry_id","version","created_utc","status","governance_rules","gates"]
    for k in required:
        if k not in data: fail(f"missing top-level field: {k}", report)
    if data.get("registry_id") != "gate_registry_v1": fail("registry_id must be gate_registry_v1", report)
    seen=set(); enabled=0
    for idx,g in enumerate(data.get("gates", [])):
        gid=g.get("gate_id", f"<missing:{idx}>")
        if gid in seen: fail(f"duplicate gate_id: {gid}", report)
        seen.add(gid)
        for k in ["gate_id","phase","status","enabled","blocking","entrypoint","launcher","applies_to","required_inputs","outputs","decision_log_required","source","reason"]:
            if k not in g: fail(f"{gid}: missing field {k}", report)
        if g.get("enabled"):
            enabled += 1
            ep=g.get("entrypoint")
            if not ep: fail(f"{gid}: enabled gate lacks entrypoint", report)
            elif not (ROOT/ep).exists(): fail(f"{gid}: enabled entrypoint missing: {ep}", report)
            if g.get("launcher") not in ("python3_S","shell","node","internal"):
                fail(f"{gid}: unsupported launcher {g.get('launcher')}", report)
            if not isinstance(g.get("applies_to"), list) or not g.get("applies_to"):
                fail(f"{gid}: enabled gate must list applies_to", report)
            if g.get("blocking") is True and not g.get("decision_log_required"):
                fail(f"{gid}: blocking gate requires decision log", report)
        else:
            if g.get("status") not in ("deferred","retired"):
                fail(f"{gid}: disabled gate must be deferred or retired", report)
            if not g.get("reason"):
                fail(f"{gid}: disabled gate requires reason", report)
    report["gate_count"]=len(data.get("gates", []))
    report["enabled_count"]=enabled
    if report["errors"]:
        report["decision"]="fail"
    return report

if __name__ == "__main__":
    result=validate(sys.argv[1] if len(sys.argv)>1 else None)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("decision")=="pass" else 1)
