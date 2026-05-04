---
status: accepted
category: governance
created_utc: 2026-04-28T00:00:00Z
refactor_stage: R2_ADR_EXTRACTION_AND_ARCHIVAL_CONVERSION
supersedes:
  - 1_governance/cool_overlays/COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json
---
# Adopt gate registry for runtime wiring

## Context and Problem Statement

MetaBlooms inherited `COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json` as a prose-heavy wiring plan. It lists phases, gates, and scripts, but it is not an executable registry and it lacks the fields needed for runtime loading, integrity checks, and failure-mode enforcement.

## Decision Drivers

* Runtime gate wiring must be loadable and integrity-checkable.
* Gate metadata must include entrypoint, preconditions, outputs, and failure behavior.
* Historical planning context should remain available without pretending to be the live registry.
* Registry design must support explicit enablement and decision-log requirements.

## Considered Options

* Keep the plan JSON as the primary source of gate wiring truth.
* Inline gate wiring directly into runner scripts with no registry.
* Archive the plan JSON and replace it with an executable gate registry plus validator.

## Decision Outcome

Chosen option: **Archive the plan JSON and replace it with an executable gate registry plus validator**, because runtime wiring needs structured, enforceable metadata rather than planning prose.

### Consequences

* Good, because gates can be loaded and verified systematically.
* Good, because each gate can declare failure mode, receipt type, and decision-log requirements.
* Good, because plan history remains preserved as archive material.
* Bad, because registry creation requires a loader and integrity validator.
* Bad, because migration requires careful field normalization from prose concepts.

### Confirmation

* `gate_registry_v1.json` exists and is validated in R5.
* `assert_gate_registry_integrity_v1.py` fails on missing entrypoints or malformed gate records.
* The legacy plan is preserved under `runtime/governance/legacy_archives/COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json`.

## Pros and Cons of the Options

### Keep the plan JSON as the primary source of gate wiring truth

* Good, because the file already lists phases and scripts.
* Bad, because it is incomplete for runtime loading and validation.
* Bad, because blocking semantics are inconsistently typed.

### Inline gate wiring directly into runner scripts with no registry

* Good, because runtime lookups are simple.
* Bad, because wiring becomes harder to audit and evolve.
* Bad, because integrity checks and discoverability degrade.

### Archive the plan JSON and replace it with an executable gate registry plus validator

* Good, because it cleanly separates history from enforcement.
* Good, because it supports strict runtime integrity checks.
* Neutral, because some planning language must be re-expressed in normalized registry fields.

## More Information

The archived source for this decision is retained at `runtime/governance/legacy_archives/COOL_6_RUNTIME_GATE_WIRING_PLAN_v1.json`.
