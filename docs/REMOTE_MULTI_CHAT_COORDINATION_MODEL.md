# Remote Multi-Chat Coordination Model

Installed by `PROFESSIONALIZATION_CONVERGENCE_STAGE43A1_REMOTE_COORDINATION_SCHEMA_AND_PLAN_INSTALL`.

## Why this exists

MetaBlooms work happens across concurrent ChatGPT chats, Termux, PowerShell, and GitHub. A single linear handoff is not enough. The repo must coordinate lanes, leases, events, sync packets, and recovery state.

## Design basis

- GitHub Actions concurrency can limit concurrent workflow/job runs, but ordering is not guaranteed. MetaBlooms therefore uses explicit event logs and leases for deterministic recovery.
- GitHub content updates require current blob SHAs and parallel create/update/delete operations can conflict. MetaBlooms therefore treats shared state as derived from append-only events.
- CODEOWNERS and branch/ruleset protections are useful enforcement layers, but they do not replace MetaBlooms stage receipts, path leases, and recovery indexes.

## First-order state

`coordination/events/` is append-only and records stage, sync, lease, conflict, and handoff events.

## Derived state

`recovery/*.json` and `recovery/*.md` files are compacted summaries for fast recovery.

## Conflict behavior

Silent overwrites are forbidden. Conflicts must create packets under `coordination/conflicts/` and remain visible until resolved.
