# RESTORE_LADDER_MODE_NORMALIZATION_PROOF_v1

## Purpose

Define and prove restore source precedence plus Git filemode normalization.

## Restore selection order

1. `CURRENT_WORKING_BASELINE_POINTER_v1.json`
2. `STAGE_STATE_LEDGER_v1.json` latest PASS entry
3. recovery-proven stable baseline manifest
4. manual repaired artifact with explicit repair receipt

## Mode normalization rule

Every restore must run:

```bash
git config core.filemode false
```

before Git cleanliness checks.

## Proof cases

- Pointer source outranks stable ZIP.
- Ledger latest PASS outranks stable ZIP when pointer is absent.
- Stable ZIP requires verified manifest or explicit repair receipt.
- Mode-only drift is normalized by `core.filemode=false`.
- Content drift remains visible and blocks.

## F5 non-goals

F5 does not implement a restore CLI, promote active roots, or export a stable baseline.

## Next Correct Command

`EXECUTE F6 — BLOCKED RECEIPT HANDLING RULE`
