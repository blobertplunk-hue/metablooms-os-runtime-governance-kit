# G5_REPAIRED_RECOVERY_PROVEN_EXPORT_v1

G5 rebuilds the export after applying the G4 validator repair plan.

The prior F7 export is not treated as recovery-proven. G5 writes final stage artifacts before zipping, uses lifecycle-labeled heads, explicit external sidecar policy, deterministic ZIP packaging, and then runs the validator against the repaired ZIP.

## Next Correct Command

`EXECUTE G6 — RECOVERY PROOF + BASELINE LOCK`
