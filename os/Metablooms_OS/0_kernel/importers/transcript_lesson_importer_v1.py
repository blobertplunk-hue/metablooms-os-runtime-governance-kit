#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

HARD_FLAG_PATTERNS = [
    (re.compile(r"\b(pc only|must use pc|requires pc|can't work in sandbox)\b", re.I), "pc_only_blocks_sandbox_primary"),
    (re.compile(r"\b(claim browser proof|pretend|fake|overclaim)\b", re.I), "evidence_tier_overclaim"),
    (re.compile(r"\b(remove|disable|skip)\b.*\b(gate|validator|fixture|proof)\b", re.I), "removes_existing_gate"),
    (re.compile(r"\b(no fixture|without fixture|no test|without test)\b", re.I), "no_fixture_for_recurring_claim"),
    (re.compile(r"\bunsafe|policy invalid|bypass policy\b", re.I), "unsafe_or_policy_invalid"),
]

LESSON_PATTERNS = [
    (re.compile(r"\b(should|need to|must|from now on|next time|always|never|prefer|default)\b", re.I), "directive"),
    (re.compile(r"\b(failed|blocked|stuck|bug|regression|false positive|timeout|hung|missing)\b", re.I), "failure"),
    (re.compile(r"\b(transcript|old chat|previous chat|conversation)\b", re.I), "transcript"),
    (re.compile(r"\b(sandbox|android|phone|/mnt/data)\b", re.I), "sandbox"),
    (re.compile(r"\b(html|visual|tracker|dashboard|browser|render|screenshot)\b", re.I), "visual_browser"),
]

MODULE_MAP = {
    "visual_browser": ["VISUAL_PRESENTATION_QUALITY_GATE", "BROWSER_RENDER_CAPABILITY_RESOLVER"],
    "sandbox": ["BROWSER_RENDER_CAPABILITY_RESOLVER"],
    "failure": ["WORKFLOW_GENERALIZATION_ENGINE"],
    "transcript": ["TRANSCRIPT_LESSON_IMPORT_GATE", "WORKFLOW_GENERALIZATION_ENGINE"],
    "directive": ["WORKFLOW_GENERALIZATION_ENGINE"],
}

CURRENT_BASELINE = {
    "reliability": 3,
    "sandbox_fit": 4,
    "automation": 3,
    "honesty": 4,
    "artifactization": 3,
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()

def split_lines(text: str):
    return [normalize_line(x) for x in text.splitlines() if normalize_line(x)]

def classify_lines(lines):
    hits = []
    for idx, line in enumerate(lines):
        tags = []
        for regex, tag in LESSON_PATTERNS:
            if regex.search(line):
                tags.append(tag)
        if tags:
            hits.append({"line": idx + 1, "text": line[:500], "tags": sorted(set(tags))})
    return hits

def derive_modules(tags):
    mods = []
    for tag in tags:
        for mod in MODULE_MAP.get(tag, []):
            if mod not in mods:
                mods.append(mod)
    if not mods:
        mods.append("WORKFLOW_GENERALIZATION_ENGINE")
    return mods

def detect_flags(text: str):
    flags = []
    for regex, flag in HARD_FLAG_PATTERNS:
        if regex.search(text):
            flags.append(flag)
    return sorted(set(flags))

def evidence_strength(hits, text: str) -> float:
    if not hits:
        return 0.0
    tag_count = len({tag for h in hits for tag in h["tags"]})
    directiveness = sum(1 for h in hits if "directive" in h["tags"])
    failures = sum(1 for h in hits if "failure" in h["tags"])
    artifact_terms = re.findall(r"\b(schema|validator|fixture|receipt|ledger|router|gate|export|artifact|resolver|policy)\b", text, re.I)
    sandbox_terms = re.findall(r"\b(sandbox|android|phone|/mnt/data|weasyprint|chromium|playwright)\b", text, re.I)
    directive_terms = re.findall(r"\b(should|need to|must|from now on|next time|always|never|prefer|default|automatically)\b", text, re.I)
    # Dense chat-transcript lessons often arrive as one long paragraph. Score internal evidence density, not only line count.
    score = (
        0.20
        + min(0.20, len(hits) * 0.04)
        + min(0.20, tag_count * 0.04)
        + min(0.15, directiveness * 0.03 + len(directive_terms) * 0.02)
        + min(0.10, failures * 0.03)
        + min(0.20, len(artifact_terms) * 0.025)
        + min(0.10, len(sandbox_terms) * 0.025)
    )
    return round(min(score, 1.0), 2)

def make_candidate(transcript_path: Path, text: str):
    lines = split_lines(text)
    hits = classify_lines(lines)
    all_tags = sorted({tag for h in hits for tag in h["tags"]})
    flags = detect_flags(text)
    strength = evidence_strength(hits, text)
    modules = derive_modules(all_tags)
    sample = "; ".join(h["text"] for h in hits[:3]) or "No reusable lesson evidence found."
    positive_delta = strength >= 0.55 and not flags
    candidate_scores = dict(CURRENT_BASELINE)
    if positive_delta:
        candidate_scores = {"reliability": 5, "sandbox_fit": 5 if "sandbox" in all_tags else 4, "automation": 5, "honesty": 5, "artifactization": 5}
    elif strength > 0:
        candidate_scores = {"reliability": 3, "sandbox_fit": 3, "automation": 3, "honesty": 3, "artifactization": 2}
    lesson_id = "transcript_candidate_" + hashlib.sha256((transcript_path.name + text[:1000]).encode("utf-8", "ignore")).hexdigest()[:12]
    return {
        "lesson_id": lesson_id,
        "source": {"type": "transcript_import", "path": str(transcript_path), "sha256": sha256_file(transcript_path)},
        "evidence": {"summary": sample, "strength": strength, "excerpt_count": len(hits), "tags": all_tags, "excerpts": hits[:8]},
        "baseline_comparison": {
            "current_behavior": "Use current OS routing, gates, resolvers, ledgers, fixtures, and sandbox-first defaults.",
            "proposed_behavior": "Adopt transcript-derived workflow lesson only if it improves current behavior and can be artifactized.",
            "score_current": CURRENT_BASELINE,
            "score_candidate": candidate_scores,
            "regression_flags": flags
        },
        "auto_include": modules,
        "artifactization": {"required": True, "minimum_artifacts": ["ledger_event", "router_candidate", "fixture_or_receipt"], "candidate_kind": "transcript_lesson"},
        "import_decision_hint": "eligible_for_router_comparison" if positive_delta else ("reject_due_to_hard_flags" if flags else "defer_or_reject_unless_router_scores_higher")
    }

def append_ledger(ledger_path: Path, candidate: dict, router_decision: dict | None = None):
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    else:
        ledger = {"schema_version": "1.0", "artifact_id": "WORKFLOW_TRANSCRIPT_IMPORT_LEDGER_v1", "events": []}
    event = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "lesson_id": candidate["lesson_id"],
        "source_sha256": candidate["source"]["sha256"],
        "evidence_strength": candidate["evidence"]["strength"],
        "tags": candidate["evidence"].get("tags", []),
        "regression_flags": candidate["baseline_comparison"].get("regression_flags", []),
        "router_decision": router_decision or {},
        "status": "candidate_logged"
    }
    ledger.setdefault("events", []).append(event)
    ledger["updated_utc"] = event["timestamp_utc"]
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ledger")
    args = ap.parse_args()
    transcript_path = Path(args.transcript)
    text = transcript_path.read_text(encoding="utf-8", errors="replace")
    candidate = make_candidate(transcript_path, text)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"candidates": [candidate]}, indent=2) + "\n", encoding="utf-8")
    if args.ledger:
        append_ledger(Path(args.ledger), candidate)
    print(json.dumps({"candidate_count": 1, "lesson_id": candidate["lesson_id"], "strength": candidate["evidence"]["strength"], "flags": candidate["baseline_comparison"]["regression_flags"]}, indent=2))

if __name__ == "__main__":
    main()
