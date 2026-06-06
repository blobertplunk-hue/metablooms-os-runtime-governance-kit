# G0_EXPORT_RECOVERY_VALIDATOR_SCOPE_LOCK_v1

## Purpose

Lock scope for an executable export-recovery validator before building another “recovery-proven” export.

## Failure class being prevented

Success claims outran artifact verification.

The prior export was structurally useful, but it was not a true recovery-proven stable export because the ZIP did not contain every final proof/lock artifact and internal metadata still had placeholders or pending lifecycle state.

## Required validator gates

1. Ledger-declared outputs must exist inside the ZIP or be explicitly external-sidecar-required.
2. ZIP must contain final PASS receipts, not pending/export_ready receipts.
3. Manifest and provenance must contain no placeholders.
4. Git heads must be synchronized or lifecycle-labeled.
5. Sidecar must exist, match the ZIP, and be bound from internal metadata.
6. ZIP must follow deterministic packaging policy.
7. DAG short IDs and ledger full IDs require an explicit mapping.
8. Boot-critical pointer conflicts must be resolved or quarantined.
9. Pointer and ledger may advance only after commit and validation succeed.
10. PASS requires a machine-readable validator decision artifact.

## G-arc plan

1. G0 — Scope lock
2. G1 — Validator schema + contract
3. G2 — Validator implementation
4. G3 — Regression fixtures
5. G4 — Run validator against F7 export
6. G5 — Repaired recovery-proven export
7. G6 — Recovery proof + baseline lock
8. G7 — Return to E4B

## G0 non-goals

G0 does not implement the validator, create an export, run recovery proof, or clean files.

## Next Correct Command

`EXECUTE G1 — EXPORT RECOVERY VALIDATOR SCHEMA + CONTRACT`
