#!/usr/bin/env python3 -S
### GOVERNANCE HEADER
# artifact_id: p0py_python_health_governance_v1
# purpose: Periodically probe python3 startup cost. Cache health state.
#          Route work away from normal python3 when startup is expensive.
#          Embed health state in stage receipts.
# tool_class: python3 -S (stdlib only)
# mutation_scope: writes health state cache only
# see_evidence:
#   - T1-ARTIFACT: python_diagnostic_receipt_v1.json SHA fc94dfcf...
#     "normal python3 ~280-294MB RSS / 1.2s; python3 -S ~14-16MB RSS / 0.09s"
#     "sitecustomize.py imports pandas/pydantic on every startup"
#   - Operational rule: prefer shell/node/jq; python3 -S for stdlib; avoid
#     normal python3 unless site packages genuinely required
###

import json, hashlib, os, subprocess, sys, time
from pathlib import Path

VERSION = "1.0"

DEFAULT_STATE_PATH = Path("/mnt/data/p0py_health_state_v1.json")
DEFAULT_RECEIPT_DIR = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/p0py_receipts")

# Thresholds (from diagnostic)
STARTUP_MS_FAST   = 200    # python3 -S is this fast
STARTUP_MS_NORMAL = 800    # acceptable
STARTUP_MS_SLOW   = 1400   # route away from normal python3
RSS_MB_FAST       = 20
RSS_MB_NORMAL     = 200
RSS_MB_SLOW       = 280    # diagnostic measured 280-294MB

# Cache TTL — recheck every N seconds (10 minutes)
CACHE_TTL_SECONDS = 600

ROUTING_TABLE = {
    "file_audit":       "shell (find/ls/wc)",
    "zip_ops":          "shell (zip/unzip)",
    "sha_verify":       "shell (sha256sum)",
    "json_read":        "python3 -S",
    "json_write":       "python3 -S",
    "sha_compute":      "python3 -S",
    "math_small":       "python3 -S",
    "doc_generation":   "node",
    "html_generation":  "node",
    "registry_query":   "python3 -S",
    "schema_validate":  "python3 -S",
    "site_packages":    "python3 (normal) — only if absolutely required",
}


def probe_python_light():
    """Probe python3 -S startup — always fast per diagnostic."""
    t0 = time.time()
    try:
        result = subprocess.run(
            ["python3", "-S", "-c", "import sys; print(sys.version_info.major)"],
            capture_output=True, text=True, timeout=5
        )
        ms = (time.time() - t0) * 1000
        ok = result.returncode == 0
        return {"available": ok, "startup_ms": round(ms, 1), "mode": "python3 -S"}
    except Exception as e:
        return {"available": False, "startup_ms": -1, "mode": "python3 -S", "error": str(e)}


def probe_python_normal():
    """Probe normal python3 startup cost."""
    t0 = time.time()
    try:
        result = subprocess.run(
            ["python3", "-c", "import sys; print(sys.version_info.major)"],
            capture_output=True, text=True, timeout=10
        )
        ms = (time.time() - t0) * 1000
        ok = result.returncode == 0
        return {"available": ok, "startup_ms": round(ms, 1), "mode": "python3 normal"}
    except Exception as e:
        return {"available": False, "startup_ms": -1, "mode": "python3 normal", "error": str(e)}


def classify_health(normal_ms):
    if normal_ms < 0:
        return "unavailable"
    if normal_ms <= STARTUP_MS_NORMAL:
        return "healthy"
    if normal_ms <= STARTUP_MS_SLOW:
        return "degraded"
    return "expensive"


def route_work(work_type, health_status):
    """Return recommended tool for work_type given current Python health."""
    if health_status in ("expensive", "degraded", "unavailable"):
        # Prefer non-Python tools for everything possible
        if work_type in ("file_audit", "zip_ops", "sha_verify"):
            return ROUTING_TABLE[work_type]
        if work_type in ("json_read", "json_write", "sha_compute", "math_small", "schema_validate"):
            return "python3 -S (stdlib only)"
        if work_type in ("doc_generation", "html_generation"):
            return "node"
        return "python3 -S if stdlib; shell otherwise"
    # Healthy: normal python3 allowed for site-package work
    return ROUTING_TABLE.get(work_type, "python3 -S")


def load_state(state_path):
    if not state_path.exists():
        return None
    try:
        d = json.loads(state_path.read_text())
        age = time.time() - d.get("probed_at", 0)
        if age > CACHE_TTL_SECONDS:
            return None   # expired
        return d
    except Exception:
        return None


def save_state(state_path, state):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = state_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(tmp, state_path)


def run_health_check(state_path=DEFAULT_STATE_PATH, force=False):
    """Run probes and persist state. Returns state dict."""
    cached = load_state(state_path)
    if cached and not force:
        cached["from_cache"] = True
        return cached

    light = probe_python_light()
    normal = probe_python_normal()
    health = classify_health(normal["startup_ms"])

    state = {
        "probed_at": time.time(),
        "probed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python3_S": light,
        "python3_normal": normal,
        "health_status": health,
        "routing_recommendation": {
            wt: route_work(wt, health) for wt in ROUTING_TABLE.keys()
        },
        "from_cache": False,
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
        "diagnostic_baseline": {
            "S_startup_ms": "90-160 (fast)",
            "normal_startup_ms": "1200 (sitecustomize loads pandas/pydantic)",
            "source": "python_diagnostic_receipt_v1.json SHA fc94dfcf..."
        }
    }
    save_state(state_path, state)
    return state


def embed_in_receipt(state):
    """Return a compact health summary for embedding in stage receipts."""
    return {
        "p0py_health": state["health_status"],
        "python3_S_ms": state["python3_S"]["startup_ms"],
        "python3_normal_ms": state["python3_normal"]["startup_ms"],
        "cache_age_s": round(time.time() - state["probed_at"]),
        "routing_note": (
            "Use python3 -S for stdlib work; shell for file ops"
            if state["health_status"] in ("expensive", "degraded")
            else "Normal python3 available but prefer python3 -S for startup cost"
        ),
    }


def write_receipt(state, receipt_dir):
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = {
        "receipt_type": "P0PY_HEALTH_RECEIPT",
        "created_at": time.time(),
        **state,
        "stage_embed": embed_in_receipt(state),
    }
    ts = int(time.time() * 1000)
    rpath = receipt_dir / f"P0PY_HEALTH_{ts}.json"
    tmp = rpath.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt, indent=2))
    os.replace(tmp, rpath)
    return str(rpath), hashlib.sha256(rpath.read_bytes()).hexdigest()


def main():
    import argparse
    ap = argparse.ArgumentParser(description="P0PY Python Health Governance v1")
    ap.add_argument("--state-path",   default=str(DEFAULT_STATE_PATH))
    ap.add_argument("--receipt-dir",  default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--force",        action="store_true", help="Force re-probe even if cached")
    ap.add_argument("--embed",        action="store_true", help="Print compact embed dict")
    ap.add_argument("--route",        help="Print routing recommendation for work type")
    ap.add_argument("--json-output",  action="store_true")
    args = ap.parse_args()

    state = run_health_check(Path(args.state_path), force=args.force)

    if args.route:
        rec = route_work(args.route, state["health_status"])
        print(f"Route '{args.route}' → {rec}")
        sys.exit(0)

    if args.embed:
        print(json.dumps(embed_in_receipt(state), indent=2))
        sys.exit(0)

    rpath, rsha = write_receipt(state, Path(args.receipt_dir))

    icon = {"healthy": "✓", "degraded": "⚠", "expensive": "✗", "unavailable": "✗"}
    h = state["health_status"]
    print(f"  [{icon.get(h,'?')}] P0PY: {h}  "
          f"python3-S={state['python3_S']['startup_ms']}ms  "
          f"normal={state['python3_normal']['startup_ms']}ms  "
          f"{'(cached)' if state.get('from_cache') else '(fresh probe)'}")

    if args.json_output:
        print(json.dumps(state, indent=2))

    sys.exit(0)


if __name__ == "__main__":
    main()
