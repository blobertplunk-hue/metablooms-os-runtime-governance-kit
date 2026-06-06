# Old Chat Work Status Share Prompt

Paste this into an old MetaBlooms work chat when you need it to register what it did and what remains.

```text
You are an old MetaBlooms work chat. Share your work for the old_chat_github_registration cartridge.

Return only JSON using schema:
mb.old_chat_github_registration.work_status_packet.v1

You must report:

1. What you have done.
2. What you are currently doing or left partially complete.
3. Whether you consider the work finished.
4. What evidence proves the work exists.
5. What files, patches, workflows, schemas, receipts, exports, or handoff bundles you claim.
6. What still needs to be checked before anything is promoted to GitHub.
7. Whether each artifact is ready, blocked, smoke-only, superseded, or incomplete.

Do not claim promotion.
Do not claim GitHub already has the work unless you have direct evidence.
Do not omit blockers.
Do not omit unfinished work.
Do not mark work COMPLETE_VERIFIED unless tests, receipts, and repository comparison evidence exist.

Return JSON only.
```
