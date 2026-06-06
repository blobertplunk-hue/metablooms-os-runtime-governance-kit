#!/usr/bin/env python3
import json, time
from pathlib import Path

def nested_get(obj, dotted):
    cur = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur

def evaluate(route_packet, see_receipt_path=None):
    research_required = "research_required" in set(route_packet.get("matched_routes", []) or []) or "SEE_PASS" in set(route_packet.get("required_stages", []) or [])
    if not research_required:
        return {"stage":"RESEARCH_FAILURE_BLOCKING","research_required":False,"decision":"ALLOW","verdict":"PASS","issues":[]}
    if not see_receipt_path:
        return {"stage":"RESEARCH_FAILURE_BLOCKING","research_required":True,"decision":"BLOCK","verdict":"FAIL","issues":["research_required_but_no_see_receipt_provided"]}
    path = Path(see_receipt_path)
    if not path.exists():
        return {"stage":"RESEARCH_FAILURE_BLOCKING","research_required":True,"decision":"BLOCK","verdict":"FAIL","issues":["see_receipt_path_missing"]}
    receipt = json.loads(path.read_text())
    issues = []
    if receipt.get("stage") != "SEE_VALIDATION": issues.append("see_receipt_stage_not_SEE_VALIDATION")
    if receipt.get("verdict") != "PASS": issues.append("see_receipt_verdict_not_PASS")
    for dotted in ["web_run_evidence_validation.passed", "source_binding_validation.passed", "semantic_validation.passed"]:
        if nested_get(receipt, dotted) is not True: issues.append(dotted + "_not_true")
    return {"stage":"RESEARCH_FAILURE_BLOCKING","research_required":True,"decision":"BLOCK" if issues else "ALLOW","verdict":"FAIL" if issues else "PASS","issues":issues}

if __name__ == "__main__":
    print(json.dumps({"module":"research_failure_blocker_v1","status":"importable","time":time.time()}))
