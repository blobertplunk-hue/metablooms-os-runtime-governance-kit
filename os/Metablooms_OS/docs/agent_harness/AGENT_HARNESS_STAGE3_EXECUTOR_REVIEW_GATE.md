# Agent Harness Stage 3: Executor Review Gate

Stage `IMPLEMENT_AGENT_HARNESS_STAGE_3_EXECUTOR_REVIEW_GATE` installs a pre-execution review gate for agent-harness workpackets.

## Operator commands

```bash
mb harness --executor-review --json
mb harness --review-gate --json
```

## Enforced behavior

- Implementation workpackets require diff-review evidence.
- Implementation workpackets require bounded write scopes.
- `cartridge_executor_v1.py` calls `agent_harness_executor_review_gate_v1.py` before handler execution.
- Gate output writes a bounded JSON report and trace span.

## Stage limit

This stage installs the executor-review gate. It does not launch autonomous agents.
