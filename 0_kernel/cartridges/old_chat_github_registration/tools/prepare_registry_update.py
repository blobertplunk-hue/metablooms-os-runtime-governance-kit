#!/usr/bin/env python3
"""Prepare GitHub chat-work registry updates from an old-chat packet and comparison report.

This tool writes a deterministic update bundle only. It does not push, merge, or
promote artifacts. A later GitHub PR/adjudication must review the generated
files.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRY_SCHEMA = "mb.old_chat_github_registration.github_registry_index.v1"
QUEUE_SCHEMA = "mb.old_chat_github_registration.github_promotion_queue_index.v1"
PACKET_SCHEMA = "mb.old_chat_github_registration.work_status_packet.v1"
QUEUE_STATUSES = {
    "READY_FOR_PROMOTION",
    "BLOCKED_MISSING_LOCAL_EVIDENCE",
    "BLOCKED_PATH_SHA_CONFLICT",
    "NEEDS_HUMAN_ADJUDICATION",
    "SMOKE_ONLY_DO_NOT_PROMOTE",
    "SUPERSEDED_DO_NOT_PROMOTE",
}
NO_PROMOTE_RECS = {"SMOKE_ONLY_DO_NOT_PROMOTE", "SUPERSEDED_DO_NOT_PROMOTE", "NO_PROMOTION"}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON object required: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_id(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._-")[:120] or "unknown_chat"


def empty_registry(repo: str) -> dict[str, Any]:
    return {
        "schema": REGISTRY_SCHEMA,
        "updated_at_utc": utc_now(),
        "repo": repo,
        "registered_chat_count": 0,
        "queue_counts": {
            "finished_verified": 0,
            "finished_unverified": 0,
            "in_progress": 0,
            "blocked": 0,
            "superseded": 0,
            "abandoned": 0,
            "ready_for_promotion": 0,
            "blocked_missing_evidence": 0,
            "blocked_conflict": 0,
        },
        "chats": [],
    }


def empty_queue(repo: str) -> dict[str, Any]:
    return {
        "schema": QUEUE_SCHEMA,
        "updated_at_utc": utc_now(),
        "repo": repo,
        "queue_item_count": 0,
        "status_counts": {
            "ready_for_promotion": 0,
            "blocked_missing_evidence": 0,
            "blocked_conflict": 0,
            "needs_adjudication": 0,
            "do_not_promote": 0,
        },
        "items": [],
    }


def load_or_empty(path: Path, empty: dict[str, Any]) -> dict[str, Any]:
    return read_json(path) if path.exists() else empty


def validate_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != PACKET_SCHEMA:
        raise SystemExit("packet schema mismatch")
    if not str(packet.get("chat_url", "")).startswith("https://chatgpt.com/"):
        raise SystemExit("packet chat_url invalid")
    if not packet.get("source_chat_id"):
        raise SystemExit("packet source_chat_id required")
    if packet.get("completion_status") not in {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "COMPLETE_UNVERIFIED", "COMPLETE_VERIFIED", "SUPERSEDED", "ABANDONED"}:
        raise SystemExit("packet completion_status invalid")
    if packet.get("completion_status") == "COMPLETE_VERIFIED" and not packet.get("evidence"):
        raise SystemExit("COMPLETE_VERIFIED requires evidence")


def validate_indexes(registry: dict[str, Any], queue: dict[str, Any]) -> None:
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise SystemExit("registry schema mismatch")
    if queue.get("schema") != QUEUE_SCHEMA:
        raise SystemExit("queue schema mismatch")
    if not isinstance(registry.get("chats"), list):
        raise SystemExit("registry.chats must be a list")
    if not isinstance(queue.get("items"), list):
        raise SystemExit("queue.items must be a list")


def artifact_recommendations(packet: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for artifact in packet.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        rec = str(artifact.get("promotion_recommendation", "NEEDS_HUMAN_ADJUDICATION"))
        for key in (artifact.get("declared_path"), artifact.get("sha256"), artifact.get("label")):
            if key:
                result[str(key)] = rec
    return result


def queue_status(artifact: dict[str, Any], recs: dict[str, str], conflict: bool = False) -> str:
    if conflict:
        return "BLOCKED_PATH_SHA_CONFLICT"
    rec = recs.get(str(artifact.get("declared_path"))) or recs.get(str(artifact.get("sha256"))) or recs.get(str(artifact.get("label")))
    if rec == "SMOKE_ONLY_DO_NOT_PROMOTE":
        return "SMOKE_ONLY_DO_NOT_PROMOTE"
    if rec == "SUPERSEDED_DO_NOT_PROMOTE":
        return "SUPERSEDED_DO_NOT_PROMOTE"
    if rec in NO_PROMOTE_RECS:
        return "NEEDS_HUMAN_ADJUDICATION"
    if artifact.get("local_evidence_path"):
        return "READY_FOR_PROMOTION"
    return "BLOCKED_MISSING_LOCAL_EVIDENCE"


def queue_key(source_chat_id: str, artifact: dict[str, Any], suffix: str = "") -> str:
    return "|".join([source_chat_id, suffix, str(artifact.get("declared_path") or ""), str(artifact.get("sha256") or ""), str(artifact.get("label") or "")])


def recompute_counts(registry: dict[str, Any], queue: dict[str, Any]) -> None:
    chats = registry["chats"]
    items = queue["items"]
    registry["registered_chat_count"] = len(chats)
    qc = {k: 0 for k in registry["queue_counts"]}
    status_map = {
        "COMPLETE_VERIFIED": "finished_verified",
        "COMPLETE_UNVERIFIED": "finished_unverified",
        "IN_PROGRESS": "in_progress",
        "BLOCKED": "blocked",
        "SUPERSEDED": "superseded",
        "ABANDONED": "abandoned",
    }
    for chat in chats:
        mapped = status_map.get(chat.get("completion_status"))
        if mapped:
            qc[mapped] += 1
    for item in items:
        if item.get("status") == "READY_FOR_PROMOTION":
            qc["ready_for_promotion"] += 1
        elif item.get("status") == "BLOCKED_MISSING_LOCAL_EVIDENCE":
            qc["blocked_missing_evidence"] += 1
        elif item.get("status") == "BLOCKED_PATH_SHA_CONFLICT":
            qc["blocked_conflict"] += 1
    registry["queue_counts"] = qc
    queue["queue_item_count"] = len(items)
    sc = {k: 0 for k in queue["status_counts"]}
    for item in items:
        status = item.get("status")
        if status == "READY_FOR_PROMOTION":
            sc["ready_for_promotion"] += 1
        elif status == "BLOCKED_MISSING_LOCAL_EVIDENCE":
            sc["blocked_missing_evidence"] += 1
        elif status == "BLOCKED_PATH_SHA_CONFLICT":
            sc["blocked_conflict"] += 1
        elif status == "NEEDS_HUMAN_ADJUDICATION":
            sc["needs_adjudication"] += 1
        elif status in {"SMOKE_ONLY_DO_NOT_PROMOTE", "SUPERSEDED_DO_NOT_PROMOTE"}:
            sc["do_not_promote"] += 1
    queue["status_counts"] = sc


def prepare(packet: dict[str, Any], report: dict[str, Any], registry: dict[str, Any], queue: dict[str, Any], repo: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    validate_packet(packet)
    validate_indexes(registry, queue)
    source_chat_id = str(packet["source_chat_id"])
    sid = safe_id(source_chat_id)
    chat_url = str(packet["chat_url"])
    for chat in registry["chats"]:
        if chat.get("chat_url") == chat_url and chat.get("source_chat_id") != source_chat_id:
            raise SystemExit("duplicate chat_url conflicts with different source_chat_id")
    packet_path = f"governance/chat_work_registry/chat_packets/{sid}.json"
    report_path = f"governance/chat_work_registry/reports/{sid}.comparison_report.json"
    row = {
        "chat_url": chat_url,
        "source_chat_id": source_chat_id,
        "registered_at_utc": packet.get("registered_at_utc", utc_now()),
        "last_seen_at_utc": utc_now(),
        "work_summary": packet.get("work_summary", ""),
        "completion_status": packet.get("completion_status", "COMPLETE_UNVERIFIED"),
        "done_count": len(packet.get("done_work", [])),
        "unfinished_count": len(packet.get("current_work", [])),
        "blocked_count": len(packet.get("blockers", [])),
        "ready_for_promotion_count": 0,
        "packet_path": packet_path,
        "report_path": report_path,
    }
    registry["chats"] = [c for c in registry["chats"] if c.get("source_chat_id") != source_chat_id] + [row]
    existing = {item.get("key") for item in queue["items"]}
    recs = artifact_recommendations(packet)
    added_ready = added_blocked = 0
    for artifact in report.get("unshared", []):
        if not isinstance(artifact, dict):
            continue
        key = queue_key(source_chat_id, artifact)
        if key in existing:
            continue
        status = queue_status(artifact, recs)
        item = {
            "key": key,
            "chat_url": chat_url,
            "source_chat_id": source_chat_id,
            "label": str(artifact.get("label", "")),
            "declared_path": artifact.get("declared_path"),
            "sha256": artifact.get("sha256"),
            "status": status,
            "created_at_utc": utc_now(),
            "packet_path": packet_path,
            "report_path": report_path,
        }
        queue["items"].append(item)
        existing.add(key)
        if status == "READY_FOR_PROMOTION":
            row["ready_for_promotion_count"] += 1
            added_ready += 1
        else:
            added_blocked += 1
    for artifact in report.get("conflicts", []):
        if not isinstance(artifact, dict):
            continue
        key = queue_key(source_chat_id, artifact, "conflict")
        if key in existing:
            continue
        queue["items"].append({
            "key": key,
            "chat_url": chat_url,
            "source_chat_id": source_chat_id,
            "label": str(artifact.get("label", "")),
            "declared_path": artifact.get("declared_path"),
            "sha256": artifact.get("sha256"),
            "status": "BLOCKED_PATH_SHA_CONFLICT",
            "created_at_utc": utc_now(),
            "packet_path": packet_path,
            "report_path": report_path,
        })
        added_blocked += 1
    registry["repo"] = repo
    queue["repo"] = repo
    registry["updated_at_utc"] = utc_now()
    queue["updated_at_utc"] = utc_now()
    recompute_counts(registry, queue)
    receipt = {
        "schema": "mb.old_chat_github_registration.registry_update_receipt.v1",
        "decision": "PASS_PREPARED_REGISTRY_UPDATE",
        "packet_path": packet_path,
        "report_path": report_path,
        "registered_chat_count": registry["registered_chat_count"],
        "queue_item_count": queue["queue_item_count"],
        "queue_added_ready": added_ready,
        "queue_added_blocked": added_blocked,
    }
    return registry, queue, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--repo", default="blobertplunk-hue/metablooms-os-runtime-governance-kit")
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    packet = read_json(args.packet)
    report = read_json(args.report)
    registry = load_or_empty(args.registry, empty_registry(args.repo))
    queue = load_or_empty(args.queue, empty_queue(args.repo))
    registry, queue, receipt = prepare(packet, report, registry, queue, args.repo)
    write_json(args.out_dir / "governance/chat_work_registry/registered_chats.index.json", registry)
    write_json(args.out_dir / "governance/chat_work_registry/promotion_queue.index.json", queue)
    write_json(args.out_dir / receipt["packet_path"], packet)
    write_json(args.out_dir / receipt["report_path"], report)
    write_json(args.out_dir / "registry_update_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
