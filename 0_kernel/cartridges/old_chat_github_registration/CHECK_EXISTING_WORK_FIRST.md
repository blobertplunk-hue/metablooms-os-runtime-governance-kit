# Check Existing Work First

Every old chat must check GitHub registry state before registering new work.

## Required sources

Fetch and validate these exact files:

- `governance/chat_work_registry/registered_chats.index.json`
- `governance/chat_work_registry/promotion_queue.index.json`

If either fetch fails, stop with `GITHUB_FETCH_BLOCKED`.

## Required checks

| Check | Match means | Response |
|---|---|---|
| Same `chat_url` | Same chat is already registered | Mark refresh or duplicate. |
| Same `source_chat_id` | Same chat identity | Refresh existing row, not new row. |
| Same `declared_path` | Same target file or work path | Compare SHA and status. |
| Same `sha256` | Same content already exists | Mark duplicate or already shared. |
| Similar `work_summary` | Possible overlapping work | Mark `NEEDS_HUMAN_ADJUDICATION`. |
| Existing queue item | Work already pending | Do not create a duplicate queue item. |

## Required overlap fields

The packet notes must include:

- `overlap_checked`: yes or no
- `related_registered_chats`: source chat IDs or empty list
- `related_queue_items`: queue keys or empty list
- `overlap_decision`: `NONE_FOUND`, `DUPLICATE`, `CONTINUATION`, `CONFLICT`, or `NEEDS_HUMAN_ADJUDICATION`

If another chat appears to be doing the same cartridge, workflow, schema, receipt, export, or path work, do not claim independent completion. Explain whether this is duplicate, continuation, replacement, or conflict.
