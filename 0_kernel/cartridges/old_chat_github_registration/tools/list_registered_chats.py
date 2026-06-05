#!/usr/bin/env python3
"""List old-chat registrations from a GitHub-resident registry index."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REGISTRY_SCHEMA = "mb.old_chat_github_registration.github_registry_index.v1"
STATUS_KEYS = [
    "finished_verified",
    "finished_unverified",
    "in_progress",
    "blocked",
    "superseded",
    "abandoned",
    "ready_for_promotion",
    "blocked_missing_evidence",
    "blocked_conflict",
]


def load_registry(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("registry must be a JSON object")
    return data


def validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("schema") != REGISTRY_SCHEMA:
        errors.append(f"schema must be {REGISTRY_SCHEMA}")
    chats = registry.get("chats")
    if not isinstance(chats, list):
        errors.append("chats must be a list")
        chats = []
    if registry.get("registered_chat_count") != len(chats):
        errors.append("registered_chat_count does not match chats length")
    queue_counts = registry.get("queue_counts")
    if not isinstance(queue_counts, dict):
        errors.append("queue_counts must be an object")
        queue_counts = {}
    for key in STATUS_KEYS:
        if not isinstance(queue_counts.get(key), int) or queue_counts.get(key, -1) < 0:
            errors.append(f"queue_counts.{key} must be a nonnegative integer")
    seen_urls: set[str] = set()
    seen_ids: set[str] = set()
    for idx, chat in enumerate(chats):
        if not isinstance(chat, dict):
            errors.append(f"chats[{idx}] must be an object")
            continue
        url = chat.get("chat_url")
        sid = chat.get("source_chat_id")
        if not isinstance(url, str) or not url.startswith("https://chatgpt.com/"):
            errors.append(f"chats[{idx}].chat_url invalid")
        elif url in seen_urls:
            errors.append(f"duplicate chat_url: {url}")
        else:
            seen_urls.add(url)
        if not isinstance(sid, str) or not sid:
            errors.append(f"chats[{idx}].source_chat_id required")
        elif sid in seen_ids:
            errors.append(f"duplicate source_chat_id: {sid}")
        else:
            seen_ids.add(sid)
    return errors


def compute_summary(registry: dict[str, Any]) -> dict[str, int]:
    chats = registry.get("chats", [])
    summary = {
        "registered_chats": len(chats),
        "finished_verified": 0,
        "finished_unverified": 0,
        "in_progress": 0,
        "blocked": 0,
        "superseded": 0,
        "abandoned": 0,
    }
    for chat in chats:
        status = chat.get("completion_status")
        if status == "COMPLETE_VERIFIED":
            summary["finished_verified"] += 1
        elif status == "COMPLETE_UNVERIFIED":
            summary["finished_unverified"] += 1
        elif status == "IN_PROGRESS":
            summary["in_progress"] += 1
        elif status == "BLOCKED":
            summary["blocked"] += 1
        elif status == "SUPERSEDED":
            summary["superseded"] += 1
        elif status == "ABANDONED":
            summary["abandoned"] += 1
    return summary


def active_rows(chats: list[dict[str, Any]], active_only: bool) -> list[dict[str, Any]]:
    if not active_only:
        return chats
    return [chat for chat in chats if chat.get("completion_status") not in {"SUPERSEDED", "ABANDONED"}]


def render_markdown(registry: dict[str, Any], active_only: bool = False) -> str:
    summary = compute_summary(registry)
    rows = active_rows(registry.get("chats", []), active_only)
    out = [
        f"Registered chats: {summary['registered_chats']}",
        "",
        f"Finished verified: {summary['finished_verified']}",
        f"Finished unverified: {summary['finished_unverified']}",
        f"In progress: {summary['in_progress']}",
        f"Blocked: {summary['blocked']}",
        f"Superseded: {summary['superseded']}",
        f"Abandoned: {summary['abandoned']}",
        "",
        "| Chat | Status | Done | Unfinished | Blocked | Ready for promotion | Last seen |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for chat in rows:
        out.append(
            "| {sid} | {status} | {done} | {unfinished} | {blocked} | {ready} | {last_seen} |".format(
                sid=chat.get("source_chat_id", ""),
                status=chat.get("completion_status", ""),
                done=chat.get("done_count", 0),
                unfinished=chat.get("unfinished_count", 0),
                blocked=chat.get("blocked_count", 0),
                ready=chat.get("ready_for_promotion_count", 0),
                last_seen=chat.get("last_seen_at_utc", ""),
            )
        )
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--active-only", action="store_true")
    args = parser.parse_args()
    registry = load_registry(args.registry)
    errors = validate_registry(registry)
    if errors:
        print(json.dumps({"decision": "FAIL_BAD_REGISTRY", "errors": errors}, indent=2, sort_keys=True))
        return 2
    summary = compute_summary(registry)
    if args.format == "json":
        payload = {"schema": "mb.old_chat_github_registration.listing.v1", "summary": summary, "chats": active_rows(registry.get("chats", []), args.active_only)}
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_markdown(registry, args.active_only), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
