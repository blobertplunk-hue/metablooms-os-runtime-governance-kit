# TRANSACTIONAL_STAGE_RUNNER_CONTRACT_v1

## Purpose

Define retry-safe transaction semantics for governed MetaBlooms stages.

## Core transaction

1. P0_PREFLIGHT
2. P1_STAGE_ROOT
3. P2_WRITE_OUTPUTS
4. P3_VERIFY
5. P4_PROMOTE
6. P5_COMMIT
7. P6_UPDATE_STATE
8. P7_HANDOFF

## Main rule

No future stage may claim success unless its required artifacts are written, verified, committed, and state is updated.

## Promotion rules

- Promote only after verification passes.
- Use the smallest valid change set.
- Do not delete tracked files without a deletion contract.
- Contract-only stages may write directly only after clean preflight.

## Idempotency rules

- Stage artifact paths must be deterministic.
- Canonical receipts must use stable names.
- Re-runs must either overwrite deterministic targets or confirm they already satisfy the contract.
- Pointer and ledger update only after commit.

## Blocked stage rules

- Failed stages write a blocker receipt.
- Failed stages do not update the pointer.
- Failed stages do not advance the ledger latest_pass.

## F3 non-goals

F3 does not implement a runner script, export a baseline, or perform restore proof.

## Next Correct Command

`EXECUTE F4 — MANIFEST/PROVENANCE EXPORT CONTRACT`
