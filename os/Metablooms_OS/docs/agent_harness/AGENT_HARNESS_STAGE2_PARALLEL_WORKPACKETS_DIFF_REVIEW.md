# Agent Harness Stage 2: Parallel Workpackets and Diff Review

Stage 2 adds a bounded parallel-workpacket model to the MetaBlooms agent harness.

## Operator commands

```bash
mb harness --plan --parallel-plan --stage IMPLEMENT_AGENT_HARNESS_STAGE_2_PARALLEL_WORKPACKETS_AND_DIFF_REVIEW --json
mb harness --diff-review --stage IMPLEMENT_AGENT_HARNESS_STAGE_2_PARALLEL_WORKPACKETS_AND_DIFF_REVIEW --json
mb harness --check --json
```

## Governance rules

- Parallelism is represented as deterministic workpackets, not unmanaged autonomous agents.
- Workpackets in a shared parallel group may proceed only when their write scopes do not overlap.
- Implementation, validation, audit, and export workpackets require diff review before promotion.
- Trace entries carry bounded summaries; full plans and diff reviews are artifacts under `runtime/agent_harness/`.
- Conflicts create blockers or human-interrupt candidates rather than silent merge.

## Stage limit

This stage installs the planner, diff-review report, schema, and validator. It does not run real parallel agents or mutate production files outside scoped runtime artifacts.
