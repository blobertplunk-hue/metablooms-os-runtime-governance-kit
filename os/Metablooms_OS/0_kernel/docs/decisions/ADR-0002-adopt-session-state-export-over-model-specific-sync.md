---
status: accepted
category: runtime-state
created_utc: 2026-04-28T00:00:00Z
refactor_stage: R2_ADR_EXTRACTION_AND_ARCHIVAL_CONVERSION
supersedes:
  - CLAUDE_MEMORY_SYNC_v1.json
  - 0_kernel/scripts/claude_memory_sync_writer_v1.py
---
# Adopt session-state export over model-specific sync

## Context and Problem Statement

MetaBlooms inherited a model-specific handoff file (`CLAUDE_MEMORY_SYNC_v1.json`) and writer script (`claude_memory_sync_writer_v1.py`). These artifacts are useful as historical evidence of session transfer needs, but they encode vendor-specific assumptions and stale runtime paths. MetaBlooms needs a portable state export that survives model changes and sandbox differences.

## Decision Drivers

* Runtime state transfer must be model-agnostic.
* Export shape must be schema-validatable and artifact-hash-aware.
* Writer paths must respect the `python3 -S` execution lane or shell-first policy.
* Historical sync artifacts should remain available for audit and migration reference.

## Considered Options

* Keep Claude-specific sync as the ongoing handoff mechanism.
* Remove sync artifacts and rely only on receipts.
* Archive Claude-specific sync artifacts and replace them with a session-state export contract and exporter.

## Decision Outcome

Chosen option: **Archive Claude-specific sync artifacts and replace them with a session-state export contract and exporter**, because MetaBlooms needs portable session continuity without binding governance to a specific model vendor.

### Consequences

* Good, because future sessions can consume a stable export shape independent of model branding.
* Good, because the export can be validated and launcher-bound to the Python-safe lane.
* Good, because receipts remain primary while the export becomes a bounded handoff summary.
* Bad, because migration requires a new schema, validator, and exporter.
* Bad, because historical sync fields may not map one-to-one into the new structure.

### Confirmation

* `session_state_export_schema_v1.json` and `SESSION_STATE_EXPORT_LATEST_v1.json` are created and validated in R4.
* `session_state_exporter_v1.py` replaces model-specific naming and uses the safe execution lane.
* Legacy Claude-specific sync artifacts remain archived under `runtime/governance/legacy_archives/`.

## Pros and Cons of the Options

### Keep Claude-specific sync as the ongoing handoff mechanism

* Good, because the artifacts already exist.
* Bad, because the naming and fields are vendor-specific.
* Bad, because the source includes stale path assumptions and nonportable context.

### Remove sync artifacts and rely only on receipts

* Good, because it simplifies the system.
* Bad, because resumable session handoff loses a bounded summary layer.
* Bad, because operators must reconstruct state from many receipts every time.

### Archive Claude-specific sync artifacts and replace them with a session-state export contract and exporter

* Good, because it preserves history while improving portability.
* Good, because it supports schema validation and safer execution routing.
* Neutral, because the migration introduces a temporary parallel state during refactor.

## More Information

The archived source artifacts for this decision are retained at `runtime/governance/legacy_archives/CLAUDE_MEMORY_SYNC_v1.json` and `runtime/governance/legacy_archives/claude_memory_sync_writer_v1.py`.
