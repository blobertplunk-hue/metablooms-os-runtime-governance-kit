# Start Here for Old Chats

This is the front door for any old MetaBlooms chat that needs to register and share work through GitHub.

## Rule 0: registration is not promotion

Old chats do not push directly to the repository and do not claim promotion. They report work, evidence, status, blockers, and artifact claims. A later governed update prepares registry files and a later adjudication decides whether anything becomes a PR.

## Step 1: fetch the GitHub registry first

Before describing your own work, fetch these exact repository files:

- `governance/chat_work_registry/registered_chats.index.json`
- `governance/chat_work_registry/promotion_queue.index.json`

If either file cannot be fetched, stop and report `GITHUB_FETCH_BLOCKED`. Do not say no chats are registered unless the GitHub registry was fetched and validated.

## Step 2: check existing registered work

Check for:

- the same `chat_url`;
- the same `source_chat_id`;
- similar `work_summary` values;
- overlapping `declared_path` values;
- queue items already marked `READY_FOR_PROMOTION` or blocked for the same work.

If the same chat URL already exists, mark the packet as a refresh or duplicate. If similar work exists, mark `NEEDS_HUMAN_ADJUDICATION` and explain the overlap.

## Step 3: report work status

Use `OLD_CHAT_SHARE_PROMPT.md` and return only a JSON packet using schema `mb.old_chat_github_registration.work_status_packet.v1`.

You must report:

- what you have done;
- what you are still doing;
- whether the work is finished;
- what evidence exists;
- what files, patches, workflows, schemas, receipts, exports, or bundles you claim;
- what is blocked or unfinished;
- what should or should not be promoted.

## Step 4: put outputs in canonical paths

A governed update should place outputs here:

| Output | Canonical path |
|---|---|
| Work-status packet | `governance/chat_work_registry/chat_packets/<source_chat_id>.json` |
| Comparison report | `governance/chat_work_registry/reports/<source_chat_id>.comparison_report.json` |
| Registry index | `governance/chat_work_registry/registered_chats.index.json` |
| Promotion queue | `governance/chat_work_registry/promotion_queue.index.json` |

## Step 5: compare before promotion

No artifact is ready for promotion until it has been compared against the GitHub repository manifest. Path/SHA conflicts block promotion. Missing local evidence blocks promotion. Smoke-only or superseded work must not be promoted.

## Step 6: stop at a packet if update tooling is unavailable

If the registry update tool is unavailable, return the work-status packet and stop. Do not invent a registry update.
