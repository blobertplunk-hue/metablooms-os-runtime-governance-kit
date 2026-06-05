#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

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

def registry_errors(value):
    errors = []
    if value.get("schema") != "mb.old_chat_github_registration.github_registry_index.v1":
        errors.append("BAD_REGISTRY_SCHEMA")
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
    return errors

def queue_errors(value):
    errors = []
    if value.get("schema") != "mb.old_chat_github_registration.github_promotion_queue_index.v1":
        errors.append("BAD_QUEUE_SCHEMA")
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
        key = row.get("key")
        if not isinstance(key, str) or not key:
            errors.append("BAD_QUEUE_KEY")
        elif key in keys:
            errors.append("DUPLICATE_QUEUE_KEY")
        else:
            keys.add(key)
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
