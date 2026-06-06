# GitHub Fetch Contract

Purpose: define how a future chat reconstructs old-chat registry state from GitHub.

## Required sequence

1. Fetch governance/chat_work_registry/registered_chats.index.json.
2. Validate schema and recomputed counts.
3. Fetch governance/chat_work_registry/promotion_queue.index.json.
4. Validate schema and recomputed counts.
5. Fetch per-chat packet_path and report_path only when detailed inspection is needed.
6. Never infer registry state from memory or local receipts when GitHub state is available.

## Fail-closed requirements

- Missing registry index: FAIL_CLOSED_NO_REGISTRY.
- Malformed registry index: FAIL_CLOSED_BAD_REGISTRY.
- Missing promotion queue index: FAIL_CLOSED_NO_PROMOTION_QUEUE.
- Malformed promotion queue index: FAIL_CLOSED_BAD_PROMOTION_QUEUE.
- GitHub access failure: report GITHUB_FETCH_BLOCKED, not NO_CHATS_REGISTERED.

## Retrieval rule

Use exact file paths first. Avoid broad recursive listing as the primary registry source. The compact index files are the registry-of-record.
