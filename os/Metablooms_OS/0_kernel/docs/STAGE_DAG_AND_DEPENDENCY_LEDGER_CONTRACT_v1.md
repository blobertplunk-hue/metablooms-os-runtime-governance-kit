# STAGE_DAG_AND_DEPENDENCY_LEDGER_CONTRACT_v1

## Purpose

Prevent lost-stage restores by recording the governed stage graph, dependencies, outputs, and latest successful state.

## Restore precedence

1. Current working baseline pointer
2. Latest PASS entry in `STAGE_STATE_LEDGER_v1.json`
3. Latest recovery-proven stable baseline
4. Manual repaired artifact with explicit repair receipt

## DAG file

`0_kernel/pipeline/STAGE_DAG_v1.json`

## Ledger file

`0_kernel/state/STAGE_STATE_LEDGER_v1.json`

## Ledger update rule

The ledger must update after successful governed stages, repairs, rematerializations, exports, and baseline locks.

Blocked stages may be recorded, but must not advance `latest_pass`.

## PASS entry requirements

A PASS entry must include:

- stage
- verdict
- git head
- receipt
- outputs
- dependencies
- supersedes
- timestamp

## F2 non-goals

F2 does not implement the transactional runner, restore ladder, or export process.

## Next Correct Command

`EXECUTE F3 — TRANSACTIONAL STAGE RUNNER CONTRACT`
