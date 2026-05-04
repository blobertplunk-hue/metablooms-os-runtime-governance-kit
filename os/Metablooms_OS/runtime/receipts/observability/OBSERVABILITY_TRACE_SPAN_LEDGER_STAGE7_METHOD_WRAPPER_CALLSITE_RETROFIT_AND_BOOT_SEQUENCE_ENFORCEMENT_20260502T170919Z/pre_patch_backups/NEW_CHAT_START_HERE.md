# MetaBlooms OS Start Here

<!-- METABLOOMS_OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_v1 -->

## Operator visual tracker first

Open the visual tracker before governed work resumes:

```text
OPEN_OPERATOR_VISUAL_TRACKER.html
runtime/operator_tracker/operator_visual_tracker_latest.html
runtime/operator_tracker/OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_LATEST.json
```

Current rule: show the tracker first, then execute exactly one bounded governed stage.

Latest full authority from this stage is verified by external `.sha256` sidecar because a ZIP cannot contain its own final hash without changing its bytes.

Current repaired full authority export: `METABLOOMS_OS_STAGE3_AUTHORITY_RECONCILED_NEW_CHAT_VALIDATOR_PASS_20260502T163016Z.zip`
Checksum sidecar: `METABLOOMS_OS_STAGE3_AUTHORITY_RECONCILED_NEW_CHAT_VALIDATOR_PASS_20260502T163016Z.zip.sha256`

---

# MetaBlooms OS Start Contract — Stage 3 Operator Visual Tracker Authority

Authority ZIP: `METABLOOMS_OS_STAGE3_AUTHORITY_RECONCILED_NEW_CHAT_VALIDATOR_PASS_20260502T163016Z.zip`
Sidecar: `METABLOOMS_OS_STAGE3_AUTHORITY_RECONCILED_NEW_CHAT_VALIDATOR_PASS_20260502T163016Z.zip.sha256`
Canonical root: `/mnt/data/Metablooms_OS`
Boot entry contract: `0_kernel/boot_contracts/NEW_CHAT_START_CONTRACT_v1.md`

## Required startup sequence

1. Verify the authority ZIP SHA-256 against the external sidecar before trusting the archive.
2. Extract or verify `/mnt/data/Metablooms_OS` as the canonical working root.
3. Open/show `OPEN_OPERATOR_VISUAL_TRACKER.html` before governed work resumes.
4. Run `runtime/governance/boot_critical_governance_loader_v1.py`.
5. Run `runtime/governance/governance_scatter_prevention_v1.py`.
6. Run `runtime/governance/fresh_chat_boot_rehearsal_v1.py`.
7. Run `runtime/governance/new_chat_start_contract_validator_v1.py`.
8. Run `runtime/governance/runtime_starter_smoke_v1.py`.
9. Run `runtime/cartridges/prompt_governance_v1/validate_prompt_governance_cartridge_v1.py` and prompt route pre-execution enforcement before substantive MetaBlooms work.
10. Execute at most one bounded governed stage, then write a receipt and handoff.

## Fail-closed conditions

Fail closed if checksum verification, pointer-copy reconciliation, boot-critical file checks, scatter governance, `fresh_chat_boot_rehearsal_v1.py`, `prompt_governance_v1`, pre-execution routing, runtime starter smoke, or operator visual tracker boot-surface validation cannot be proven by same-turn artifacts.

## Current boot surface

- Root tracker: `OPEN_OPERATOR_VISUAL_TRACKER.html`
- Runtime tracker: `runtime/operator_tracker/operator_visual_tracker_latest.html`
- Boot surface manifest: `runtime/operator_tracker/OPERATOR_VISUAL_TRACKER_BOOT_SURFACE_LATEST.json`

## Authority pointer copies

The following pointer copies must remain semantically identical JSON objects:

- `CURRENT_FULL_AUTHORITY_POINTER_v1.json`
- `runtime/authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json`
- `0_kernel/registry/current_authority/CURRENT_FULL_AUTHORITY_POINTER_v1.json`
