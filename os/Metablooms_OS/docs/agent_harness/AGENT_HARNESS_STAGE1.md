# Agent Harness Stage 1

Stage: `IMPLEMENT_AGENT_HARNESS_STAGE_1`

This stage installs the first MetaBlooms agent harness layer: a typed stage graph, role policy, workpacket schema, planner command, validator, executor registration, and `mb harness` operator surface.

## Scope

Stage 1 is a contract and validation stage. It does **not** start unbounded autonomous agents. It defines role-scoped workpackets so later stages can coordinate research, planning, implementation, validation, audit, and export without mixing responsibilities.

## Critical invariants

- Artifacts become authority only after validation and promotion gates pass.
- Each role has explicit write scope.
- Security hard-blocks stay hard blocks; reviewable failures become checkpointed interrupts.
- Harness metadata can be validated with no broad extraction.
- Parallelization is allowed only for declared groups; export remains serialized behind promotion.

## Operator command

```bash
mb harness --json
mb harness --plan --stage IMPLEMENT_AGENT_HARNESS_STAGE_1 --json
mb harness --check --json
```
