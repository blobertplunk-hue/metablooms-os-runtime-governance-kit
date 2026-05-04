# EXPORT_RECOVERY_PROVEN_VALIDATOR_IMPLEMENTATION_NOTES_v1

## Stage

G2 — Export Recovery Validator Implementation

## Scope

Implementation only. Regression fixtures are deferred to G3.

## Implemented script

`0_kernel/scripts/export_recovery_proven_validator_v1.py`

## Gate coverage

The implementation includes all ten G1 gates:

1. ledger-declared outputs inside ZIP
2. final PASS receipts inside ZIP
3. no placeholder metadata
4. git-head lifecycle consistency
5. sidecar binding
6. deterministic ZIP policy
7. DAG/ledger mapping
8. pointer conflict resolution
9. transactional state order
10. policy-as-code decision

## Expected first target

The existing F7 export is expected to fail at least the missing-output and placeholder-metadata gates. That proof is deferred to G4.

## Next Correct Command

`EXECUTE G3 — EXPORT RECOVERY VALIDATOR REGRESSION FIXTURES`
