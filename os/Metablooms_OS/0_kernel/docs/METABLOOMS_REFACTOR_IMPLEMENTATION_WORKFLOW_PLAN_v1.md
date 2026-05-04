# MetaBlooms governed refactor implementation workflow plan v1

## Purpose

Implement a governed, LLM-optimized refactor that converts weak or half-runtime artifacts into:
- ADRs for rationale and historical decisions
- executable contracts and registries for machine-read governance
- evidence-bound gates for allow/deny decisions
- portable session-state export instead of model-specific sync files
- cartridge-grade telemetry with stable event semantics and replay/validation support

This plan is written against the live runtime at `/mnt/data/Metablooms_OS` and the repaired full-OS source archive at `/mnt/data/METABLOOMS_FULL_OS_v3_3_PHASE1_PHASE2_MERGED_REPAIRED.zip`.

## Scope targets

### Source artifacts to ingest from repaired full OS bundle
- `CLAUDE_MEMORY_SYNC_v1.json`
- `0_kernel/scripts/claude_memory_sync_writer_v1.py`
- `0_kernel/scripts/p0a_external_reuse_scan_precheck_v1.py`
- `1_governance/cool_overlays/COOL_5_EXTERNAL_REUSE_SCAN_GATE_SCHEMA_v1.json`
- `1_governance/cool_overlays/COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json`
- `0_kernel/scripts/usefulness_surface_validator_v1.py`
- `0_kernel/scripts/p0py_python_health_governance_v1.py`
- `0_kernel/scripts/stage_base_resolver_v1.py`
- `2_engines/telemetry/MISCONCEPTION_TELEMETRY_ENGINE_v1.js`
- `1_governance/cool_overlays/MISCONCEPTION_TELEMETRY_SCHEMA_v1.json`
- `3_data/html_activities/fractions_number_line_telemetry_v1.html`
- `0_kernel/scripts/dryrun_receipt_phase_accuracy_patch_v1.py`
- `1_governance/workflow_v6/CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json`

### Keep/promote targets
- session state export lane
- external reuse scan gate
- usefulness validator gate
- telemetry schema + engine + replay fixture + demo
- stage-base resolver and python health governance where still useful

### Demote/split targets
- `CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json` -> ADR + executable compatibility contract
- `CLAUDE_MEMORY_SYNC_v1.json` -> session-state export snapshot, not runtime authority
- `COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json` -> actual registry input, not plan prose

## Design principles
1. History/rationale must live in ADRs, not in pseudo-runtime JSON.
2. Runtime enforcement must be executable and return pass/fail plus reasons.
3. Schema annotations are documentation, not enforcement.
4. Telemetry must use stable event names, typed attributes, and replayable fixtures.
5. All new Python execution paths must route through the existing `python3 -S` lane unless a stricter shell-only path is possible.
6. Every stage writes: pre-state probe -> mutation receipt -> verify receipt -> handoff.
7. No broad multi-goal patching in one stage; one bounded mutation family per stage.

## Repository placement model

### Human rationale / ADRs
- New root: `0_kernel/docs/decisions/`
- Naming: `ADR-XXXX-<slug>.md`
- Initial ADRs:
  - `ADR-0001-split-rationale-from-runtime-contracts.md`
  - `ADR-0002-adopt-session-state-export-over-model-specific-sync.md`
  - `ADR-0003-adopt-gate-registry-for-runtime-wiring.md`
  - `ADR-0004-adopt-evidence-bound-reuse-scan-gate.md`
  - `ADR-0005-adopt-stable-telemetry-event-contracts.md`

### Machine-readable contracts / registries
- `runtime/governance/contracts/`
- `runtime/governance/registries/`
- `runtime/governance/schemas/`
- `runtime/governance/decision_logs/`

### Execution scripts
- `0_kernel/scripts/` for orchestration, validation, migration, and receipt writers
- `runtime/governance/` for launcher wrappers, active policy bindings, and registry loaders

### Telemetry runtime
- `2_engines/telemetry/engine/`
- `2_engines/telemetry/schemas/`
- `2_engines/telemetry/fixtures/`
- `3_data/html_activities/` for classroom demos/examples

### Receipts and stage outputs
- `receipts/refactor_program/`
- `0_kernel/registry/lessons_learned/`
- `0_kernel/registry/repair_backlog/` for anything intentionally deferred

## Implementation order

### Stage R0 — Boot, authority, and source intake contract
**Goal:** prove current root, prove source bundle, and stage candidate imports without mutating live authority.

**Actions**
- Verify `/mnt/data/Metablooms_OS` is writable and current.
- Verify repaired source bundle hash and enumerate target files.
- Extract only the target Claude-added artifacts into a bounded staging area:
  - `0_kernel/staging/refactor_intake_<timestamp>/source_bundle_extract/`
- Write path map and intake manifest.

**Outputs**
- `receipts/refactor_program/R0_INTAKE_RECEIPT.json`
- `receipts/refactor_program/R0_PATH_MAP.json`
- `receipts/refactor_program/R0_SOURCE_INTAKE_MANIFEST.json`

**Gate to proceed**
- every listed source artifact either extracted or explicitly marked absent
- no live runtime mutation yet

### Stage R1 — Classification and disposition binding
**Goal:** convert the keep/optional/dead-weight judgment into explicit artifact disposition.

**Actions**
- Create `runtime/governance/contracts/artifact_disposition_contract_v1.json`.
- Record each source artifact as one of:
  - `promote`
  - `split`
  - `archive_only`
  - `discard`
- Add required successor artifact ids and destination paths.

**Outputs**
- `runtime/governance/contracts/artifact_disposition_contract_v1.json`
- `receipts/refactor_program/R1_DISPOSITION_RECEIPT.json`

**Gate to proceed**
- no artifact may remain ambiguous
- every `split` item must identify both archived rationale target and executable successor target

### Stage R2 — ADR extraction and archival conversion
**Goal:** relocate rationale/history out of pseudo-runtime JSON.

**Actions**
- Parse `CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json` and any surviving Claude sync narrative fields.
- Generate ADRs under `0_kernel/docs/decisions/` using MADR-style sections:
  - context/problem
  - decision drivers
  - considered options
  - decision outcome
  - consequences
  - confirmation
- Leave tombstone/redirect metadata in old locations where needed.

**Outputs**
- ADR markdown files
- `runtime/governance/contracts/legacy_artifact_redirects_v1.json`
- `receipts/refactor_program/R2_ADR_EXTRACTION_RECEIPT.json`

**Gate to proceed**
- every narrative-heavy source either archived as ADR or explicitly kept for machine use

### Stage R3 — Compatibility contract replacement for cross-link JSON
**Goal:** replace cross-link memo with executable compatibility contract.

**Actions**
- Create `runtime/governance/contracts/unified_runtime_compatibility_contract_v1.json`.
- Fields:
  - `contract_id`
  - `authoritative_root`
  - `accepted_source_tracks[]`
  - `required_handoff_artifacts[]`
  - `compatibility_rules[]`
  - `stale_after_utc`
  - `supersedes[]`
- Implement validator:
  - `0_kernel/scripts/validate_unified_runtime_compatibility_contract_v1.py`
- Add regression fixture and test receipt.

**Outputs**
- compatibility contract JSON
- validator script
- test fixture under `runtime/evals/governance_regression_suite_v1/fixtures/`
- `receipts/refactor_program/R3_COMPATIBILITY_CONTRACT_RECEIPT.json`

**Gate to proceed**
- validator returns fail on stale or incomplete contract
- old cross-link file marked `archive_only`

### Stage R4 — Session-state export replacement
**Goal:** replace Claude-specific memory sync with model-agnostic state export.

**Actions**
- Create schema: `runtime/governance/schemas/session_state_export_schema_v1.json`
- Create snapshot artifact path: `runtime/governance/state_exports/SESSION_STATE_EXPORT_LATEST_v1.json`
- Implement writer:
  - `0_kernel/scripts/session_state_exporter_v1.py`
- Implement validator:
  - `0_kernel/scripts/validate_session_state_export_v1.py`
- Required export sections:
  - `runtime_facts`
  - `open_work`
  - `deferred_work`
  - `recent_receipts`
  - `transfer_note`
  - `artifact_hashes`
- Force launcher binding to `runtime/governance/python3_S_lane_exec_v1.sh`

**Outputs**
- schema
- exporter
- validator
- latest export snapshot
- `receipts/refactor_program/R4_SESSION_STATE_EXPORT_RECEIPT.json`

**Gate to proceed**
- export validates
- no field names mention specific external model/vendor
- exporter uses `python3 -S` lane or shell-only path

### Stage R5 — Gate registry conversion
**Goal:** replace wiring-plan prose with an actual runtime registry.

**Actions**
- Create `runtime/governance/registries/gate_registry_v1.json`
- Required per-gate fields:
  - `gate_id`
  - `status`
  - `entrypoint`
  - `language`
  - `inputs`
  - `outputs`
  - `applies_to`
  - `preconditions`
  - `failure_mode`
  - `receipt_type`
  - `enabled`
  - `decision_log_required`
- Implement loader:
  - `runtime/governance/load_gate_registry_v1.py`
- Implement integrity validator:
  - `0_kernel/scripts/assert_gate_registry_integrity_v1.py`
- Migrate any gate definitions recoverable from `COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json`.

**Outputs**
- gate registry JSON
- loader
- integrity validator
- `receipts/refactor_program/R5_GATE_REGISTRY_RECEIPT.json`

**Gate to proceed**
- every enabled gate resolves to a real path
- no enabled gate may point to a missing script or schema

### Stage R6 — Evidence-bound external reuse scan gate
**Goal:** upgrade the reuse precheck from advisory script to real policy gate.

**Actions**
- Promote source script into:
  - `0_kernel/scripts/evaluate_external_reuse_gate_v1.py`
- Replace COOL_5 schema with two artifacts:
  - `runtime/governance/schemas/external_reuse_gate_input_schema_v1.json`
  - `runtime/governance/schemas/external_reuse_gate_decision_schema_v1.json`
- Decision output fields:
  - `decision`
  - `decision_id`
  - `reasons[]`
  - `missing_evidence[]`
  - `matched_candidates[]`
  - `evidence_artifact_hashes[]`
  - `staleness_status`
- Bind decision logs under:
  - `runtime/governance/decision_logs/external_reuse/`

**Outputs**
- evaluator script
- input/output schemas
- test fixtures: pass/fail/defer
- `receipts/refactor_program/R6_EXTERNAL_REUSE_GATE_RECEIPT.json`

**Gate to proceed**
- no `pass` without evidence artifact hashes
- stale evidence yields `defer` or `fail`

### Stage R7 — Usefulness validator promotion
**Goal:** turn the usefulness validator into a registered first-class gate.

**Actions**
- Ingest `usefulness_surface_validator_v1.py`
- Create schema:
  - `runtime/governance/schemas/usefulness_surface_contract_v1.json`
- Register gate in `gate_registry_v1.json`
- Require standard receipt and decision log emission.
- Add fixtures for:
  - fully useful artifact
  - decorative artifact
  - structurally valid but educationally weak artifact

**Outputs**
- promoted validator
- schema
- fixtures
- `receipts/refactor_program/R7_USEFULNESS_GATE_RECEIPT.json`

**Gate to proceed**
- validator must distinguish structure-valid from actually-useful

### Stage R8 — Python health + stage resolver harmonization
**Goal:** preserve the strong Claude-originated operational utilities while aligning them with the current python-safe lane.

**Actions**
- Ingest and review:
  - `p0py_python_health_governance_v1.py`
  - `stage_base_resolver_v1.py`
- Merge any non-duplicative logic into active runtime scripts or wrappers.
- Remove any plain `python3` dependency in favor of the `python3 -S` launcher.
- Register both utilities if they remain separately valuable.

**Outputs**
- harmonized scripts or merged patches
- updated launcher bindings if needed
- `receipts/refactor_program/R8_PYTHON_HEALTH_AND_RESOLVER_RECEIPT.json`

**Gate to proceed**
- no retained operational utility may launch plain `python3`

### Stage R9 — Telemetry cartridge promotion
**Goal:** convert telemetry artifacts into cartridge-grade reusable runtime pieces.

**Actions**
- Move engine to:
  - `2_engines/telemetry/engine/misconception_telemetry_engine_v1.js`
- Move schema to:
  - `2_engines/telemetry/schemas/misconception_event_schema_v1.json`
- Add replay fixtures:
  - `2_engines/telemetry/fixtures/misconception_events_pass_v1.json`
  - `2_engines/telemetry/fixtures/misconception_events_fail_v1.json`
- Keep classroom demo at:
  - `3_data/html_activities/fractions_number_line_telemetry_v1.html`
- Add adapter contract:
  - `runtime/cartridges/telemetry_cartridge_contract_v1.json`
- Normalize event shape to stable names and typed attributes.

**Outputs**
- promoted engine + schema + fixtures + cartridge contract
- `receipts/refactor_program/R9_TELEMETRY_CARTRIDGE_RECEIPT.json`

**Gate to proceed**
- fixture replay validates
- demo emits schema-valid events

### Stage R10 — Decision logging and audit trail hardening
**Goal:** unify gate decision logs and mutation receipts.

**Actions**
- Standardize decision log pathing:
  - `runtime/governance/decision_logs/<gate_id>/`
- Required fields:
  - `decision_id`
  - `gate_id`
  - `input_hash`
  - `bundle_or_contract_version`
  - `decision`
  - `reasons`
  - `timestamp_utc`
- Ensure every promoted gate writes both receipt and decision log.

**Outputs**
- `runtime/governance/schemas/decision_log_schema_v1.json`
- `0_kernel/scripts/validate_decision_log_v1.py`
- `receipts/refactor_program/R10_DECISION_LOGGING_RECEIPT.json`

**Gate to proceed**
- every enabled gate in registry either logs decisions or is explicitly marked `decision_log_required=false`

### Stage R11 — Legacy quarantine and redirect cleanup
**Goal:** prevent runtime drift from archived artifacts.

**Actions**
- Move dead-weight originals to:
  - `0_kernel/docs/archive/legacy_refactor_inputs/`
- Replace live references with redirect metadata.
- Add one registry file listing archived/superseded artifacts.

**Outputs**
- archive folder
- `runtime/governance/contracts/superseded_artifacts_registry_v1.json`
- `receipts/refactor_program/R11_LEGACY_QUARANTINE_RECEIPT.json`

**Gate to proceed**
- no active workflow file points at superseded artifacts

### Stage R12 — Regression suite and export preparation
**Goal:** make the refactor durable and export-safe.

**Actions**
- Add regression cases for:
  - stale compatibility contract
  - invalid session export
  - missing gate entrypoint
  - reuse gate with no evidence
  - telemetry invalid event shape
  - plain-python attempt from retained utility
- Write export inclusion manifest for all new paths.
- Rebuild project-files overlay from live runtime before final export.

**Outputs**
- regression fixtures under `runtime/evals/governance_regression_suite_v1/`
- `receipts/refactor_program/R12_REGRESSION_AND_EXPORT_PREP_RECEIPT.json`
- export manifest update

**Completion gate**
- all promoted artifacts present in live runtime
- all superseded artifacts archived or redirected
- regression suite pass
- project-files export contains new ADRs, contracts, registries, schemas, scripts, fixtures, and receipts

## LLM optimization rules for execution
- Prefer shell/coreutils for inventory, path moves, manifest generation, hashing, and archive work.
- Use Python only when needed for schema/JSON-aware transforms, and route through `python3 -S`.
- Keep prompts and stage work orders narrow:
  - one mutation family
  - one verification family
  - one receipt family
- Generate structured intermediate artifacts first, prose second.
- Read source files before patching and read patched files after patching.
- For any gate/policy design choice, compare at least five candidate implementation options before selecting one and bind the choice into an ADR.

## Required stage receipts
Every stage must write:
- `<STAGE>_PRESTATE.json`
- `<STAGE>_MUTATION_RECEIPT.json`
- `<STAGE>_VERIFY_RECEIPT.json`
- `<STAGE>_HANDOFF.json`

Minimum receipt fields:
- `stage_id`
- `timestamp_utc`
- `inputs`
- `mutations`
- `artifacts_written`
- `verification_steps`
- `result`
- `next_stage`
- `blockers[]`

## Recommended first executable stage
`R0_INTAKE_AND_PATH_BINDING_BOUNDED`

Rationale: the current live runtime does not yet contain most of the Claude-originated files; they are available in the repaired full-OS source zip. Intake and explicit path binding must happen before any refactor promotion work.
