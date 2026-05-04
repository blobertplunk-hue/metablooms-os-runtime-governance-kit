#!/usr/bin/env python3
"""Prompt route pre-execution enforcer v1.
Converts a raw task-start prompt into an explicit governed execution contract.
No model calls are made here; it deterministically classifies, strengthens, and gates prompts.
"""
from __future__ import annotations
import hashlib, json, pathlib, re, time

ROOT_DEFAULT = pathlib.Path(__file__).resolve().parents[2]
KNOWN_PROFILES = {
    "governed_implementation": ["implement", "install", "repair", "patch", "execute", "stage", "export"],
    "governed_research": ["research", "web.run", "SEE", "evidence", "sources"],
    "governed_artifact_generation": ["create", "generate", "artifact", "bundle", "docx", "html", "csv"],
    "authentic": ["authentic", "student", "real world"],
    "adaptive": ["adaptive", "differentiate", "route", "personalize"],
    "wit": ["wit", "funny", "humor"]
}
TASK_TYPES = {
    "governed_implementation": ["install", "repair", "patch", "execute", "stage", "export", "implement"],
    "research": ["research", "web.run", "SEE", "cite", "evidence", "sources"],
    "artifact_generation": ["create", "generate", "make", "build", "docx", "html", "csv", "bundle"],
    "audit": ["audit", "inspect", "verify", "validate", "compare"]
}
GATES_BY_TASK = {
    "governed_implementation": ["boot_verify", "gap_audit", "prompt_auto_improvement", "preexecution_route_enforcer", "artifact_write", "validator_replay", "receipt_handoff", "export_attempt"],
    "research": ["research_plan", "web_run_required", "SEE", "CE", "evidence_binding", "receipt_handoff"],
    "artifact_generation": ["artifact_spec", "prompt_auto_improvement", "preexecution_route_enforcer", "readback_validation", "checksum", "receipt_handoff"],
    "audit": ["boot_verify", "source_integrity", "evidence_table", "gap_classification", "receipt_handoff"]
}

def _load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def classify_task(prompt: str) -> str:
    low = prompt.lower()
    scores = {k: sum(1 for w in words if w.lower() in low) for k, words in TASK_TYPES.items()}
    best = max(scores, key=lambda k: (scores[k], k == "governed_implementation"))
    return best if scores[best] > 0 else "governed_implementation"

def select_profile(prompt: str, task_type: str, root: pathlib.Path = ROOT_DEFAULT) -> str:
    low = prompt.lower()
    profile_scores = {p: sum(1 for w in words if w.lower() in low) for p, words in KNOWN_PROFILES.items()}
    if task_type == "research":
        profile_scores["governed_research"] += 3
    elif task_type == "artifact_generation":
        profile_scores["governed_artifact_generation"] += 3
    elif task_type == "governed_implementation":
        profile_scores["governed_implementation"] += 3
    profile = max(profile_scores, key=lambda k: profile_scores[k])
    registry = _load_json(root / "runtime/cartridges/prompt_governance_v1/PROMPT_PROFILE_REGISTRY_v1.json", {})
    available = set()
    if isinstance(registry, dict):
        raw = registry.get("profiles", registry)
        if isinstance(raw, dict): available.update(raw.keys())
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("profile_id"): available.add(item["profile_id"])
                elif isinstance(item, str): available.add(item)
    aliases = {"governed_research":"governed_research", "governed_artifact_generation":"governed_artifact_generation", "governed_implementation":"governed_implementation", "authentic":"authentic", "adaptive":"adaptive", "wit":"wit"}
    chosen = aliases.get(profile, "governed_implementation")
    if available and chosen not in available:
        # fall back to strongest governed profile present, else fail closed downstream
        for cand in ["governed_implementation", "governed_research", "governed_artifact_generation", "authentic", "adaptive", "wit"]:
            if cand in available: return cand
    return chosen

def improve_prompt(prompt: str, task_type: str, profile: str) -> str:
    prompt = prompt.strip()
    additions = []
    if "boot" not in prompt.lower(): additions.append("Boot and verify the current authority artifacts before acting.")
    if "receipt" not in prompt.lower(): additions.append("Write a receipt and handoff for every completed bounded stage.")
    if "validate" not in prompt.lower() and "test" not in prompt.lower(): additions.append("Validate readback and behavior before claiming completion.")
    if task_type in {"governed_implementation", "artifact_generation"} and "export" not in prompt.lower(): additions.append("Attempt a full OS export when validation permits; otherwise write a blocked/partial receipt.")
    if task_type == "research" and "web.run" not in prompt.lower(): additions.append("Use web.run and bind external claims to citations.")
    additions.append("Order any ranked options best-to-worst and explain why option 1 is best when options are presented.")
    additions.append("Fail closed if required artifacts, gates, or evidence are missing.")
    return prompt + "\n\nGoverned pre-execution improvements:\n- " + "\n- ".join(additions)

def enforce_prompt_route(prompt: str, root: str | pathlib.Path | None = None, context: dict | None = None) -> dict:
    root = pathlib.Path(root) if root else ROOT_DEFAULT
    if not prompt or not prompt.strip():
        return {"decision":"DENY", "reason":"missing_user_prompt"}
    task_type = classify_task(prompt)
    profile = select_profile(prompt, task_type, root)
    improved = improve_prompt(prompt, task_type, profile)
    required = GATES_BY_TASK.get(task_type, GATES_BY_TASK["governed_implementation"])
    ranked = [
        {"rank":1,"option":"execute_with_preexecution_contract","why":"best: binds task intent, profile, gates, artifacts, and validation before tools run"},
        {"rank":2,"option":"execute_with_existing_prompt_only","why":"weaker: may preserve user wording but misses automatic repair and governance hardening"},
        {"rank":3,"option":"manual_prompt_review_only","why":"weakest: delays execution and does not enforce artifact writeback"}
    ]
    payload = {
        "decision":"ALLOW",
        "created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "selected_profile":profile,
        "task_type":task_type,
        "improved_prompt":improved,
        "required_gates":required,
        "evidence_requirements":["web.run_required_for_current_or_best-practice_claims", "SEE_packet_when_research_used", "CE_packet_before_implementation_decision"],
        "artifact_requirements":["receipt", "handoff", "validation_packet", "checksum_for_exported_bundle"],
        "ranking_explanation":ranked,
        "fail_closed_conditions":["missing_user_prompt", "unknown_profile", "missing_required_gate", "artifact_write_unproven", "validator_denied"],
        "source_prompt_sha256":hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
    payload["contract_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload

if __name__ == "__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--root", default=None)
    args=ap.parse_args()
    print(json.dumps(enforce_prompt_route(args.prompt, args.root), indent=2, sort_keys=True))
