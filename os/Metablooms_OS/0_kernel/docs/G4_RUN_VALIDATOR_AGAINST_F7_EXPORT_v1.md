# G4_RUN_VALIDATOR_AGAINST_F7_EXPORT_v1

## Result

Validator verdict against the prior F7 export: `FAIL`.

## Meaning

This is expected. G4 is a validation/proof stage, not a repair stage. The prior F7 export should fail because the audit found real export-consistency defects.

## Failed gates

- `G1_LEDGER_DECLARED_OUTPUTS_INSIDE_ZIP`
- `G2_FINAL_PASS_RECEIPTS_INSIDE_ZIP`
- `G3_NO_PLACEHOLDER_METADATA`
- `G4_GIT_HEAD_LIFECYCLE_CONSISTENCY`
- `G5_SIDECAR_BINDING`
- `G6_DETERMINISTIC_ZIP_POLICY`
- `G8_POINTER_CONFLICT_RESOLUTION`
- `G10_POLICY_AS_CODE_DECISION`

## Next Correct Command

`EXECUTE G5 — REPAIRED RECOVERY-PROVEN EXPORT`
