# Registry Update Prep Contract

This contract defines the minimum deterministic update set for registering old-chat work in GitHub.

## Inputs

- A validated work-status packet.
- A comparison report from the old-chat artifact comparator.
- The current registered_chats index.
- The current promotion_queue index.

## Outputs

- Updated governance/chat_work_registry/registered_chats.index.json.
- Updated governance/chat_work_registry/promotion_queue.index.json.
- Copied chat packet under governance/chat_work_registry/chat_packets.
- Copied comparison report under governance/chat_work_registry/reports.
- A registry update receipt.

## Required gates

- Duplicate chat_url is blocked unless the same source_chat_id is being refreshed.
- COMPLETE_VERIFIED requires evidence and repository comparison evidence.
- READY_FOR_PROMOTION requires local evidence and no path digest conflict.
- Missing-evidence items stay blocked.
- Smoke-only and superseded work cannot enter READY_FOR_PROMOTION.
- Registry counts must be recomputed from rows, not hand-entered.
