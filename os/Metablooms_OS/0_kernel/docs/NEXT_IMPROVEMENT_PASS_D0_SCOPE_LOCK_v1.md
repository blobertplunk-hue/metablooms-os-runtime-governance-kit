# NEXT_IMPROVEMENT_PASS_D0_SCOPE_LOCK_v1

## Stage

D0 — Verify baseline + lock D1 scope only.

## Status

Bounded preflight and scope-lock only. No D1 implementation was performed.

## Current stable baseline

- Active root: `/mnt/data/Metablooms_OS_refined`
- Baseline lock: `0_kernel/registry/BASELINE_LOCK_RECREATED_CURRENT_BEFORE_D0_RECEIPT.json`
- Stable export: `/mnt/data/Metablooms_OS_refined_RECREATED_CURRENT_BASELINE_BEFORE_D0.zip`

## Verified baseline capabilities

- boot runtime executor
- trigger router evaluator
- CE packet validator
- runaway-turn breaker invariant
- tracked-cache export/recovery invariant

## Selected next improvement

D1 — SEE packet schema + validator.

## D1 scope

D1 is specification only. It should create:

- `0_kernel/docs/SEE_PACKET_VALIDATOR_SPEC_v1.md`
- `0_kernel/schemas/SEE_PACKET_SCHEMA_v1.json`
- `0_kernel/schemas/SEE_PACKET_VALIDATOR_CONTRACT_v1.json`
- `0_kernel/registry/SEE_PACKET_VALIDATOR_SPEC_RECEIPT_v1.json`
- `0_kernel/registry/D1_TO_D2_HANDOFF_v1.json`

## D1 must not

- implement the validator
- export a baseline
- run cleanup
- run broad `/mnt/data` scans
- claim SEE validation is executable yet

## SEE validator target behavior

Future implementation should validate original request, research trigger reason, query plan, `web.run` evidence flag, source list, claim/source bindings, contradictions/gaps, synthesis, limitations, SEE verdict, and receipt path.

## Runaway-turn guard

If D1 starts expanding into implementation, export, cleanup, or recovery work, stop and write a blocked/partial receipt.

## Next Correct Command

`EXECUTE STAGE D1 — SEE PACKET VALIDATOR SPEC`
