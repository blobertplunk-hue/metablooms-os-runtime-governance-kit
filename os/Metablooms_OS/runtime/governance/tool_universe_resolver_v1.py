#!/usr/bin/env python3
"""MetaBlooms Tool Universe Resolver v1.

Purpose:
  Convert the full known sandbox/tool/installable universe into a ranked,
  policy-filtered candidate set that BTS must evaluate before selecting tools.

Boundary:
  This resolver does not execute tools. It only resolves, scores, denies, and
  explains candidate tools for BTS_TOOL_EVALUATION.
"""
from __future__ import annotations
import argparse, json, hashlib, os, re, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RESOLVER_VERSION = "TOOL_UNIVERSE_RESOLVER_v1"
CANDIDATE_SCHEMA = "TOOL_CANDIDATE_SET_v1"
GENOME_PATH = Path("0_kernel/registry/tool_governance/TOOL_CAPABILITY_GENOME_BASELINE_v1.json")
SANDBOX_INVENTORY = Path("0_kernel/registry/tool_governance/sandbox_tool_probe_inventory_v1.json")
EXTERNAL_MANIFEST = Path("0_kernel/registry/tool_governance/EXTERNAL_TOOL_CAPABILITY_MANIFEST_v1.json")
INSTALL_PROFILE_REGISTRY = Path("0_kernel/registry/tool_governance/GOVERNED_TOOL_INSTALL_PROFILE_REGISTRY_v1.json")
COMPETENCE = Path("_bts/tool_competence.json")
FORBIDDEN_CANDIDATES = [Path("FORBIDDEN_VALIDATION_METHODS_v1.json"), Path("runtime/authority/FORBIDDEN_VALIDATION_METHODS_v1.json")]

JOB_RULES = [
    ("observability_trace_export", [r"observability", r"trace", r"tracing", r"span", r"otel", r"opentelemetry", r"langgraph", r"langsmith", r"openai agents", r"adapter"]),
    ("zip_export", [r"zip", r"export", r"authority", r"bundle", r"archive", r"package"]),
    ("zip_crc_proof", [r"crc", r"integrity", r"archive proof", r"validate zip", r"replay proof"]),
    ("html_validation", [r"html", r"tts", r"accessibility", r"dom", r"google sites", r"interactive"]),
    ("document_extraction", [r"pptx", r"powerpoint", r"docx", r"pdf", r"slides", r"extract"]),
    ("filesystem_repair", [r"repair", r"patch", r"write", r"copy", r"filesystem", r"file"]),
    ("see_web_research", [r"research", r"sota", r"current", r"2026", r"web", r"cite", r"evidence"]),
    ("spreadsheet_generation", [r"spreadsheet", r"xlsx", r"workbook", r"csv"]),
    ("external_install_profile", [r"install", r"npm", r"package", r"library", r"dependency"]),
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists(): return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def resolve_root(root: Optional[str]) -> Path:
    p = Path(root or os.environ.get("METABLOOMS_ROOT", "/mnt/data/Metablooms_OS"))
    if not p.exists(): raise RuntimeError(f"MetaBlooms root missing: {p}")
    return p

def classify_task(task: str, explicit_job_type: str = "") -> str:
    if explicit_job_type: return explicit_job_type
    t = task.lower()
    hits: List[Tuple[int,str]] = []
    for job, pats in JOB_RULES:
        score = sum(1 for pat in pats if re.search(pat, t))
        if score: hits.append((score, job))
    if not hits: return "general_governed_task"
    hits.sort(reverse=True)
    # Prefer specific observability/tracing work over the generic "export" token.
    # Stage 6R exposed that "trace export adapters" was too easily misrouted to zip_export.
    jobs = {j for _, j in hits}
    if "observability_trace_export" in jobs and any(w in t for w in ["trace", "tracing", "span", "opentelemetry", "otel", "langgraph", "langsmith", "openai agents", "observability"]):
        return "observability_trace_export"
    # bias authority export when both filesystem and zip appear, but only for real archive/authority exports.
    if "zip_export" in jobs and any(w in t for w in ["authority zip", "bootable full os", "os authority", "bundle zip", "archive", "package"]): return "zip_export"
    return hits[0][1]

def sandbox_available(root: Path) -> set[str]:
    inv = load_json(root / SANDBOX_INVENTORY, {})
    tools = set()
    raw = inv.get("tools", inv if isinstance(inv, list) else [])
    if isinstance(raw, dict): raw = raw.values()
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict) and item.get("available", item.get("exists", False)):
            name = str(item.get("tool") or item.get("name") or item.get("id") or "")
            if name: tools.add(name)
    return tools

def load_forbidden(root: Path) -> Dict[str, Any]:
    out = {"patterns": ["unzip -tqq", "unzip_tqq", "unzip-tqq"], "sources": []}
    for rel in FORBIDDEN_CANDIDATES:
        data = load_json(root / rel, None)
        if data is not None:
            out["sources"].append(str(rel))
            raw = json.dumps(data).lower()
            if "unzip" in raw: out["patterns"].append("unzip")
    return out

def genome_available(tool_id: str, genome: Dict[str, Any], available: set[str], install_profiles: Dict[str, Any]) -> bool:
    state = genome.get("install_state")
    if state in ["GOVERNED_PROFILE", "PROMOTED", "SMOKE_TESTED", "INSTALLED"]: return True
    if state == "INSTALLABLE": return bool(install_profiles)
    if tool_id.startswith("node_") and "node" in available: return True
    if tool_id.startswith("python") and ("python3" in available or "python" in available): return True
    return False

def candidate_status(genome: Dict[str, Any], job_type: str, available: bool, forbidden: Dict[str, Any]) -> str:
    tid = genome["tool_id"]
    if genome.get("install_state") == "DENIED" or genome.get("risk_tier") == "denied": return "DENIED"
    ftxt = json.dumps([tid, genome.get("execution_route", ""), genome.get("known_failure_classes", [])]).lower()
    if "unzip_tqq" in tid or "unzip -tqq" in ftxt: return "DENIED"
    if not available: return "DEFER_INSTALL"
    if job_type in genome.get("job_types", []) and genome.get("install_state") in ["GOVERNED_PROFILE", "PROMOTED"]: return "PREFERRED"
    if job_type in genome.get("job_types", []): return "ALLOWED"
    return "FALLBACK"

def score_candidate(genome: Dict[str, Any], job_type: str, status: str, competence: Dict[str, Any]) -> Tuple[float, List[str], Optional[float]]:
    score = 0.0; reasons=[]
    if status == "DENIED": return -100.0, ["denied by risk tier / forbidden-method memory"], None
    if status == "DEFER_INSTALL": score += 5; reasons.append("candidate is installable but not yet smoke-tested/promoted")
    if job_type in genome.get("job_types", []): score += 45; reasons.append(f"job_type match: {job_type}")
    if genome.get("install_state") in ["GOVERNED_PROFILE", "PROMOTED"]: score += 25; reasons.append("governed/promoted route")
    elif genome.get("install_state") == "SMOKE_TESTED": score += 18; reasons.append("smoke-tested route")
    elif genome.get("install_state") == "INSTALLED": score += 12; reasons.append("installed route")
    if genome.get("requires_approval"): score -= 3; reasons.append("requires approval")
    if any(job_type in p or "authority" in p for p in genome.get("preferred_when", [])): score += 10; reasons.append("preferred_when matches job family")
    comp = competence.get(genome["tool_id"], competence.get(genome.get("execution_route", ""), {}))
    comp_score = comp.get("score") if isinstance(comp, dict) else None
    if comp_score is not None:
        score += 10 * float(comp_score); reasons.append(f"BTS competence_score={comp_score}")
        if comp.get("flagged"): score -= 20; reasons.append("BTS competence flag lowers rank")
    if genome.get("known_failure_classes"): score -= min(15, 5*len(genome["known_failure_classes"])); reasons.append("known failure classes lower rank")
    score += (sum(ord(ch) for ch in genome.get("tool_id", "")) % 7) / 1000.0
    return round(score, 3), reasons, comp_score

def resolve(task: str, root: Path, stage_id: str, explicit_job_type: str = "") -> Dict[str, Any]:
    job_type = classify_task(task, explicit_job_type)
    baseline = load_json(root / GENOME_PATH, {"genomes": []})
    available = sandbox_available(root)
    install_profiles = load_json(root / INSTALL_PROFILE_REGISTRY, {}).get("profiles", {})
    competence = load_json(root / COMPETENCE, {})
    forbidden = load_forbidden(root)
    candidates=[]
    for genome in baseline.get("genomes", []):
        avail = genome_available(genome["tool_id"], genome, available, install_profiles)
        status = candidate_status(genome, job_type, avail, forbidden)
        score, reasons, comp_score = score_candidate(genome, job_type, status, competence)
        # Include relevant, denied, installable, or known fallback candidates. Avoid massive irrelevant dump.
        relevant = job_type in genome.get("job_types", []) or status == "DENIED" or any(job_type in x for x in genome.get("preferred_when", []))
        if relevant or job_type == "general_governed_task":
            candidates.append({
                "tool_id": genome["tool_id"], "display_name": genome.get("display_name", genome["tool_id"]),
                "decision_status": status, "score": score, "reasons": reasons,
                "risk_tier": genome.get("risk_tier"), "requires_approval": bool(genome.get("requires_approval")),
                "install_state": genome.get("install_state"), "competence_score": comp_score,
                "execution_route": genome.get("execution_route"),
                "evidence_refs": genome.get("evidence_refs", []),
                "known_failure_classes": genome.get("known_failure_classes", []),
                "fallbacks": genome.get("fallbacks", []),
                "denied_replacements": genome.get("denied_replacements", [])
            })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    allowed = [c for c in candidates if c["decision_status"] in ["PREFERRED", "ALLOWED", "FALLBACK"]]
    top = allowed[0]["tool_id"] if allowed else None
    scores = [c["score"] for c in allowed]
    spread = (max(scores)-min(scores)) if len(scores) > 1 else 0.0
    min_candidates = 2 if job_type not in ["general_governed_task"] else 1
    coverage = min(1.0, len(candidates)/max(min_candidates,1)) * (1.0 if allowed else 0.0)
    suff_reasons=[]
    if len(candidates) < min_candidates: suff_reasons.append("too few candidates for governed comparison")
    if not allowed: suff_reasons.append("no allowed candidates")
    if len(allowed) > 1 and spread <= 0: suff_reasons.append("allowed candidates have no score spread")
    verdict = "PASS" if not suff_reasons else "FAIL"
    seed = json.dumps({"stage_id": stage_id, "task": task, "job_type": job_type, "top": top, "candidate_count": len(candidates)}, sort_keys=True)
    candidate_set_id = "tool_candidates_" + hashlib.sha256(seed.encode()).hexdigest()[:16]
    return {
        "schema": CANDIDATE_SCHEMA, "candidate_set_id": candidate_set_id, "resolver_version": RESOLVER_VERSION, "created_utc": utc(),
        "stage_id": stage_id, "task": task, "classified_job_type": job_type,
        "source_registries": [str(GENOME_PATH), str(SANDBOX_INVENTORY), str(INSTALL_PROFILE_REGISTRY), str(COMPETENCE)] + forbidden.get("sources", []),
        "top_allowed_tool_id": top, "candidates": candidates,
        "sufficiency": {"verdict": verdict, "candidate_count": len(candidates), "allowed_count": len(allowed), "score_spread": round(spread,3), "coverage_score": round(coverage,3), "reasons": suff_reasons},
        "selection_gate": {"rule": "BTS_TOOL_EVALUATION must cover resolver candidates or explain exclusions; selected tool should be top_allowed_tool_id unless WHY_NOT_BETTER_TOOL justification passes.", "requires_why_not_better_if_selected_not_top": True}
    }

def validate_evaluation(candidate_set: Dict[str, Any], evaluation: Dict[str, Any]) -> Dict[str, Any]:
    candidates = [c for c in candidate_set.get("candidates", []) if c.get("decision_status") != "DENIED"]
    required = {c["tool_id"] for c in candidates[: min(5, len(candidates))]}
    eval_items = evaluation.get("candidates", evaluation.get("tool_evaluation", []))
    covered=set(); exclusions=[]
    for item in eval_items:
        tid = item.get("tool_id") or item.get("tool")
        if tid in required: covered.add(tid)
        if item.get("exclusion_reason"): exclusions.append(tid)
    selected = evaluation.get("selected_tool_id") or next((i.get("tool_id") or i.get("tool") for i in eval_items if str(i.get("verdict", "")).upper() == "SELECTED"), None)
    top = candidate_set.get("top_allowed_tool_id")
    missing = sorted(required - covered)
    why = evaluation.get("why_not_better_tool") or evaluation.get("why_not_top_candidate") or ""
    reasons=[]
    if missing: reasons.append(f"BTS_TOOL_EVALUATION missing resolver candidates: {', '.join(missing)}")
    if selected and top and selected != top and len(str(why).strip()) < 20: reasons.append("selected tool is not top-ranked and lacks sufficient WHY_NOT_BETTER_TOOL justification")
    verdict = "PASS" if not reasons and selected else "FAIL"
    return {"schema":"TOOL_SELECTION_SUFFICIENCY_GATE_RESULT_v1", "timestamp_utc": utc(), "verdict": verdict, "selected_tool_id": selected, "top_allowed_tool_id": top, "covered_candidate_count": len(covered), "required_candidate_count": len(required), "missing_candidates": missing, "reasons": reasons}

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument('--root', default='/mnt/data/Metablooms_OS')
    sub=ap.add_subparsers(dest='cmd', required=True)
    r=sub.add_parser('resolve'); r.add_argument('--task', required=True); r.add_argument('--stage-id', default='STAGE6H'); r.add_argument('--job-type', default=''); r.add_argument('--out')
    v=sub.add_parser('validate-evaluation'); v.add_argument('--candidate-set', required=True); v.add_argument('--evaluation', required=True); v.add_argument('--out')
    args=ap.parse_args(argv); root=resolve_root(args.root)
    if args.cmd == 'resolve':
        out=resolve(args.task, root, args.stage_id, args.job_type)
    else:
        out=validate_evaluation(json.loads(Path(args.candidate_set).read_text()), json.loads(Path(args.evaluation).read_text()))
    s=json.dumps(out, indent=2, sort_keys=True)
    if getattr(args, 'out', None): Path(args.out).parent.mkdir(parents=True, exist_ok=True); Path(args.out).write_text(s+'\n', encoding='utf-8')
    print(s)
    return 0 if out.get('sufficiency', out).get('verdict') == 'PASS' else 1
if __name__ == '__main__': raise SystemExit(main())
