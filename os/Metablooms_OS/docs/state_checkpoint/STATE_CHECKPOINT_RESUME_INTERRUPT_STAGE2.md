# State Checkpoint / Resume / Interrupt Stage 2

Stage 2 hard-wires checkpoints and security interrupts into the stage runner.

## Critical path

```text
mb run-stage --execute
  -> checkpoint_manager_v1.py create start checkpoint
  -> security_gate_enforcer_v1.py
  -> reviewable gate failures create interrupt checkpoint
  -> malicious prompt injection gates hard-block
  -> cartridge_executor_v1.py only after gate pass
  -> checkpoint_manager_v1.py create end checkpoint
```

## Security interrupt rule

Only gates MBSEC-GATE-004 through MBSEC-GATE-007 may produce a human-review interrupt. Prompt injection, forged/stale authority, archive-safety, and prompt-injection fixture failures remain hard blocks.

## Resume invariant

Resume must use the same `thread_id`. The resume payload is JSON data, not an executable instruction.
