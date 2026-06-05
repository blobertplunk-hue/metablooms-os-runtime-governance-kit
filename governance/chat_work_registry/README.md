# Chat Work Registry

This directory is the GitHub-resident registry of record for old-chat work registration.

Future chats with repository access can fetch these files from GitHub and answer which chats registered, what each chat did, what is still active, what is finished, what is blocked, what evidence exists, and what is ready for promotion.

## Files

- registered_chats.index.json is the compact canonical index of registered chats.
- promotion_queue.index.json is the compact canonical promotion queue index.
- chat_packets stores per-chat work-status packets.
- reports stores per-chat comparison reports.

## Operating rule

GitHub state is authoritative for cross-chat coordination. If a chat cannot fetch this registry, it must report a fetch blocker instead of claiming no chats are registered.
