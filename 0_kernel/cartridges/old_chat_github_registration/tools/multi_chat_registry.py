#!/usr/bin/env python3
"""Maintain a multi-chat URL registry and promotion queue for old-chat registration reports."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRY_SCHEMA = "mb.old_chat_github_registration.registry.v1"
QUEUE_SCHEMA = "mb.old_chat_github_registration.promotion_queue.v1"
REPORT_SCHEMA = "mb.old_chat_github_registration.report.v1"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        if default is None:
            raise SystemExit(f"missing json: {path}")
        return default
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"json object required: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def empty_registry() -> dict[str, Any]:
    return {"schema": REGISTRY_SCHEMA, "updated_at_utc": now_utc(), "chats": []}


def empty_queue() -> dict[str, Any]:
    return {"schema": QUEUE_SCHEMA, "updated_at_utc": now_utc(), "items": []}


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("schema") != REPORT_SCHEMA:
        errors.append(f"report.schema must be {REPORT_SCHEMA}")
    if not isinstance(report.get("chat_url"), str) or not report["chat_url"].startswith("https://chatgpt.com/"):
        errors.append("report.chat_url must start with https://chatgpt.com/")
    if not isinstance(report.get("source_chat_id"), str) or not report["source_chat_id"]:
        errors.append("report.source_chat_id is required")
    for key in ("artifacts", "unshared", "missing_local_evidence", "conflicts"):
        if not isinstance(report.get(key), list):
            errors.append(f"report.{key} must be a list")
    return errors


def normalize_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("schema") != REGISTRY_SCHEMA:
        raise SystemExit(f"registry.schema must be {REGISTRY_SCHEMA}")
    if not isinstance(registry.get("chats"), list):
        raise SystemExit("registry.chats must be a list")
    return registry


def normalize_queue(queue: dict[str, Any]) -> dict[str, Any]:
    if queue.get("schema") != QUEUE_SCHEMA:
        raise SystemExit(f"queue.schema must be {QUEUE_SCHEMA}")
    if not isinstance(queue.get("items"), list):
        raise SystemExit("queue.items must be a list")
    return queue


def artifact_key(chat_url: str, artifact: dict[str, Any]) -> str:
    return "|".join([
        chat_url,
        str(artifact.get("declared_path") or ""),
        str(artifact.get("sha256") or ""),
        str(artifact.get("label") or ""),
    ])


def ingest(registry: dict[str, Any], queue: dict[str, Any], report: dict[str, Any], report_path: str | None = None) -> dict[str, Any]:
    errors = validate_report(report)
    if errors:
        return {"decision": "FAIL_REPORT_VALIDATION", "errors": errors, "registry": registry, "queue": queue}

    chat_url = report["chat_url"]
    source_chat_id = report["source_chat_id"]
    existing = [chat for chat in registry["chats"] if chat.get("chat_url") == chat_url]
    duplicate = bool(existing)
    status = "DUPLICATE_URL_REINGESTED" if duplicate else "REGISTERED"

    if duplicate:
        existing[0].setdefault("report_paths", [])
        if report_path and report_path not in existing[0]["report_paths"]:
            existing[0]["report_paths"].append(report_path)
        existing[0]["last_seen_at_utc"] = now_utc()
        existing[0]["last_decision"] = report.get("decision")
    else:
        registry["chats"].append({
            "chat_url": chat_url,
            "source_chat_id": source_chat_id,
            "registered_at_utc": now_utc(),
            "last_seen_at_utc": now_utc(),
            "last_decision": report.get("decision"),
            "report_paths": [report_path] if report_path else [],
        })

    existing_queue_keys = {item.get("key") for item in queue["items"]}
    added_ready = 0
    added_blocked = 0
    missing_evidence_keys = {artifact_key(chat_url, a) for a in report.get("missing_local_evidence", []) if isinstance(a, dict)}

    for artifact in report.get("unshared", []):
        if not isinstance(artifact, dict):
            continue
        key = artifact_key(chat_url, artifact)
        if key in existing_queue_keys:
            continue
        queue_status = "BLOCKED_MISSING_LOCAL_EVIDENCE" if key in missing_evidence_keys else "READY_FOR_PROMOTION"
        queue["items"].append({
            "key": key,
            "chat_url": chat_url,
            "source_chat_id": source_chat_id,
            "label": artifact.get("label"),
            "declared_path": artifact.get("declared_path"),
            "sha256": artifact.get("sha256"),
            "local_evidence_path": artifact.get("local_evidence_path"),
            "status": queue_status,
            "created_at_utc": now_utc(),
            "report_path": report_path,
        })
        existing_queue_keys.add(key)
        if queue_status == "READY_FOR_PROMOTION":
            added_ready += 1
        else:
            added_blocked += 1

    for artifact in report.get("conflicts", []):
        if not isinstance(artifact, dict):
            continue
        key = artifact_key(chat_url, artifact) + "|conflict"
        if key in existing_queue_keys:
            continue
        queue["items"].append({
            "key": key,
            "chat_url": chat_url,
            "source_chat_id": source_chat_id,
            "label": artifact.get("label"),
            "declared_path": artifact.get("declared_path"),
            "sha256": artifact.get("sha256"),
            "status": "BLOCKED_PATH_SHA_CONFLICT",
            "created_at_utc": now_utc(),
            "report_path": report_path,
        })
        added_blocked += 1

    registry["updated_at_utc"] = now_utc()
    queue["updated_at_utc"] = now_utc()
    return {
        "decision": "WARN_DUPLICATE_CHAT_URL" if duplicate else "PASS_INGESTED",
        "chat_status": status,
        "chat_url": chat_url,
        "queue_added_ready": added_ready,
        "queue_added_blocked": added_blocked,
        "registry_count": len(registry["chats"]),
        "queue_count": len(queue["items"]),
        "registry": registry,
        "queue": queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--out-registry", required=True, type=Path)
    parser.add_argument("--out-queue", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    registry = normalize_registry(load_json(args.registry, empty_registry()))
    queue = normalize_queue(load_json(args.queue, empty_queue()))
    report = load_json(args.report)
    result = ingest(registry, queue, report, str(args.report))
    write_json(args.out_registry, result["registry"])
    write_json(args.out_queue, result["queue"])
    receipt = {k: v for k, v in result.items() if k not in {"registry", "queue"}}
    write_json(args.receipt, receipt)
    return 0 if not result["decision"].startswith("FAIL") else 2


if __name__ == "__main__":
    raise SystemExit(main())
