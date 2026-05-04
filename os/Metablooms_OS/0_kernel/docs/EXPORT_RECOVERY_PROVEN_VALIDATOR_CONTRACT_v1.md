# EXPORT_RECOVERY_PROVEN_VALIDATOR_CONTRACT_v1

## Purpose

Prevent false “recovery-proven” export claims.

The validator must fail closed unless the ZIP, sidecar, internal manifest, provenance, receipts, ledger, DAG, pointer, and validator decision all agree.

## Required gates

1. Ledger-declared outputs inside ZIP
2. Final PASS receipts inside ZIP
3. No placeholder metadata
4. Git head lifecycle consistency
5. Sidecar binding
6. Deterministic ZIP policy
7. DAG ↔ ledger mapping
8. Pointer conflict resolution
9. Transactional state order
10. Policy-as-code decision

## Fail-closed examples

The validator must return FAIL if:

- a ledger-declared output is missing from the ZIP;
- a receipt inside the ZIP says PENDING_EXPORT, export_ready, blocked, or lacks PASS;
- manifest/provenance contains `<filled_after_zip>`, TODO, pending, or size 0;
- Git heads diverge without lifecycle labels;
- sidecar hash/size does not match the ZIP;
- ZIP contains nested `.git`, caches, duplicate entries, or unmanifested unstable evidence;
- DAG short IDs cannot be mapped to ledger full IDs;
- active conflicting boot-critical pointers remain;
- no machine-readable validator decision exists.

## G1 non-goals

G1 does not implement the validator. It defines the schema and contract for G2.

## Next Correct Command

`EXECUTE G2 — EXPORT RECOVERY VALIDATOR IMPLEMENTATION`
