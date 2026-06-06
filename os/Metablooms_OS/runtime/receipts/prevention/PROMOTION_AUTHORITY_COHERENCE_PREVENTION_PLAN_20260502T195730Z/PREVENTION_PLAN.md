# Promotion Authority Coherence Prevention Plan

## Failure class
Promotion allowed a current authority export while the boot authority graph was not closed: controlled files existed outside the controlled artifact index, and stale boot/start authority references coexisted with the current pointer.

## Preventive gate to add
PROMOTION_AUTHORITY_COHERENCE_GATE_v1 must become a blocking gate before any export can be labeled current/full/bootable authority.

## Required blocking checks
1. Controlled artifact closure: every controlled-path artifact is indexed with sha256, size, role, and lifecycle state.
2. Registry transaction proof: any added/moved/deleted controlled artifact has a paired registry delta and sha256 sidecar update.
3. Stale authority sweep: all boot-facing files resolve to the same current authority, except files explicitly marked historical/non-authoritative.
4. Validator invocation contract map: each boot validator declares and is tested with its accepted CLI shape.
5. Fresh-chat boot replay: boot must be reproduced from /mnt/data only, after extraction, using the same start contract a new chat sees.
6. Export self-consistency: exported ZIP contents must include every ledger/pointer-declared boot artifact and must not include unindexed controlled artifacts.
7. Promotion lock fail-closed: pointer promotion to ACTIVE is denied unless all checks above return PASS.

## Anti-regression additions
- Add fixture with intentionally unregistered controlled artifact: must DENY.
- Add fixture with stale CURRENT_EXPORT_AUTHORITY and current pointer mismatch: must DENY.
- Add fixture with mixed positional-root and --root validators: must normalize or DENY with clear remediation.
- Add receipt lint: no success receipt can omit scatter gate output and fresh-chat replay output.

## Smallest next implementation stage
Implement only the gate spec, path classifier, authority-file scanner, CLI contract inventory, and test fixtures first. Do not repair/register the current files in the same stage; proving the prevention gate comes before corrective mutation.
