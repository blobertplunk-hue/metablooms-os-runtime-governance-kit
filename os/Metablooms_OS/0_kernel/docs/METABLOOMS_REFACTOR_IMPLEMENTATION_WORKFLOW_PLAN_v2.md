# MetaBlooms governed refactor implementation workflow plan v2

## Purpose

Implement a governed, LLM-optimized refactor that converts weak or half-runtime artifacts into:
- ADRs for rationale and historical decisions
- executable contracts and registries for machine-read governance
- evidence-bound gates for allow/deny decisions
- portable session-state export instead of model-specific sync files
- cartridge-grade telemetry with stable event semantics and replay/validation support

This v2 updates v1 by adding:
- an explicit risk register
- a bounded option-analysis protocol
- a deterministic merge/refactor protocol
- gate-failure recovery rules
- source-bundle verification procedure
- conflict handling for already-present runtime artifacts

## Authority and inputs

- Live runtime root: `/mnt/data/Metablooms_OS`
- Repaired source archive: `/mnt/data/METABLOOMS_FULL_OS_v3_3_PHASE1_PHASE2_MERGED_REPAIRED.zip`
- Prior plan superseded: `0_kernel/docs/METABLOOMS_REFACTOR_IMPLEMENTATION_WORKFLOW_PLAN_v1.md`

## External design anchors

### ADR structure
Use MADR-style ADR sections:
- Context and Problem Statement
- Decision Drivers
- Considered Options
- Decision Outcome
- Consequences
- Confirmation

### Policy / decision separation
Treat allow/deny governance as policy-style decisioning:
- machine-readable input
- deterministic result
- decision id
- auditable decision log
- policy tests separate from production logic

### Schema discipline
Treat JSON Schema annotations as documentation only, not enforcement. Enforcement must live in validators/gates.

### Telemetry discipline
Use stable low-cardinality event names plus typed attributes and explicit event schemas.

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

## Core implementation rules

1. History/rationale must live in ADRs, not in pseudo-runtime JSON.
2. Runtime enforcement must be executable and return pass/fail plus reasons.
3. Schema annotations are documentation, not enforcement.
4. Telemetry must use stable event names, typed attributes, and replayable fixtures.
5. All new Python execution paths must route through the existing `python3 -S` lane unless a stricter shell-only path is possible.
6. Every stage writes: pre-state probe -> mutation receipt -> verify receipt -> handoff.
7. No broad multi-goal patching in one stage; one bounded mutation family per stage.
8. If a gate fails, write a blocked receipt and stop unless a documented recovery branch exists in this plan.
9. No source artifact may be trusted until its path, hash, and extracted content are bound into the intake manifest.

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
- `0_kernel/registry/repair_backlog/`
- `runtime/governance/risk/`

## Explicit risk register

Create and maintain:
- `runtime/governance/risk/refactor_program_risk_register_v1.json`

Required fields per risk:
- `risk_id`
- `title`
- `description`
- `trigger`
- `likelihood` (`low|medium|high`)
- `impact` (`low|medium|high`)
- `detection_method`
- `mitigation`
- `fallback_branch`
- `owner_artifact`
- `status`

Initialize with at least these risks:
- `RISK-001`: source bundle missing one or more named artifacts
- `RISK-002`: live runtime already contains conflicting successor artifacts
- `RISK-003`: python3 `-S` lane incompatible with a needed import path
- `RISK-004`: stage produces archival ADR but no executable successor
- `RISK-005`: registry enables a gate whose entrypoint does not exist
- `RISK-006`: telemetry schema and engine drift structurally
- `RISK-007`: option-analysis overhead stalls simple stages
- `RISK-008`: repaired bundle hash unavailable or mismatched

## Option-analysis protocol (bounded)

Not every change requires five long-form options. Use this bounded protocol:

### Decision classes
- `Class A` — architecture-affecting change: requires five candidate options.
- `Class B` — important but local implementation choice: requires three candidate options.
- `Class C` — mechanical rename/move/path-binding patch: requires two candidate options.

### Time bounds
- Class A: max 20 minutes of option analysis
- Class B: max 10 minutes
- Class C: max 5 minutes

### Required output
For every stage that includes option analysis, write:
- `decision_context`
- `decision_class`
- `candidate_options[]`
- `selection_rule`
- `chosen_option`
- `rejected_options`
- `time_bound_minutes`

Path:
- `runtime/governance/decision_logs/DECISION_LOG_<stage>_<timestamp>.json`

## Merge / refactor protocol

Whenever a stage says to merge, replace, or promote logic, use this deterministic comparison order:

1. **Path bind both candidates** and hash them.
2. **Classify relationship** as one of:
   - identical
   - duplicate-with-minor-drift
   - complementary
   - conflicting
   - source-missing
3. For code/script files, compare:
   - launcher safety (`python3 -S` / shell-first)
   - error handling
   - receipt writing behavior
   - path correctness
   - dependency footprint
   - testability
4. Keep the version that wins on:
   - runtime safety
   - governance compliance
   - smaller dependency surface
   - clearer failure behavior
5. If neither version clearly wins, create a successor artifact rather than force-merging.
6. Record the exact decision in a decision log.

No stage may use the phrase “merge non-duplicative logic” without writing this protocol outcome.

## Gate-failure recovery rules

If any gate fails:
1. write `*_BLOCKED_RECEIPT.json`
2. include failed gate, reason, evidence paths, and recommended next branch
3. stop the mainline stage
4. only continue if one of these is true:
   - the plan explicitly defines a fallback branch for that gate
   - the failure is fixed in a bounded repair substage

Allowed fallback branch types:
- `retry_after_reprobe`
- `archive_without_promotion`
- `quarantine_conflict_and_continue`
- `defer_to_repair_backlog`

Manual override is not part of the default path. Any override must be a separate artifact-bearing decision stage.

## Source bundle verification procedure

Before extraction, write:
- `receipts/refactor_program/R0_SOURCE_HASH_PROBE.json`

Procedure:
1. compute current SHA-256 of the repaired source archive
2. compare to sidecar if present
3. enumerate required entries directly from the ZIP
4. record missing entries explicitly
5. bind verified source hash into intake manifest

If no trusted expected hash is available, mark status as:
- `hash_observed_not_precommitted`
and proceed only if the archive contents also pass path-level checks.

## Implementation order

### Stage R0 — Boot, authority, and source intake contract
**Goal:** prove current root, prove source bundle, and stage candidate imports without mutating live authority.

**Actions**
- Verify `/mnt/data/Metablooms_OS` is writable and current.
- Verify repaired source bundle hash and enumerate target files.
- Extract only the target Claude-added artifacts into a bounded staging area:
  - `0_kernel/staging/refactor_intake_<timestamp>/source_bundle_extract/`
- Write path map and intake manifest.
- Initialize risk register with observed source-presence status.

**Outputs**
- `receipts/refactor_program/R0_INTAKE_RECEIPT.json`
- `receipts/refactor_program/R0_PATH_MAP.json`
- `receipts/refactor_program/R0_SOURCE_INTAKE_MANIFEST.json`
- `receipts/refactor_program/R0_SOURCE_HASH_PROBE.json`
- `runtime/governance/risk/refactor_program_risk_register_v1.json`

**Gate to proceed**
- every listed source artifact either extracted or explicitly marked absent
- no live runtime mutation yet

**Failure branch**
- missing source artifacts -> `archive_without_promotion` or `defer_to_repair_backlog`

### Stage R1 — Classification and disposition binding
**Goal:** convert keep/optional/dead-weight judgment into explicit artifact disposition.

**Actions**
- Create `runtime/governance/contracts/artifact_disposition_contract_v1.json`.
- Record each source artifact as one of:
  - `promote`
  - `split`
  - `archive_only`
  - `discard`
- Add required successor artifact ids and destination paths.
- Record any live-runtime conflicts.

**Outputs**
- disposition contract
- `receipts/refactor_program/R1_DISPOSITION_RECEIPT.json`
- decision log if any `split` or `conflicting` choices were made

**Gate to proceed**
- no artifact may remain ambiguous
- every `split` item identifies both archived rationale target and executable successor target

### Stage R2 — ADR extraction and archival conversion
**Goal:** relocate rationale/history out of pseudo-runtime JSON.

**Actions**
- Parse `CROSS_LINK_GW_OS_KERNEL_HANDOFF_v1.json` and surviving Claude sync narrative fields.
- Generate ADRs under `0_kernel/docs/decisions/` using MADR-style sections.
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
- Required fields:
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
- fixture under `runtime/evals/governance_regression_suite_v1/fixtures/`
- `receipts/refactor_program/R3_COMPATIBILITY_CONTRACT_RECEIPT.json`

**Gate to proceed**
- validator fails on stale or incomplete contract
- old cross-link file marked `archive_only`

### Stage R4 — Session-state export replacement
**Goal:** replace Claude-specific memory sync with model-agnostic state export.

**Actions**
- Create schema: `runtime/governance/schemas/session_state_export_schema_v1.json`
- Create snapshot artifact path: `runtime/governance/state_exports/SESSION_STATE_EXPORT_LATEST_v1.json`
- Implement writer: `0_kernel/scripts/session_state_exporter_v1.py`
- Implement validator: `0_kernel/scripts/validate_session_state_export_v1.py`
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
- Implement loader: `runtime/governance/load_gate_registry_v1.py`
- Implement integrity validator: `0_kernel/scripts/assert_gate_registry_integrity_v1.py`
- Migrate any gate definitions recoverable from `COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json`.

**Outputs**
- gate registry JSON
- loader
- integrity validator
- `receipts/refactor_program/R5_GATE_REGISTRY_RECEIPT.json`

**Gate to proceed**
- every enabled gate resolves to a real path
- no enabled gate points to a missing script or schema

### Stage R6 — Evidence-bound external reuse scan gate
**Goal:** convert the external reuse scan from advisory prose/script into an evidence-bound gate.

**Actions**
- Create schema: `runtime/governance/schemas/external_reuse_scan_input_schema_v1.json`
- Create policy contract: `runtime/governance/contracts/external_reuse_scan_gate_contract_v1.json`
- Implement runner: `0_kernel/scripts/run_external_reuse_scan_gate_v1.py`
- Required input fields:
  - `target_artifact_path`
  - `see_evidence_artifacts[]`
  - `reuse_claims[]`
  - `decision_context`
- Required output fields:
  - `decision`
  - `reasons[]`
  - `missing_evidence[]`
  - `matched_candidates[]`
  - `decision_id`
- Add policy tests / fixtures.

**Outputs**
- input schema
- gate contract
- runner
- fixture set
- decision log entries
- `receipts/refactor_program/R6_REUSE_SCAN_GATE_RECEIPT.json`

**Gate to proceed**
- no `pass` decision without evidence artifact hashes
- tests cover pass/fail/defer outcomes

### Stage R7 — Usefulness validator promotion into registered gate
**Goal:** promote usefulness validation from script utility to official registered gate.

**Actions**
- Define schema for usefulness-surface input
- refactor existing validator if needed
- register gate in `gate_registry_v1.json`
- add regression fixtures and expected decision outputs

**Outputs**
- usefulness schema
- updated validator
- registry update
- `receipts/refactor_program/R7_USEFULNESS_GATE_RECEIPT.json`

**Gate to proceed**
- validator usable both standalone and via registry
- failures produce structured reasons

### Stage R8 — Python health governance alignment
**Goal:** keep useful Python-health logic while aligning it with the new launcher rules.

**Actions**
- Compare imported `p0py_python_health_governance_v1.py` against live Python workaround artifacts using the merge/refactor protocol.
- Keep / adapt only logic that improves current runtime behavior.
- Ensure all promoted paths resolve through the `python3 -S` lane or shell-first wrappers.
- If import assumptions break under `-S`, quarantine those branches and record them in the risk register.

**Outputs**
- updated/promoted Python health governance artifact(s)
- decision log for keep/replace/split choice
- `receipts/refactor_program/R8_PYTHON_HEALTH_ALIGNMENT_RECEIPT.json`

**Gate to proceed**
- no promoted Python governance artifact may require normal `python3`
- all retained branches verified in the sandbox

### Stage R9 — Stage-base resolver assessment and promotion
**Goal:** promote or absorb stage-base resolver utility if it still closes a live failure class.

**Actions**
- compare imported resolver to current live root/path handling
- if useful, either keep as a standalone resolver or absorb logic into existing path-binding utilities
- add probe tests for writable root resolution

**Outputs**
- promoted or absorbed resolver logic
- test fixture(s)
- `receipts/refactor_program/R9_STAGE_BASE_RESOLVER_RECEIPT.json`

**Gate to proceed**
- root resolution behavior demonstrably improves or at minimum stays non-regressive

### Stage R10 — Telemetry cartridge promotion
**Goal:** convert telemetry pieces into cartridge-grade reusable runtime components.

**Actions**
- move/normalize telemetry JS under `2_engines/telemetry/engine/`
- move schema under `2_engines/telemetry/schemas/`
- create replay fixtures under `2_engines/telemetry/fixtures/`
- bind classroom HTML demo to the promoted schema/engine
- define event names and typed attributes explicitly
- add validation script for telemetry payload conformance

**Outputs**
- normalized telemetry engine
- telemetry schema
- replay fixtures
- updated demo HTML
- telemetry validator
- `receipts/refactor_program/R10_TELEMETRY_PROMOTION_RECEIPT.json`

**Gate to proceed**
- schema and engine agree structurally
- demo emits valid events against fixture/validator

### Stage R11 — Decision logging standardization
**Goal:** standardize decision log format across new gates and refactor choices.

**Actions**
- create schema: `runtime/governance/schemas/decision_log_schema_v1.json`
- ensure every promoted gate can emit:
  - `decision_id`
  - `gate_id`
  - `input_artifacts`
  - `result`
  - `reasons`
  - `timestamp_utc`
- add validator and fixture

**Outputs**
- decision log schema
- validator
- sample logs
- `receipts/refactor_program/R11_DECISION_LOG_STANDARDIZATION_RECEIPT.json`

**Gate to proceed**
- every new gate path either emits or explicitly declines decision logs with justification

### Stage R12 — Legacy quarantine, redirects, and cleanup
**Goal:** prevent ambiguous old artifacts from silently reasserting authority.

**Actions**
- move superseded artifacts to a quarantine/archive path or leave tombstones
- update redirects contract
- update artifact disposition contract status to final
- add lessons-learned entries for each demotion/split class

**Outputs**
- quarantine tree or archive paths
- final disposition contract
- lessons-learned entries
- `receipts/refactor_program/R12_LEGACY_QUARANTINE_RECEIPT.json`

**Gate to proceed**
- no superseded artifact remains in a live authority path without redirect metadata

### Stage R13 — Regression suite expansion
**Goal:** extend the governance regression suite to cover all new runtime pieces.

**Actions**
- add fixtures/tests for:
  - stale compatibility contract
  - malformed state export
  - gate registry missing entrypoint
  - reuse gate missing evidence
  - usefulness gate low-value artifact fail
  - telemetry schema mismatch
  - decision log schema mismatch
- emit consolidated regression receipt

**Outputs**
- fixture additions
- regression receipt
- `receipts/refactor_program/R13_REGRESSION_EXPANSION_RECEIPT.json`

**Gate to proceed**
- all new tests pass or are explicitly blocked with reasoned receipts

### Stage R14 — Export-prep and overlay synchronization
**Goal:** prepare the runtime for a later clean export without stale overlay regression.

**Actions**
- sync any project-files overlay content regenerated from live authority
- verify project-files overlay includes the promoted artifacts needed for boot continuity
- write export-readiness handoff only; do not claim final export in this stage

**Outputs**
- overlay sync receipt
- export-readiness handoff
- `receipts/refactor_program/R14_EXPORT_PREP_RECEIPT.json`

**Gate to proceed**
- overlay content matches live promoted governance artifacts for the relevant paths

## Program-level success criteria

The program is successful when all of the following are true:
1. narrative-heavy artifacts have ADR successors and no longer occupy live authority roles
2. machine-readable contracts and registries are loadable and validated
3. new gates are evidence-bound and produce structured results
4. session state export is model-agnostic and launcher-safe
5. telemetry artifacts are schema-bound, replayable, and validated
6. superseded artifacts are quarantined or redirected
7. regression coverage exists for every promoted refactor family

## Immediate next governed stage

`R0_INTAKE_AND_PATH_BINDING_BOUNDED_V2`
