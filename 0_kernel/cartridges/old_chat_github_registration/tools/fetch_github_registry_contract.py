#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REGISTRY_REQUIRED = ["schema", "updated_at_utc", "repo", "registered_chat_count", "queue_counts", "chats"]
QUEUE_REQUIRED = ["schema", "updated_at_utc", "repo", "queue_item_count", "status_counts", "items"]
REGISTRY_COUNT_KEYS = ["finished_verified", "finished_unverified", "in_progress", "blocked", "superseded", "abandoned", "ready_for_promotion", "blocked_missing_evidence", "blocked_conflict"]
QUEUE_COUNT_KEYS = ["ready_for_promotion", "blocked_missing_evidence", "blocked_conflict", "needs_adjudication", "do_not_promote"]
CHAT_REQUIRED = ["chat_url", "source_chat_id", "registered_at_utc", "last_seen_at_utc", "work_summary", "completion_status", "done_count", "unfinished_count", "blocked_count", "ready_for_promotion_count", "packet_path", "report_path"]
QUEUE_ITEM_REQUIRED = ["key", "chat_url", "source_chat_id", "label", "status", "created_at_utc"]


def read_json(path, missing_code):
    if not path.exists():
        return None, [missing_code]
    try:
        value = json.loads(path.read_text())
    except Exception as exc:
        return None, ["BAD_JSON:" + str(exc)]
    if not isinstance(value, dict):
        return None, ["NOT_OBJECT"]
    return value, []


def require_keys(value, keys, prefix):
    return [prefix + "_MISSING_" + key for key in keys if key not in value]


def count_object_errors(value, key, required_keys, prefix):
    errors = []
    obj = value.get(key)
    if not isinstance(obj, dict):
        return [prefix + "_BAD_" + key.upper()]
    for required in required_keys:
        if not isinstance(obj.get(required), int) or obj.get(required) < 0:
            errors.append(prefix + "_BAD_COUNT_" + required)
    return errors


def registry_errors(value):
    errors = require_keys(value, REGISTRY_REQUIRED, "REGISTRY")
    if value.get("schema") != "mb.old_chat_github_registration.github_registry_index.v1":
        errors.append("BAD_REGISTRY_SCHEMA")
    if not isinstance(value.get("updated_at_utc"), str) or not value.get("updated_at_utc"):
        errors.append("BAD_REGISTRY_UPDATED_AT")
    if not isinstance(value.get("repo"), str) or not value.get("repo"):
        errors.append("BAD_REGISTRY_REPO")
    errors += count_object_errors(value, "queue_counts", REGISTRY_COUNT_KEYS, "REGISTRY")
    chats = value.get("chats")
    if not isinstance(chats, list):
        return errors + ["BAD_REGISTRY_CHATS"]
    if value.get("registered_chat_count") != len(chats):
        errors.append("BAD_REGISTRY_COUNT")
    seen_urls = set()
    seen_ids = set()
    for row in chats:
        if not isinstance(row, dict):
            errors.append("BAD_REGISTRY_ROW")
            continue
        errors += require_keys(row, CHAT_REQUIRED, "CHAT_ROW")
        url = row.get("chat_url")
        sid = row.get("source_chat_id")
        if not isinstance(url, str) or not url.startswith("https://chatgpt.com/"):
            errors.append("BAD_CHAT_URL")
        elif url in seen_urls:
            errors.append("DUPLICATE_CHAT_URL")
        else:
            seen_urls.add(url)
        if not isinstance(sid, str) or not sid:
            errors.append("BAD_SOURCE_CHAT_ID")
        elif sid in seen_ids:
            errors.append("DUPLICATE_SOURCE_CHAT_ID")
        else:
            seen_ids.add(sid)
        for key in ["done_count", "unfinished_count", "blocked_count", "ready_for_promotion_count"]:
            if not isinstance(row.get(key), int) or row.get(key) < 0:
                errors.append("BAD_CHAT_ROW_COUNT_" + key)
    return errors


def queue_errors(value):
    errors = require_keys(value, QUEUE_REQUIRED, "QUEUE")
    if value.get("schema") != "mb.old_chat_github_registration.github_promotion_queue_index.v1":
        errors.append("BAD_QUEUE_SCHEMA")
    if not isinstance(value.get("updated_at_utc"), str) or not value.get("updated_at_utc"):
        errors.append("BAD_QUEUE_UPDATED_AT")
    if not isinstance(value.get("repo"), str) or not value.get("repo"):
        errors.append("BAD_QUEUE_REPO")
    errors += count_object_errors(value, "status_counts", QUEUE_COUNT_KEYS, "QUEUE")
    items = value.get("items")
    if not isinstance(items, list):
        return errors + ["BAD_QUEUE_ITEMS"]
    if value.get("queue_item_count") != len(items):
        errors.append("BAD_QUEUE_COUNT")
    keys = set()
    for row in items:
        if not isinstance(row, dict):
            errors.append("BAD_QUEUE_ROW")
            continue
        errors += require_keys(row, QUEUE_ITEM_REQUIRED, "QUEUE_ROW")
        key = row.get("key")
        if not isinstance(key, str) or not key:
            errors.append("BAD_QUEUE_KEY")
        elif key in keys:
            errors.append("DUPLICATE_QUEUE_KEY")
        else:
            keys.add(key)
        if not isinstance(row.get("chat_url"), str) or not row.get("chat_url", "").startswith("https://chatgpt.com/"):
            errors.append("BAD_QUEUE_CHAT_URL")
        if not isinstance(row.get("source_chat_id"), str) or not row.get("source_chat_id"):
            errors.append("BAD_QUEUE_SOURCE_CHAT_ID")
        if row.get("status") not in {"READY_FOR_PROMOTION", "BLOCKED_MISSING_LOCAL_EVIDENCE", "BLOCKED_PATH_SHA_CONFLICT", "NEEDS_HUMAN_ADJUDICATION", "SMOKE_ONLY_DO_NOT_PROMOTE", "SUPERSEDED_DO_NOT_PROMOTE"}:
            errors.append("BAD_QUEUE_STATUS")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    errors = []
    registry, e = read_json(args.registry, "NO_REGISTRY_FILE")
    errors += e
    queue, e = read_json(args.queue, "NO_QUEUE_FILE")
    errors += e
    if registry is not None:
        errors += registry_errors(registry)
    if queue is not None:
        errors += queue_errors(queue)
    report = {
        "schema": "mb.old_chat_github_registration.github_fetch_contract_report.v1",
        "decision": "PASS_GITHUB_REGISTRY_FETCH_CONTRACT" if not errors else "BAD_GITHUB_REGISTRY_FETCH_CONTRACT",
        "errors": errors,
        "registered_chat_count": registry.get("registered_chat_count") if registry else None,
        "queue_item_count": queue.get("queue_item_count") if queue else None,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 2

if __name__ == "__main__":
    raise SystemExit(main())
