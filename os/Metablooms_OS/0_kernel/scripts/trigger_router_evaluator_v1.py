#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, time, sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_ROOT = Path("/mnt/data/Metablooms_OS_refined")
DEFAULT_ROUTER = DEFAULT_ROOT / "0_kernel/schemas/TRIGGER_ROUTER_v1.json"
DEFAULT_PIPELINE = DEFAULT_ROOT / "0_kernel/schemas/MASTER_PIPELINE_CONTRACT_v1.json"
DEFAULT_RECEIPT_DIR = DEFAULT_ROOT / "0_kernel/registry/router_receipts"

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

def evaluate_request(request: str, router: Dict[str, Any], pipeline: Dict[str, Any]) -> Dict[str, Any]:
    text = (request or "").lower()
    matched_routes, required_stages, required_modules = [], [], []
    issues = []
    pipeline_stages = set(pipeline.get("stages", []))
    for route in router.get("routes", []):
        signals = [str(s).lower() for s in route.get("signals", [])]
        if any(s in text for s in signals):
            rid = route.get("route_id")
            matched_routes.append(rid)
            for st in route.get("required_stages", []):
                if st not in required_stages:
                    required_stages.append(st)
                if st not in pipeline_stages:
                    issues.append(f"route_stage_not_in_pipeline:{rid}:{st}")
            for m in route.get("required_modules", []):
                if m not in required_modules:
                    required_modules.append(m)
    if "BOOT" not in required_stages:
        required_stages.insert(0, "BOOT")
    packet = {
        "version": "1.0",
        "created_at": time.time(),
        "stage": "TRIGGER_ROUTER_EVALUATION",
        "request": request,
        "matched_routes": matched_routes,
        "required_stages": required_stages,
        "required_modules": required_modules,
        "pipeline_stage_validation": {"missing": [i.split(":")[-1] for i in issues if i.startswith("route_stage_not_in_pipeline")]},
        "verdict": "PASS" if not issues else "FAIL",
        "issues": issues
    }
    return packet

def write_receipt(packet: Dict[str, Any], receipt_dir: Path) -> Path:
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / f"ROUTER_RECEIPT_{int(time.time()*1000)}.json"
    packet["receipt_path"] = str(path)
    _mb_write_json_file(path, packet, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_trigger_router_evaluator_v1_py_L53', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    return path

def main(argv: Optional[List[str]]=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request")
    ap.add_argument("--request-file")
    ap.add_argument("--router", default=str(DEFAULT_ROUTER))
    ap.add_argument("--pipeline", default=str(DEFAULT_PIPELINE))
    ap.add_argument("--receipt-dir", default=str(DEFAULT_RECEIPT_DIR))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    req = args.request
    if args.request_file:
        req = Path(args.request_file).read_text(encoding="utf-8")
    if not req:
        print(json.dumps({"verdict":"FAIL","issues":["missing_request"]}, indent=2), file=sys.stderr)
        return 2
    packet = evaluate_request(req, load_json(Path(args.router)), load_json(Path(args.pipeline)))
    receipt = write_receipt(packet, Path(args.receipt_dir))
    if args.json:
        print(json.dumps(packet, indent=2))
    else:
        print(json.dumps({"verdict": packet["verdict"], "receipt": str(receipt)}, indent=2))
    return 0 if packet["verdict"] == "PASS" else 3

if __name__ == "__main__":
    raise SystemExit(main())
