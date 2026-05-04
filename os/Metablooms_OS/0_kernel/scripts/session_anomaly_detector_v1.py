#!/usr/bin/env python3
### GOVERNANCE HEADER
# artifact_id: session_anomaly_detector_v1
# purpose: Compare current CLAUDE_MEMORY_SYNC against last N sessions in
#          history ledger. Flags unexpected baseline SHA changes, amendment
#          count drops, silently cleared blockers, or stage regression.
#          Stronger than per-file validation — detects patterns across time.
# mutation_scope: read-only (writes anomaly report only)
# owasp_risk_addressed: ASI06 Memory & Context Poisoning + ASI01 Agent Goal Hijack
###

from __future__ import annotations

import hashlib, json, os, time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VERSION = "1.0"

DEFAULT_SYNC = Path("/mnt/data/CLAUDE_MEMORY_SYNC_v1.json")
DEFAULT_HISTORY = Path("/mnt/data/CLAUDE_MEMORY_SYNC_HISTORY_v1.jsonl")
DEFAULT_REPORT_DIR = Path("/mnt/data/Metablooms_OS_refined/0_kernel/registry/anomaly_reports")

HISTORY_WINDOW = 5  # compare against last N sessions


class AnomalySeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


@dataclass
class Anomaly:
    anomaly_id: str
    severity: AnomalySeverity
    description: str
    evidence: str = ""
    recommendation: str = ""

    def to_dict(self):
        return {k: (v.value if isinstance(v, AnomalySeverity) else v)
                for k, v in self.__dict__.items()}


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_history(history_path: Path, window: int = HISTORY_WINDOW) -> List[Dict]:
    if not history_path.exists():
        return []
    lines = [l for l in history_path.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
    entries = []
    for line in lines[-window:]:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries


def write_json_atomic(path: Path, data: Dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    _mb_write_json_file(tmp, data, operation_id='STAGE4_ATOMIC_JSON_0_kernel_scripts_session_anomaly_detector_v1_py_L74', create_parent=True, allowed_roots=[str(_MBAJWPath('/mnt/data').resolve())], indent=2, sort_keys=False, ensure_ascii=True, max_bytes=20000000)
    os.replace(tmp, path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_anomalies(sync: Dict, history: List[Dict]) -> List[Anomaly]:
    anomalies: List[Anomaly] = []

    if not history:
        return [Anomaly(
            "SAD_NO_HISTORY", AnomalySeverity.LOW,
            "No history available — this is a first-run or fresh environment",
            recommendation="No action needed; anomaly detection will activate after first successful sync",
        )]

    last = history[-1]
    all_history = history

    # --- 1. Baseline SHA sequence analysis ---
    sha_seq = [h.get("baseline_sha_prefix", "") for h in all_history if h.get("baseline_sha_prefix")]
    current_sha = str(sync.get("baseline_sha", ""))[:16]

    if sha_seq and current_sha:
        # Count unique SHAs in window
        unique_shas = set(sha_seq + [current_sha])
        if len(unique_shas) > 3:
            anomalies.append(Anomaly(
                "SAD_SHA_VOLATILITY", AnomalySeverity.HIGH,
                f"Baseline SHA changed {len(unique_shas)} distinct values in last {len(sha_seq)+1} sessions",
                evidence=f"SHAs seen: {list(unique_shas)}",
                recommendation="Verify each baseline SHA change was intentional (deployment vs unexpected)",
            ))

    # --- 2. Amendment count trend ---
    amend_counts = [h.get("amendment_count", 0) for h in all_history]
    current_count = len(sync.get("active_amendments", []))

    if amend_counts:
        max_historical = max(amend_counts)
        if current_count < max_historical:
            drop = max_historical - current_count
            sev = AnomalySeverity.CRITICAL if drop > 3 else AnomalySeverity.HIGH if drop > 1 else AnomalySeverity.MEDIUM
            anomalies.append(Anomaly(
                "SAD_AMENDMENT_REGRESSION",
                sev,
                f"Amendment count dropped from historical max {max_historical} to current {current_count}",
                evidence=f"History counts: {amend_counts} → current: {current_count}",
                recommendation="Check whether amendments were intentionally removed or lost during session",
            ))

    # --- 3. Known blocker silently cleared ---
    last_blockers = set(last.get("known_blockers_preview", []))
    current_blockers = set(
        b[:50] for b in sync.get("known_blockers", [])
    )
    # Check if last had blockers that are gone now without a matching next_chunk item
    if last_blockers and not current_blockers:
        next_chunk = set(c.lower() for c in sync.get("next_chunk", []))
        # Some may have been intentionally resolved
        anomalies.append(Anomaly(
            "SAD_BLOCKERS_CLEARED", AnomalySeverity.MEDIUM,
            "All known_blockers were cleared between sessions — verify each was intentionally resolved",
            evidence=f"Previous blockers: {list(last_blockers)[:3]}",
            recommendation="Confirm each blocker was resolved with a receipt, not silently dropped",
        ))

    # --- 4. Stage regression ---
    current_stage = sync.get("current_stage", "")
    last_stage = last.get("current_stage", "")
    if last_stage and current_stage:
        # Look for explicit backwards movement keywords
        regress_signals = ["retry", "rollback", "revert", "undo", "repair", "restart"]
        if any(sig in current_stage.lower() for sig in regress_signals):
            anomalies.append(Anomaly(
                "SAD_STAGE_REGRESSION", AnomalySeverity.MEDIUM,
                f"Current stage suggests regression: '{current_stage}'",
                evidence=f"Previous stage: '{last_stage}'",
                recommendation="Verify whether this is an intentional repair pass or unexpected rollback",
            ))

    # --- 5. Session note entropy (sudden length drop) ---
    note_lens = [h.get("session_note_words", 0) for h in all_history]
    current_note_len = len(sync.get("session_note", "").split())
    if note_lens:
        avg_len = sum(note_lens) / len(note_lens)
        if avg_len > 5 and current_note_len < avg_len * 0.2:
            anomalies.append(Anomaly(
                "SAD_NOTE_ENTROPY_DROP", AnomalySeverity.MEDIUM,
                f"Session note length dropped from avg {avg_len:.0f} to {current_note_len} words",
                evidence="May indicate truncated or placeholder sync",
                recommendation="Ensure session_note accurately reflects what was done this session",
            ))

    # --- 6. Composite risk score ---
    severity_weights = {
        AnomalySeverity.CRITICAL: 1.0,
        AnomalySeverity.HIGH: 0.6,
        AnomalySeverity.MEDIUM: 0.3,
        AnomalySeverity.LOW: 0.1,
    }
    risk_score = sum(severity_weights[a.severity] for a in anomalies)
    if risk_score >= 1.5:
        anomalies.append(Anomaly(
            "SAD_COMPOSITE_RISK", AnomalySeverity.CRITICAL,
            f"Composite risk score {risk_score:.1f} exceeds threshold 1.5 — multiple anomalies detected",
            evidence=f"Anomaly count: {len(anomalies)-1}  Score: {risk_score:.1f}",
            recommendation="Do not load this sync into Claude memory without manual review of all anomalies",
        ))

    return anomalies


def run_detection(
    sync_path: Path,
    history_path: Path,
    report_dir: Path,
    window: int = HISTORY_WINDOW,
) -> Dict:
    sync = load_json(sync_path)
    if sync is None:
        return {
            "verdict": "ERROR",
            "error": f"Cannot read sync file: {sync_path}",
        }

    history = load_history(history_path, window)
    anomalies = detect_anomalies(sync, history)

    criticals = [a for a in anomalies if a.severity == AnomalySeverity.CRITICAL]
    highs     = [a for a in anomalies if a.severity == AnomalySeverity.HIGH]
    mediums   = [a for a in anomalies if a.severity == AnomalySeverity.MEDIUM]

    verdict = (
        "CRITICAL" if criticals else
        "HIGH"     if highs     else
        "MEDIUM"   if mediums   else
        "CLEAN"
    )

    report = {
        "report_type": "SESSION_ANOMALY_DETECTION_REPORT",
        "detector_version": VERSION,
        "created_at": time.time(),
        "sync_path": str(sync_path),
        "history_window": window,
        "history_entries_analyzed": len(history),
        "verdict": verdict,
        "anomaly_count": len(anomalies),
        "criticals": len(criticals),
        "highs": len(highs),
        "mediums": len(mediums),
        "anomalies": [a.to_dict() for a in anomalies],
        "load_recommendation": (
            "SAFE — no significant anomalies detected"
            if verdict == "CLEAN"
            else "REVIEW RECOMMENDED — anomalies detected but may be intentional"
            if verdict in ("MEDIUM",)
            else "MANUAL REVIEW REQUIRED before loading into Claude memory"
        ),
    }

    ts = int(time.time() * 1000)
    rpath = report_dir / f"ANOMALY_REPORT_{ts}.json"
    rsha = write_json_atomic(rpath, report)
    report["report_path"] = str(rpath)
    report["report_sha"] = rsha

    # Console
    icon = {"CLEAN": "✓", "MEDIUM": "⚠", "HIGH": "⚠", "CRITICAL": "✗"}[verdict]
    print(f"  [{icon}] Anomaly detector: {verdict}  anomalies={len(anomalies)}")
    for a in anomalies[:5]:
        print(f"    [{a.severity}] {a.anomaly_id}: {a.description[:70]}")

    return report


def main(argv=None):
    import argparse, sys
    ap = argparse.ArgumentParser(description="MetaBlooms Session Anomaly Detector v1")
    ap.add_argument("--sync",       default=str(DEFAULT_SYNC))
    ap.add_argument("--history",    default=str(DEFAULT_HISTORY))
    ap.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    ap.add_argument("--window",     type=int, default=HISTORY_WINDOW)
    ap.add_argument("--json-output", action="store_true")
    args = ap.parse_args(argv)

    result = run_detection(
        sync_path=Path(args.sync),
        history_path=Path(args.history),
        report_dir=Path(args.report_dir),
        window=args.window,
    )
    if args.json_output:
        print(json.dumps(result, indent=2))
    verdict = result.get("verdict", "ERROR")
    sys.exit(0 if verdict in ("CLEAN", "MEDIUM") else 1)


if __name__ == "__main__":
    main()
