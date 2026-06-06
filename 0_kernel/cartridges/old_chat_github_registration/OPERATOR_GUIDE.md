# Old Chat Work Status Operator Guide

The old-chat cartridge collects work status before artifact promotion. The operator must know what a chat did, what it is doing, and whether it is finished before any repository action is allowed.

## Required workflow

1. Ask the old chat for a `mb.old_chat_github_registration.work_status_packet.v1` packet.
2. Validate the packet against `schemas/old_chat_work_status_packet.schema.json`.
3. Convert artifact claims into the existing artifact comparison packet when repository comparison is needed.
4. Compare artifacts against a complete GitHub manifest or an explicitly partial manifest source.
5. Ingest the comparison report into the registry and promotion queue.
6. Promote only after separate adjudication.

## Completion status rules

- `COMPLETE_VERIFIED` requires evidence, tests or receipts, and repository comparison evidence.
- `COMPLETE_UNVERIFIED` means the old chat says it is finished but the cartridge has not verified it.
- `IN_PROGRESS` and `BLOCKED` must remain visible in the future GitHub registry-of-record.
- `SUPERSEDED` and `ABANDONED` are not hidden; they explain why work should not be promoted.

## Promotion rules

Registration is not promotion. A work-status packet can recommend review, but it cannot authorize a GitHub PR by itself. Promotion requires exact evidence, repository comparison, conflict checks, and explicit adjudication.
