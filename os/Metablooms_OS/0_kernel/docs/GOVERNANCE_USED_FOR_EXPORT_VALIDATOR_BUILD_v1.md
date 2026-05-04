# GOVERNANCE_USED_FOR_EXPORT_VALIDATOR_BUILD_v1

- `boot_manifest_v1.json` — Registers active runtime governance and next-stage components.
- `artifact_registry.json` — Tracks artifacts, hashes, statuses, and lineage.
- `CURRENT_WORKING_BASELINE_POINTER_v1.json` — Prevents stale ZIP fallback by identifying current active root.
- `STAGE_STATE_LEDGER_v1.json` — Records PASS/BLOCK/repair state and latest_pass.
- `STAGE_DAG_v1.json` — Records stage dependencies and ordering.
- `AUTO_RUNAWAY_STAGE_SPLIT_CONTRACT_v1.json` — Forces bounded micro-stages instead of runaway turns.
- `TRANSACTIONAL_STAGE_RUNNER_CONTRACT_v1.json` — Defines staged preflight, verify, promote, commit, state-update semantics.
- `MANIFEST_PROVENANCE_EXPORT_CONTRACT_v1.json` — Defines manifest/provenance export requirements.
- `RESTORE_LADDER_CONTRACT_v1.json` — Defines restore precedence and Git filemode normalization.
- `BLOCKED_RECEIPT_HANDLING_RULE_v1.json` — Prevents failed-stage artifacts from dirtying future stages.
- `G0_EXPORT_RECOVERY_VALIDATOR_SCOPE_CONTRACT_v1.json` — Locks validator scope from audit and research.
- `G0_EXPORT_RECOVERY_VALIDATOR_GATE_MATRIX_v1.json` — Enumerates blocking gates.
- `EXPORT_RECOVERY_PROVEN_VALIDATOR_CONTRACT_v1.json` — Machine-readable validator contract.
- `export_recovery_proven_validator_v1.py` — Executable fail-closed validator.
- `SEE/CE packets` — Research-backed synthesis and comprehension framing.
- `stage receipts and handoffs` — Proof and continuity discipline for every stage.

## Next Correct Command

`EXECUTE G4 — RUN VALIDATOR AGAINST F7 EXPORT`
