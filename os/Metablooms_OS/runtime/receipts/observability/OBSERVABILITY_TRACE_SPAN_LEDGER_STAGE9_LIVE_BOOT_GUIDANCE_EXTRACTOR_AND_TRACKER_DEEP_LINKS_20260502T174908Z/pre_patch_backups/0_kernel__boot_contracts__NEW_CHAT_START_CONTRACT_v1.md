# MetaBlooms OS Start Contract — Stage 3 Reconciled Operator Visual Tracker Authority

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
8. Run `runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json`.
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


## Stage 6 method reliability authority
Before relying on suppressed failure lessons or runtime starter smoke command guidance, run `0_kernel/validators/validate_observability_trace_span_ledger_stage6_method_reliability_v1.py --root /mnt/data/Metablooms_OS --json` and prefer `runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json` over direct ad hoc invocation.


## Stage 7 boot-sequence enforcement

Runtime starter smoke must be invoked through `runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json`. Direct ad hoc invocation of `runtime_starter_smoke_v1.py` is reserved as the wrapper's underlying implementation dependency, not as the operator-facing boot command.


Before trusting boot-sequence wrapper enforcement, run `0_kernel/validators/validate_observability_trace_span_ledger_stage7_boot_sequence_enforcement_v1.py --root /mnt/data/Metablooms_OS --json`.


## OBSERVABILITY TRACE/SPAN LEDGER STAGE 8 — WRAPPER-ONLY BOOT + HISTORICAL CALLSITE QUARANTINE

Live boot guidance is wrapper-only. Run:

```bash
python runtime/governance/runtime_starter_smoke_contract_wrapper_v1.py --root /mnt/data/Metablooms_OS --json
```

Historical receipts and old boot-smoke evidence may still mention the underlying runtime starter smoke implementation. Those references are provenance, not operator instructions, and are classified by `runtime/traces/observability/HISTORICAL_CALLSITE_QUARANTINE_INDEX_LATEST.json` under `0_kernel/registry/observability/MB_HISTORICAL_CALLSITE_QUARANTINE_POLICY_v1.json`.

Before trusting boot instructions, run:

```bash
python 0_kernel/validators/validate_observability_trace_span_ledger_stage8_historical_callsite_quarantine_v1.py --root /mnt/data/Metablooms_OS --json
```
