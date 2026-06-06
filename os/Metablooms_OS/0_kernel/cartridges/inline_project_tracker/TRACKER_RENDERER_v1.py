#!/usr/bin/env python3
"""MetaBlooms Inline Project Tracker Markdown renderer v1.

TRACKER-4R mobile reflow repair:
- Uses a compact stacked tracker, not a box/table layout.
- Avoids box-drawing borders, right-side pipes, and fixed-width padded cells.
- Preserves a small visual progress strip only when progress is determinate.
- Fails closed into a compact blocked tracker when state is invalid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

TOP_MARKER = "TRACKER ▸"
MAX_WIDTH = 64
BAR_WIDTH = 6
REQUIRED_FIELDS = [
    "project_name",
    "status",
    "current_stage",
    "progress_mode",
    "completed_stages",
    "now",
    "evidence",
    "blocker",
    "next_allowed_action",
    "stop_rule",
]


def _clean(value: Any) -> str:
    return "" if value is None else str(value).replace("\n", " ").strip()


def _shorten(value: Any, width: int = 46) -> str:
    text = _clean(value)
    if len(text) <= width:
        return text
    return text[: max(0, width - 1)].rstrip() + "…"


def _latest_evidence_label(state: Dict[str, Any]) -> str:
    evidence = state.get("evidence") or []
    if not evidence:
        return "missing"
    latest = evidence[-1]
    label = latest.get("label", "evidence")
    sha = latest.get("sha256", "")
    short = sha[:12] if isinstance(sha, str) and len(sha) >= 12 else "no-sha"
    return _shorten(f"{label} {short}", 46)


def _bar(idx: int, total: int) -> str:
    filled = max(0, min(BAR_WIDTH, round((idx / total) * BAR_WIDTH)))
    return "█" * filled + "░" * (BAR_WIDTH - filled)


def _progress_text(state: Dict[str, Any]) -> str:
    mode = state.get("progress_mode")
    label = state.get("progress_label") or "unknown"
    idx = state.get("stage_index")
    total = state.get("stage_total")
    if mode == "determinate" and isinstance(idx, int) and isinstance(total, int) and total > 0:
        return f"[{_bar(idx, total)}] {idx}/{total} complete"
    return f"indeterminate — {_shorten(label, 30)}"


def validate_state_minimal(state: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if field not in state:
            errors.append(f"missing required field: {field}")
    if state.get("progress_mode") == "determinate":
        if not isinstance(state.get("stage_index"), int) or not isinstance(state.get("stage_total"), int):
            errors.append("determinate progress requires integer stage_index and stage_total")
        elif state["stage_total"] <= 0 or state["stage_index"] < 0 or state["stage_index"] > state["stage_total"]:
            errors.append("determinate progress requires 0 <= stage_index <= stage_total")
    if not isinstance(state.get("evidence"), list) or not state.get("evidence"):
        errors.append("evidence must contain at least one evidence item")
    blocker = state.get("blocker")
    if not isinstance(blocker, dict) or "present" not in blocker or "summary" not in blocker:
        errors.append("blocker must include present and summary")
    return errors


def render_tracker(state: Dict[str, Any]) -> str:
    errors = validate_state_minimal(state)
    if errors:
        state = {
            "project_name": state.get("project_name", "Unknown Project"),
            "status": "FAILED_CLOSED",
            "current_stage": state.get("current_stage", "state validation"),
            "progress_mode": "indeterminate",
            "progress_label": "state invalid",
            "now": "tracker state failed validation",
            "evidence": state.get("evidence", []),
            "blocker": {"present": True, "summary": "; ".join(errors[:2]), "evidence_path": None},
            "next_allowed_action": "repair tracker state before governed work",
            "stop_rule": "stop before governed action",
            "completed_stages": state.get("completed_stages", []),
            "stage_index": None,
            "stage_total": None,
        }
    blocker = state.get("blocker") or {}
    blocker_text = blocker.get("summary") if blocker.get("present") else "none"
    lines = [
        f"{TOP_MARKER} {_shorten(state.get('project_name'), 38)}",
        _progress_text(state),
        f"Status: {_shorten(state.get('status'), 48)}",
        f"Stage: {_shorten(state.get('current_stage'), 47)}",
        f"Now: {_shorten(state.get('now'), 49)}",
        f"Evidence: {_latest_evidence_label(state)}",
        f"Blocker: {_shorten(blocker_text, 46)}",
        f"Next: {_shorten(state.get('next_allowed_action'), 49)}",
        f"Stop: {_shorten(state.get('stop_rule'), 49)}",
    ]
    return "\n".join(lines)


def main(argv: Iterable[str]) -> int:
    args = list(argv)
    if len(args) != 2:
        print("usage: TRACKER_RENDERER_v1.py <TRACKER_STATE_v1.json>", file=sys.stderr)
        return 2
    state_path = Path(args[1])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    print(render_tracker(state))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
